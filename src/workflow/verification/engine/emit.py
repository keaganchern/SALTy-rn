"""Generate a C++ equivalence harness from a NEON+RVV kernel pair.

Two paths: generate_harness (elementwise — bound sweep + params) and
generate_multidim (FixtureSpec-driven multi-dim families, e.g. transpose).
"""
from __future__ import annotations

import os
import re

from .frontend import (parse_signature, resolve_roles, parse_struct_leaves,
                       classify_param_struct, Signature, Roles)
# Curated valid param values / ranges / constraints (the merged param data module).
from ..param_configs import (FIELD_EDGES, EDGE_VALUES, PARAM_CONSTRAINTS,
                            CONCRETE_PARAM_CONFIGS, get_param_ranges)

_FP_CTYPES = ("float", "double", "_Float16", "xnn_float16")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_XNN_MIN_H = os.path.join(_ROOT, "src", "verification_bw", "xnn_minimal.h")

# element type → (ElementKind, byte width)
_KIND = {
    "float": "F32", "double": "F64",
    "int8_t": "SINT", "int16_t": "SINT", "int32_t": "SINT", "int64_t": "SINT",
    "signed char": "SINT", "short": "SINT", "int": "SINT", "long": "SINT",
    "uint8_t": "UINT", "uint16_t": "UINT", "uint32_t": "UINT", "uint64_t": "UINT",
    "unsigned char": "UINT", "unsigned short": "UINT", "unsigned int": "UINT",
    "unsigned long": "UINT",
    "_Float16": "F16", "xnn_float16": "F16",
}
_BYTES = {
    "float": 4, "double": 8,
    "int8_t": 1, "int16_t": 2, "int32_t": 4, "int64_t": 8,
    "signed char": 1, "short": 2, "int": 4, "long": 8,
    "uint8_t": 1, "uint16_t": 2, "uint32_t": 4, "uint64_t": 8,
    "unsigned char": 1, "unsigned short": 2, "unsigned int": 4, "unsigned long": 8,
    "_Float16": 2, "xnn_float16": 2,
}


def _kind(pointee: str) -> str:
    if pointee not in _KIND:
        raise NotImplementedError(f"unhandled element type {pointee!r}")
    return _KIND[pointee]


# Per-kernel output ULP tolerance: 0 (default) = bit-exact; >0 relaxes FP outputs
# to "agree within N ULP". Keys are name substrings; SALT_ULP_TOL=<n> overrides all.
_ULP_TOL = {
    "raddstoreexpminusmax": 4,
}


def _ulp_tol_for(name: str) -> int:
    env = os.environ.get("SALT_ULP_TOL")
    if env not in (None, ""):
        return int(env)
    for key, tol in _ULP_TOL.items():
        if key in name:
            return tol
    return 0


def _detect_byte_unit(src: str, bound: str):
    """Detect the XNNPACK `batch % sizeof(T)` byte-count idiom. Returns
    (is_byte_unit, element_type). `batch` is then a byte count whose unit is
    sizeof(T); otherwise it's an element count."""
    m = re.search(rf"\b{re.escape(bound)}\b\s*[%/]\s*sizeof\s*\(\s*([\w ]+?)\s*\)", src)
    if not m:  # loop-decrement form: `batch -= k * sizeof(T)`
        m = re.search(rf"\b{re.escape(bound)}\b[^;\n]*sizeof\s*\(\s*([\w ]+?)\s*\)", src)
    return (True, m.group(1).strip()) if m else (False, None)


def _field_values(path: str, ctype: str):
    """Valid concrete edge values for a struct leaf — by field name first (the
    semantic table), then by type. Returns C literals."""
    fname = path.split(".")[-1]
    raw = FIELD_EDGES.get(fname)
    if raw is None:
        raw = EDGE_VALUES.get(ctype)
    if not raw:
        return []
    if ctype == "float" or ctype in ("xnn_float16", "_Float16"):
        return [f"{float(v)}f" for v in raw]
    if ctype == "double":
        return [f"{float(v)}" for v in raw]
    return [str(int(v)) for v in raw]          # integer fields


def _gen_configs(leaves, cap: int = 24, struct_name: str = ""):
    """One-at-a-time configs around a base (each field's first value), so every
    field's values are exercised without a combinatorial blow-up. Cross-field
    validity holds by construction (output_min/max are fixed, multiplier≥1, …)."""
    if struct_name in CONCRETE_PARAM_CONFIGS:
        paths, combos = CONCRETE_PARAM_CONFIGS[struct_name]
        return paths, combos[:cap]
    fields = [(p, _field_values(p, t)) for p, t, _ in leaves if p != "_"]
    fields = [(p, vs) for p, vs in fields if vs]
    if not fields:
        return [], []
    paths = [p for p, _ in fields]
    base = [vs[0] for _, vs in fields]
    combos = [tuple(base)]
    for i, (_, vs) in enumerate(fields):
        for v in vs[1:]:
            c = list(base)
            c[i] = v
            combos.append(tuple(c))
    return paths, combos[:cap]


def _emit_config_table(st: str, paths, combos) -> str:
    set_cases, name_cases = [], []
    for i, combo in enumerate(combos):
        assigns = " ".join(f"p.{path} = {val};" for path, val in zip(paths, combo))
        set_cases.append(f"    case {i}: {assigns} break;")
        label = ",".join(f"{path.split('.')[-1]}={val.rstrip('f')}"
                         for path, val in zip(paths, combo))
        name_cases.append(f'    case {i}: return "{label}";')
    return (f"static void _set_params({st}& p, size_t cfg) {{\n"
            f"  switch (cfg) {{\n" + "\n".join(set_cases) + "\n  }\n}\n"
            f"static const char* _cfg_name(size_t cfg) {{\n"
            f"  switch (cfg) {{\n" + "\n".join(name_cases) +
            '\n  default: return "?";\n  }\n}\n')


def _strip_simd_includes(src: str) -> str:
    """Remove the kernel's own <arm_neon.h>/<riscv_vector.h> includes — salt.hpp
    supplies the symbolic shims, and the real headers aren't on the include path."""
    return re.sub(r'^[ \t]*#[ \t]*include[ \t]*<(arm_neon|riscv_vector)\.h>[ \t]*$',
                  '', src, flags=re.M)


def _neon_void_load_adapters(src: str) -> str:
    """Accept C void-pointer loads while retaining the typed symbolic shims."""
    loads = (("vld1q_s32", "int32x4_t", "int32_t"),
             ("vld1_s8", "int8x8_t", "int8_t"),
             ("vld1q_f32", "float32x4_t", "float"))
    return "\n".join(
        f"using salt::{fn};\ninline {ret} {fn}(const void* p) "
        f"{{ return salt::{fn}(static_cast<const {elem}*>(p)); }}"
        for fn, ret, elem in loads if re.search(rf"\b{fn}\s*\(", src))


def _split_body(src: str):
    """(head, body) split at the function's opening brace. Matches the actual
    `void test_*(` definition — robust to 'test_' mentions in comments."""
    m = re.search(r'\bvoid\s+test_\w*\s*\(', src)
    brace = src.find("{", m.end()) if m else -1
    return (src[:brace], src[brace:]) if brace != -1 else (src, "")


def _scalar_broadcast_inputs(src: str, input_names) -> set:
    """Inputs read as a scalar (`*name`) in the function *body* — a broadcast
    constant, not a vector loaded via an intrinsic. The signature's `T* name`
    decl is excluded by scanning only after the opening brace."""
    _, body = _split_body(src)
    return {n for n in input_names if re.search(rf'\*\s*{re.escape(n)}\b', body)}


_SCALAR_TYPE = re.compile(r'^(u?int(8|16|32|64)_t|uint|int|short|long|float|double|size_t|u?char)$')


def _rebind_tainted_locals(body: str) -> str:
    """A scalar-typed local initialized (transitively) from a symbolic scalar now
    holds a SymbolicScalar, so its type must become `auto`. Iterates to a fixpoint
    over the taint set. Vector types (int32x4_t, …) are left alone — their shims
    already carry symbolic lanes."""
    lines = body.split("\n")
    tainted: set = set()
    changed = True
    while changed:
        changed = False
        for i, ln in enumerate(lines):
            m = re.match(r'^(\s*)(const\s+)?(\w+)\s+(\w+)\s*=\s*(.+?);(\s*)$', ln)
            if not m:
                continue
            indent, c, typ, name, init, tail = m.groups()
            if typ == "auto" or name in tainted or not _SCALAR_TYPE.match(typ):
                continue
            if ("salt_scalar" in init or "salt_param" in init or
                    any(re.search(rf'\b{re.escape(t)}\b', init) for t in tainted)):
                lines[i] = f'{indent}{c or ""}auto {name} = {init};{tail}'
                tainted.add(name)
                changed = True
    return "\n".join(lines)


def _rewrite_scalar_broadcast(src: str, names) -> str:
    """Rewrite scalar reads of broadcast inputs (in the body only) to a symbolic
    accessor: `(T) *name` -> `salt_scalar(name).cast<T>()`, `*name` -> `salt_scalar(name)`."""
    if not names:
        return src
    head, body = _split_body(src)
    if not body:
        return src
    for n in names:
        # Local pointer declarations contain '*name' too; retain those verbatim.
        parts = re.split(
            rf'(\b(?:const\s+)?\w+\s*\*\s*(?:restrict\s+)?{re.escape(n)}\b(?=\s*[=;]))',
            body)
        # Preserve the increment on the pointer, not on the loaded scalar.
        ptr = rf'{re.escape(n)}\b(\s*\+\+)?'
        for i in range(0, len(parts), 2):
            part = re.sub(rf'\(\s*(\w+)\s*\)\s*\*\s*{ptr}',
                          lambda m: f'salt_scalar({n}{m[2] or ""}).cast<{m[1]}>()', parts[i])
            part = re.sub(rf'\*\s*{ptr}',
                          lambda m: f'salt_scalar({n}{m[1] or ""})', part)
            if re.search(rf'\*\s*{re.escape(n)}\b', part):
                raise NotImplementedError(f"unrewritten scalar read of {n} remains "
                                          "(unhandled access pattern)")
            parts[i] = part
        body = "".join(parts)
    body = _rebind_tainted_locals(body)  # propagate symbolic taint to dependent scalar locals
    return head + body


def _rewrite_index_reads(src: str, names) -> str:
    """Rewrite scalar element reads `p[i]` of symbolic-buffer pointers to
    salt_scalar accessors (int element types have no NaN-payload sentinel)."""
    if not names:
        return src
    head, body = _split_body(src)
    if not body:
        return src
    for n in names:
        body = re.sub(rf'\(\s*(\w+)\s*\)\s*{re.escape(n)}\s*\[\s*([^\]]+?)\s*\]',
                      rf'salt_scalar({n} + (\2)).cast<\1>()', body)   # (T) p[i] → .cast<T>()
        body = re.sub(rf'\b{re.escape(n)}\s*\[\s*([^\]]+?)\s*\]',
                      rf'salt_scalar({n} + (\1))', body)
    body = _rebind_tainted_locals(body)
    return head + body


def _rewrite_scalar_movs(src: str) -> str:
    """Rewrite scalar buffer-to-buffer moves `*dst = *src++;` (packw remainder
    paths) to symbolic accessors: `salt_deref(dst) = salt_scalar(src); src += 1;`."""
    head, body = _split_body(src)
    if not body:
        return src
    return head + re.sub(r'\*\s*(\w+)\s*=\s*\*\s*(\w+)\s*\+\+\s*;',
                         r'salt_deref(\1) = salt_scalar(\2); \2 += 1;', body)


def _rewrite_symbolic_params(src: str, st: str, pname: str, leaves) -> str:
    """Rewrite `params->field` reads to a symbolic accessor so the solver proves
    over ALL valid param values. `(T) params->f` -> `salt_param<ft>(...).cast<T>()`."""
    head, body = _split_body(src)
    if not body:
        return src
    for path, ctype, _ in sorted(leaves, key=lambda l: -len(l[0])):  # longest first
        if path == "_":
            continue
        acc = f"salt_param<{ctype}>({pname}, offsetof({st}, {path}))"
        esc = re.escape(f"{pname}->{path}")
        body = re.sub(rf'\(\s*(\w+)\s*\)\s*{esc}\b', rf'{acc}.cast<\1>()', body)
        body = re.sub(rf'{esc}\b', acc, body)
    # XNNPACK idiom `(T)(-(U)params->f)`: the inner `(U)params->f` became a
    # `.cast<U>()` accessor above, but the outer C-style `(T)(...)` cast can't
    # apply to a SymbolicScalar. Rewrite `(T) <sym>` → symbolic `<sym>.cast<T>()`.
    _ACC = r"salt_param<\w+>\(\w+,\s*offsetof\([^)]+\)\)(?:\.cast<\w+>\(\))?"
    _CT = r"u?int(?:8|16|32|64)_t|size_t"
    _prev = None
    while _prev != body:
        _prev = body
        body = re.sub(rf'\(\s*({_CT})\s*\)\s*\(\s*-\s*({_ACC})\s*\)', r'(-\2).cast<\1>()', body)
        body = re.sub(rf'\(\s*({_CT})\s*\)\s*-\s*({_ACC})',           r'(-\2).cast<\1>()', body)
        body = re.sub(rf'\(\s*({_CT})\s*\)\s*\(\s*({_ACC})\s*\)',     r'\2.cast<\1>()', body)
        body = re.sub(rf'\(\s*({_CT})\s*\)\s*({_ACC})',               r'\2.cast<\1>()', body)
    body = _rebind_tainted_locals(body)
    if f"{pname}->" in body:  # residual param read the rewrite missed → fail loudly
        raise NotImplementedError(f"unrewritten param read of {pname} remains "
                                  "(unhandled access pattern)")
    return head + body


def _field_leaf_map(leaves):
    """field-name → (dotted_path, ctype), dropping the dummy `_` member."""
    return {p.split(".")[-1]: (p, t) for p, t, _ in leaves if p != "_"}


def _emit_param_constraints(st: str, leaves) -> list:
    """Validity asserts (e.g. output_min ≤ output_max, shift∈[0,31], multiplier>0)
    from the curated PARAM_CONSTRAINTS, against the symbolic params buffer."""
    f2l = _field_leaf_map(leaves)
    out = []
    for op, a, b in PARAM_CONSTRAINTS.get(st, []):
        if a not in f2l:
            continue
        pa, ta = f2l[a]
        bits_a = _BYTES[ta] * 8
        meth = "bv_" + op[3:].lower()          # BV_SLE -> bv_sle
        at = f"_b_params.loadScalar(offsetof({st}, {pa}), {bits_a})"
        if isinstance(b, int):
            bt = f"ctx.bv_val({bits_a}, {b})"
        elif b in f2l:
            pb, tb = f2l[b]
            bt = f"_b_params.loadScalar(offsetof({st}, {pb}), {_BYTES[tb] * 8})"
        else:
            continue
        out.append(f"    ctx.assert_(ctx.{meth}({at}, {bt}));")
    return out


def _emit_param_ranges(st: str, leaves, ranges: dict) -> list:
    """Per-field [lo, hi] bounds (from the kernel profile) — restrict symbolic
    params to their valid domain (e.g. a narrowed multiplier that must fit int16),
    which also helps the solver. Signed vs unsigned chosen by the field type."""
    f2l = _field_leaf_map(leaves)
    out = []
    for fname, bounds in (ranges or {}).items():
        if fname not in f2l or not bounds:
            continue
        lo, hi = bounds
        path, ct = f2l[fname]
        bits = _BYTES[ct] * 8
        ge, le = ("bv_sge", "bv_sle") if not ct.startswith("u") else ("bv_uge", "bv_ule")
        v = f"_b_params.loadScalar(offsetof({st}, {path}), {bits})"
        out.append(f"    ctx.assert_(ctx.{ge}({v}, mk_bv_val(ctx.tm, {bits}, {lo})));")
        out.append(f"    ctx.assert_(ctx.{le}({v}, mk_bv_val(ctx.tm, {bits}, {hi})));")
    return out


def _emit_input_range(buf_var: str, n_expr: str, lo, hi) -> list:
    """Constrain each F32 element of a symbolic input buffer to finite [lo, hi]
    (excludes NaN/inf — FP comparisons are false for NaN). Optional; weakens the
    claim to finite inputs, so it must be recorded in the verdict."""
    lo_f, hi_f = float(lo), float(hi)   # ensure valid float literals (e.g. "-1" → -1.0f)
    return [
        f"    {{  // input-range [{lo_f}, {hi_f}] on {buf_var}",
        f"        Term _lo = mk_fp32_from_float(ctx.tm, {lo_f}f), _hi = mk_fp32_from_float(ctx.tm, {hi_f}f);",
        f"        for (size_t _i = 0; _i < ({n_expr}); _i++) {{",
        f"            Term _fp = load_as_fp32(ctx.tm, {buf_var}.loadScalar(_i * 4, 32));",
        f"            ctx.assert_(ctx.land_(ctx.fp32_geq(_fp, _lo), ctx.fp32_leq(_fp, _hi)));",
        f"        }}",
        f"    }}",
    ]


def _output_is_read(src: str, name: str) -> bool:
    """True if an output buffer is *read* (loaded) anywhere — i.e. it's an in-out
    accumulator / in-place buffer, where the prior contents are part of the input.
    Detected by the output pointer appearing as the argument to a load intrinsic."""
    return bool(re.search(
        rf"(vld\w*|__riscv_vle\w+|vget\w*q?_\w+)\s*\(\s*&?\s*{re.escape(name)}\b", src))


# Multi-dim fixture: swept dims + chosen strides.
class FixtureSpec:
    def __init__(self, dims, strides, extents, out_buffers, out_extent, elem, kind,
                 out_region=None, weights=None, params=None, indirect=None,
                 out_extents=None, dual_weights=None, out_elem=None, out_kind=None,
                 probes=None, odd_tail_dim=None, grow_dim=None, grow_cross=None,
                 out_elems=None, shared_out=None, scalar_movs=False,
                 extra_params=None, raw_decls=None, index_reads=None, pre_defines=None,
                 scalar_reads=None, config_tag=None):
        self.dims = dims              # dim_name -> [values]
        self.strides = strides        # stride_name -> C++ expr (over dims)
        self.extents = extents        # buffer_name -> byte-count expr
        self.out_buffers = out_buffers
        self.out_extent = out_extent  # contiguous output element count (if no out_region)
        self.elem = elem
        self.kind = kind
        self.out_elem = out_elem or elem   # output element type (rdsum: int8 in, int32 out)
        self.out_kind = out_kind or kind   # output ElementKind (matches out_elem)
        self.out_region = out_region  # {rows,cols,row_stride,col_stride} → strided compare
        self.weights = weights or {}  # name -> (byte-extent expr, uniform fill literal) — concrete
        self.params = params          # (struct_name, {field: value}) — concrete struct, or None
        self.indirect = indirect or {}  # name -> {count, row} — T** pointer table over a symbolic buffer
        self.out_extents = out_extents   # {name: elem-count expr} — multi-output contiguous compare (each output ANDed)
        self.out_elems = out_elems or {}  # {output_name: C type} — per-output element type for MIXED-type multi-output (argmaxpool: output=float, index=uint32_t); defaults to out_elem
        self.dual_weights = dual_weights or {}  # name -> {count, neon_tile, rvv_tile} — per-dialect weight packing
        self.probes = probes or []    # extra explicit shapes [{dim: value, ...}] appended after the dims cross product
        self.odd_tail_dim = odd_tail_dim  # dim whose odd value routes the last output lane through a scalar `*out += vgetq_lane` store (rsum/rdsum tail) — captured via scalar side-channel
        self.grow_dim = grow_dim          # dim to grow continuously (unbounded sweep over argv[1..2]/budget) instead of cross-product; the rest of `dims` is the per-row representative inner set
        self.grow_cross = grow_cross      # (d0, d1): grow BOTH dims cross-product-wise as an expanding N×N square frontier until budget (dims must be empty)
        self.shared_out = shared_out or []  # outputs with unwritten holes (packw extra_bytes gaps) → force shared init even if never read
        self.scalar_movs = scalar_movs    # rewrite `*dst = *src++;` to salt_deref/salt_scalar accessors (packw remainder)
        self.extra_params = extra_params or {}  # name -> (struct, {field: value}) — 2nd+ concrete param structs (qd8 quantization_params)
        self.raw_decls = raw_decls or []  # raw C++ lines appended after buffer decls (extra constraints; cvc5 API)
        self.index_reads = index_reads or []  # local ptr names whose `p[i]` reads become salt_scalar (int scalars, no sentinel)
        self.pre_defines = pre_defines or []  # #define lines before kernel bodies (e.g. force XNN_ARCH_ARM64=0)
        self.scalar_reads = scalar_reads or []  # local input pointers dereferenced as *p / *p++
        self.config_tag = config_tag


def _transpose_fixture(elem: str) -> "FixtureSpec":
    # block_height×block_width → block_width×block_height, any element width.
    # Padded strides (+8B/row) make the output strided. grow_cross expands an N×N
    # square frontier until the budget.
    return FixtureSpec(
        dims={},
        grow_cross=("block_width", "block_height"),
        strides={"input_stride": f"block_width * sizeof({elem}) + 8",
                 "output_stride": f"block_height * sizeof({elem}) + 8"},
        extents={"input": "block_height * input_stride + 64",     # bytes
                 "output": "block_width * output_stride + 64"},
        out_buffers=["output"], out_extent=None,
        out_region={"rows": "block_width", "cols": "block_height",
                    "row_stride": "output_stride", "col_stride": f"sizeof({elem})"},
        elem=elem, kind=_kind(elem))


def _qd8_qc4w_gemm_fixture() -> "FixtureSpec":
    # qd8-f32-qc4w 1-row GEMM: int8 activations × packed 4-bit weights → f32 out.
    # ONE shared symbolic `w`; RUN --vlen 128 (NEON NR=16 == RVV vlmax(e32m4)).
    # Tile layout: ksum 16×i32 | (kc/2) nibble planes 16×u8 | scale 16×f32 | bias 16×f32.
    # raw_decls assert ksum ≡ 0 (mod 16) — the packer invariant. cvc5-only.
    tile = "(16 * 4 + ((kc + 1) / 2) * 16 + 16 * 4 + 16 * 4)"
    return FixtureSpec(
        dims={"mr": [1], "nc": [1, 2, 4, 5, 8, 15, 16], "kc": [2, 4, 6, 8, 10]},
        strides={"a_stride": "kc", "cm_stride": "nc * sizeof(float)",
                 "cn_stride": "16 * sizeof(float)"},
        extents={"a": "kc + 72",                       # +8 OOB pad (NEON vld1_s8 tail) +64
                 "w": f"((nc + 15) / 16) * {tile} + 64",
                 "c": "nc * sizeof(float) + 64"},
        out_buffers=["c"], out_extent=None,
        out_region={"rows": "mr", "cols": "nc",
                    "row_stride": "cm_stride", "col_stride": "sizeof(float)"},
        params=("xnn_f32_qc4w_minmax_params",
                {"scalar.min": "-1e30f", "scalar.max": "1e30f", "scalar.kernel_zero_point": "8"}),
        extra_params={"quantization_params": ("xnn_qd8_quantization_params",
                                              {"zero_point": "5", "inv_scale": "0.5f"})},
        index_reads=["a0"],
        raw_decls=[
            "    { auto& _tm = ctx.tm; Op _lo4 = _tm.mkOp(Kind::BITVECTOR_EXTRACT, {3, 0});",
            f"      size_t _tilesz = {tile};",
            "      size_t _fpoff = 16 * 4 + ((kc + 1) / 2) * 16;   // scale plane offset in tile",
            "      Term _flo = mk_fp32_from_float(ctx.tm, -1.0f), _fhi = mk_fp32_from_float(ctx.tm, 1.0f);",
            "      for (size_t _t = 0; _t < (nc + 15) / 16; _t++)",
            "        for (size_t _i = 0; _i < 16; _i++) {",
            "          Term _ks = _b_w.loadScalar(_t * _tilesz + _i * 4, 32);",
            "          ctx.solver->assertFormula(_tm.mkTerm(Kind::EQUAL, "
            "{_tm.mkTerm(_lo4, {_ks}), _tm.mkBitVector(4, 0)}));",
            "          // |ksum| <= 2048 (packer: ksum = 16*Σnibbles) — narrows the int→fp converters",
            "          Term _ks12 = _tm.mkTerm(_tm.mkOp(Kind::BITVECTOR_EXTRACT, {11, 0}), {_ks});",
            "          ctx.solver->assertFormula(_tm.mkTerm(Kind::EQUAL, "
            "{_ks, _tm.mkTerm(_tm.mkOp(Kind::BITVECTOR_SIGN_EXTEND, {20}), {_ks12})}));",
            "          // scale + bias planes finite [-1,1] — full-domain f32 bits are FP-blast-intractable",
            "          for (size_t _p = 0; _p < 2; _p++) {",
            "            Term _fp = load_as_fp32(ctx.tm, _b_w.loadScalar(_t * _tilesz + _fpoff + _p * 64 + _i * 4, 32));",
            "            ctx.assert_(ctx.land_(ctx.fp32_geq(_fp, _flo), ctx.fp32_leq(_fp, _fhi)));",
            "          }",
            "        } }",
        ],
        elem="int8_t", kind="SINT", out_elem="float", out_kind="F32")


def _qc8w_fixture(*, dynamic: bool, indirect: bool = False) -> "FixtureSpec":
    """NR=8, KR=1 byte layout shared by these three one-row NEON/RVV pairs.

    Each tile is [8*i32 correction/bias][ks_count*kc*8*i8][8*f32 scale],
    followed by [8*f32 bias] for qd8. No qc4w ksum/nibble constraints apply.
    Integers have their full bit-vector domain; packed FP planes are finite
    (scale nonnegative). Params are three concrete profiles, not symbolic.
    """
    depth = "(ks_count * kc)" if indirect else "kc"
    tile = f"(8 * sizeof(int32_t) + {depth} * 8 + {2 if dynamic else 1} * 8 * sizeof(float))"
    output = "float" if dynamic else "int8_t"
    dims = {"param_case": [0, 1, 2], "mr": [1],
            "nc": [1, 2, 3, 4, 5, 6, 7, 8, 9, 16, 17],
            "kc": [1, 2, 3, 4, 5, 6, 7, 8, 9, 16, 17]}
    strides = {"cm_stride": f"nc * sizeof({output})",
               "cn_stride": f"8 * sizeof({output})"}
    extents = {"w": f"((nc + 7) / 8) * {tile} + 64",
               "c": f"nc * sizeof({output}) + 64"}
    if dynamic:
        params = ("xnn_f32_minmax_params", {
            "scalar.min": "param_case == 0 ? -1e30f : (param_case == 1 ? -1.0f : -32.0f)",
            "scalar.max": "param_case == 0 ? 1e30f : (param_case == 1 ? 1.0f : 64.0f)",
        })
        extra_params = {"quantization_params": ("xnn_qd8_quantization_params", {
            "zero_point": "param_case == 0 ? 5 : (param_case == 1 ? 0 : -7)",
            "inv_scale": "param_case == 0 ? 0.5f : (param_case == 1 ? 1.0f : 2.0f)",
        })}
    else:
        params = ("xnn_qs8_qc8w_conv_minmax_params", {
            "fp32_neon.magic_bias": "12582912.0f",
            "fp32_neon.magic_bias_less_output_zero_point":
                "0x4B400000 - (param_case == 0 ? 0 : (param_case == 1 ? 5 : -7))",
            "fp32_neon.output_min": "param_case == 0 ? -128 : -64",
            "fp32_neon.output_max": "param_case == 0 ? 127 : 63",
        })
        extra_params = {}
    raw = [
        "    {",
        f"      const size_t _tile = {tile};",
        f"      const size_t _fp_off = 8 * sizeof(int32_t) + {depth} * 8;",
        "      Term _flo = mk_fp32_from_float(ctx.tm, -0x1.fffffep127f);",
        "      Term _fhi = mk_fp32_from_float(ctx.tm, 0x1.fffffep127f);",
        "      Term _zero = mk_fp32_from_float(ctx.tm, 0.0f);",
        "      for (size_t _t = 0; _t < (nc + 7) / 8; ++_t)",
        f"        for (size_t _p = 0; _p < {2 if dynamic else 1}; ++_p)",
        "          for (size_t _i = 0; _i < 8; ++_i) {",
        "            Term _fp = load_as_fp32(ctx.tm, _b_w.loadScalar(",
        "                _t * _tile + _fp_off + (_p * 8 + _i) * sizeof(float), 32));",
        "            ctx.assert_(ctx.land_(ctx.fp32_geq(_fp, _p == 0 ? _zero : _flo),",
        "                                  ctx.fp32_leq(_fp, _fhi)));",
        "          }",
        "    }",
    ]
    indirect_spec = {}
    weights = {}
    if indirect:
        # ks is a byte count of pointers; a_offset is bytes (int8 elements).
        # zero_mode covers no sentinel, all sentinel, and mixed pointer tables.
        dims["nc"] = [1, 4, 7, 8, 9, 17]
        dims["kc"] = [1, 7, 8, 9]
        dims.update(ks_count=[1, 3], a_offset=[0, 3], zero_mode=[0, 1, 2])
        strides["ks"] = "ks_count * sizeof(void*)"
        indirect_spec = {"a": {"count": "ks_count", "row": "a_offset + kc + 8"}}
        # A distinct sentinel address and replacement buffer. Symbolic zero_data
        # is stronger than assuming a particular quantized padding value.
        weights["zero"] = ("16", "0")
        extents["zero_data"] = "kc + 8"
        raw += [
            "    for (size_t _i = 0; _i < _a_rows; ++_i)",
            "      if (zero_mode == 1 || (zero_mode == 2 && _i % 2 == 0))",
            "        a_tbl[_i] = zero_arr.data();",
        ]
    else:
        strides["a_stride"] = "kc + 8"
        extents["a"] = "kc + 8"  # NEON loads 8 bytes even in the K tail.
    return FixtureSpec(
        dims=dims, strides=strides, extents=extents,
        out_buffers=["c"], out_extent="nc",
        elem="int8_t", kind="SINT", out_elem=output, out_kind=_kind(output),
        params=params, extra_params=extra_params, indirect=indirect_spec,
        weights=weights, raw_decls=raw, scalar_reads=["a0"], index_reads=["a0"],
        config_tag="qc8w_finite_fp_concrete_params_arm64",
        pre_defines=["#undef XNN_ARCH_ARM64", "#define XNN_ARCH_ARM64 1"])


def _qd8_qc8w_gemm_fixture() -> "FixtureSpec":
    return _qc8w_fixture(dynamic=True)


def _qd8_qc8w_igemm_fixture() -> "FixtureSpec":
    return _qc8w_fixture(dynamic=True, indirect=True)


def _qs8_qc8w_gemm_fixture() -> "FixtureSpec":
    return _qc8w_fixture(dynamic=False)


def _packw_fixture() -> "FixtureSpec":
    # x32-packw-x2-gemm-goi (NR=2, KR=1, SR=1): packs g groups of GOI weights+bias
    # into [bias×2][k-major 2-wide]… blocks + an extra_bytes gap. Pure BV → full domain.
    # Unwritten bytes (gaps + odd-nc bias slot) → shared_out; odd-nc remainder → scalar movs.
    # bias always non-NULL.
    blk_u32 = "(2 + 2 * kc + extra_bytes / sizeof(uint32_t))"   # block elems incl. gap
    return FixtureSpec(
        dims={"g": [1, 2], "nc": [1, 2, 3, 4, 5], "kc": [1, 2, 3, 4], "extra_bytes": [0, 8]},
        strides={"nr": "2", "kr": "1", "sr": "1"},
        extents={"weights": "g * nc * kc * sizeof(uint32_t) + 64",
                 "bias": "g * nc * sizeof(uint32_t) + 64",
                 "scale": "16", "params": "16",                   # unused void* args
                 "packed_weights": f"g * ((nc + 1) / 2) * {blk_u32} * sizeof(uint32_t) + 64"},
        out_buffers=["packed_weights"],
        out_extent=f"g * ((nc + 1) / 2) * {blk_u32}",
        shared_out=["packed_weights"], scalar_movs=True,
        elem="uint32_t", kind="UINT")


def _gemm_fixture() -> "FixtureSpec":
    # Full f32-gemm (mr≤4, nr=8): c[m][n] = clamp(bias[n] + Σ_k a[m][k]·w[k][n]).
    # kc in BYTES. Weights DUAL-PACKED (planes = 1+kc_floats: bias + weight rows,
    # NEON/RVV tile=8). Both reduce over k with FMA in identical order → kc>1 FP-safe.
    return FixtureSpec(
        dims={"mr": [1, 2, 3, 4], "nc": [1, 4, 8, 12], "kc": [4, 8]},   # mr 1-4 (both kernels 4-row); nc=12 → 2nd tile (cn_stride + a-rewind); kc BYTES
        strides={"a_stride": "kc",                       # a row pitch (bytes), tight
                 "cm_stride": "nc * sizeof(float)",      # c row pitch, tight
                 "cn_stride": "8 * sizeof(float)"},      # next nr-tile (unused at nc≤8)
        extents={"a": "mr * kc + 64", "c": "mr * cm_stride + 64"},
        out_buffers=["c"], out_extent=None,
        out_region={"rows": "mr", "cols": "nc",
                    "row_stride": "cm_stride", "col_stride": "sizeof(float)"},
        dual_weights={"w": {"planes": "1 + kc / sizeof(float)",   # bias + kc_floats weight rows
                            "ncols": "nc", "neon_tile": "8",
                            "rvv_tile": "8", "rvv_packed": False}},   # target does fixed `w += 8` (NR=8), NOT vlmax
        params=("xnn_f32_minmax_params",
                {"scalar.min": "-1e30f", "scalar.max": "1e30f"}),   # wide → no clamp
        elem="float", kind="F32")


# Per-element-type minmax params for the pool family: (struct, {field: concrete}).
# Wide ranges → the clamp is identity, so the result is the pure max-reduction;
# both sides apply the same clamp regardless, so equivalence is unaffected.
_MINMAX_PARAMS = {
    "float":   ("xnn_f32_minmax_params", {"scalar.min": "-1e30f", "scalar.max": "1e30f"}),
    "int8_t":  ("xnn_s8_minmax_params",  {"scalar.min": "-128",   "scalar.max": "127"}),
    "uint8_t": ("xnn_u8_minmax_params",  {"scalar.min": "0",      "scalar.max": "255"}),
}


def _maxpool_fixture(elem: str) -> "FixtureSpec":
    # Indirect-input: `const T** input` table of kernel_elements rows into a shared
    # symbolic buffer; per-channel max-reduction + [min,max] clamp. Max order matches
    # both sides → FULL domain (no input-range). f32 uses FP max, s8/u8 integer max.
    # GROW kernel_elements past the 9p pass boundary; inner set = channels×output_pixels.
    return FixtureSpec(
        dims={"channels": [1, 2, 3, 4, 5, 7, 8],
              "output_pixels": [1, 2]},
        grow_dim="kernel_elements",
        # Unused scalar args declared (and pinned) as zero-valued locals.
        strides={"input_offset": "0", "input_pixel_stride": "0",
                 "input_increment": "0", "output_increment": "0"},
        extents={"output": f"channels * sizeof({elem}) + 64"},
        out_buffers=["output"], out_extent="channels", out_region=None,
        # input[k] addresses [input_offset, input_offset+channels) elements per row.
        indirect={"input": {"count": "kernel_elements", "row": "input_offset + channels"}},
        params=_MINMAX_PARAMS[elem],
        elem=elem, kind=_kind(elem))


def _argmaxpool_fixture() -> "FixtureSpec":
    # Argmax pooling: per-channel max over a pooling_elements window, writing BOTH max
    # VALUES (float* output) and argmax POSITIONS (uint32_t* index) → dual MIXED-type
    # output (out_extents + out_elems). The two compares pin tie-breaking (strict `>`,
    # first-wins). GROW pooling_elements past the 9p8x boundary; inner = channels×output_pixels.
    return FixtureSpec(
        dims={"channels": [1, 2, 3, 4, 5, 7, 8], "output_pixels": [1, 2]},
        grow_dim="pooling_elements",
        # Unused scalar args declared (and pinned) as zero-valued locals.
        strides={"input_offset": "0", "input_pixel_stride": "0", "input_increment": "0",
                 "output_increment": "0", "index_increment": "0"},
        extents={"output": "channels * sizeof(float) + 64",
                 "index":  "channels * sizeof(uint32_t) + 64"},
        out_buffers=["output", "index"], out_extent=None, out_region=None,
        out_extents={"output": "channels", "index": "channels"},   # dual contiguous compare, ANDed
        out_elems={"output": "float", "index": "uint32_t"},        # mixed-type: values F32, indices UINT
        indirect={"input": {"count": "pooling_elements", "row": "input_offset + channels"}},
        params=None,                          # argmaxpool has no params struct
        elem="float", kind="F32")


def _igemm_fixture(ks: int = 1) -> "FixtureSpec":
    # Minimal igemm (a_offset=0; zero/params/strides voided). `a` is a T** table of
    # ks*mr row pointers, indexed a[p*mr + m]. `w` indexed identically both sides →
    # symbolic. FP-mul needs input-range. ks=1 base; ks=3 is igemm-ks3.
    kc_vals = [4, 8] if ks == 1 else [4]   # kc in BYTES (kc % sizeof(float)==0); ks*kc caps FP work
    return FixtureSpec(
        # mr=[1] only: kernel asserts mr<=1 (asserts off in Release → mr>1 is UB/crash).
        # nc 1/4/5/8 hits the NR=8 tail-store paths (nc&4, nc&2, nc&1) + the full tile.
        dims={"mr": [1], "nc": [1, 4, 5, 8], "kc": [4, 8]},  # kc BYTES (=1,2 floats)
        # ks in BYTES (count*sizeof(void*)); kernel does `p -= sizeof(void*)`, so the raw
        # count underflows the p-loop → SIGSEGV.
        strides={"ks": f"{ks} * sizeof(void*)", "a_offset": "0", "cm_stride": "0", "cn_stride": "0"},
        # NR=8: kernel reads a full 8-channel tile even for the nc<8 tail, so round nc up to
        # 8 — else partial tiles read OOB weights → crash/spurious CEX.
        extents={"w": f"((nc + 7) / 8) * 8 * (1 + {ks}*kc) * sizeof(float) + 64",
                 "c": "mr * nc * sizeof(float) + 64"},
        out_buffers=["c"], out_extent="mr * nc", out_region=None,
        indirect={"a": {"count": f"{ks} * mr", "row": "a_offset + kc"}},
        weights={"zero": ("16", "0.0f")},        # voided; concrete dummy → valid ptr
        params=("xnn_f32_minmax_params",         # WIDE bounds → no clamp (else min=max=0 → vacuous)
                {"scalar.min": "-1e30f", "scalar.max": "1e30f"}),
        elem="float", kind="F32")


def _dwconv_fixture(ksize: int = 3) -> "FixtureSpec":
    # Minimal depthwise conv, kernel_size=ksize (increments/strides/zero/params voided).
    # `input` is a T** table of output_width*ksize rows. Weights same layout both sides
    # → symbolic. FP-mul needs input-range. ksize=3 base; ksize=9 is dwconv-9p.
    ow_vals = [1, 2] if ksize <= 3 else [1]      # ksize products/output — cap work
    return FixtureSpec(
        dims={"output_width": ow_vals},          # inner representative set; channels is grow_dim
        grow_dim="channels",                     # grow channels 1,2,3,… until budget (soak: saturates ~8)
        strides={"input_stride": "0", "output_increment": "0",
                 "input_offset": "0", "input_pixel_stride": "0"},
        extents={"weights": f"channels * {ksize + 1} * sizeof(float) + 64",   # bias + ksize taps
                 "output": "output_width * channels * sizeof(float) + 64"},
        out_buffers=["output"], out_extent="output_width * channels", out_region=None,
        indirect={"input": {"count": f"output_width * {ksize}", "row": "input_offset + channels"}},
        weights={"zero": ("16", "0.0f")},        # voided; concrete dummy → valid ptr
        params=("xnn_f32_minmax_params", {}),    # voided; declared so &params is valid
        elem="float", kind="F32")


def _rdsum_fixture(elem: str, out_elem: str) -> "FixtureSpec":
    # Column reduction over a rows×channels matrix: output[c] += Σ_r input[r*input_stride+c].
    # int8/uint8 input, int32/uint32 INOUT output. NEON ref is the 7p7x variant. `zero` MUST
    # be a CONCRETE all-zeros buffer — the kernel's caller contract, load-bearing for
    # equivalence (a symbolic zero yields real CEX once channels exceed one NEON block).
    # ROWS GROW unbounded; channels = fixed representative set hitting every tail path.
    # Odd channels route the last lane through a scalar `*out += vgetq_lane` store → odd_tail_dim.
    return FixtureSpec(
        dims={"channels": [1, 2, 4, 7, 8, 15, 16, 17, 32, 33]},   # representative configs; rows is grow_dim
        grow_dim="rows",                              # rows grow 1,2,3,… until budget — unbounded verification
        strides={"input_stride": "channels"},        # tight row pitch (bytes; int8 ⇒ =channels)
        extents={"input": "rows * input_stride + 64",                 # symbolic matrix + OOB pad
                 "output": f"channels * sizeof({out_elem}) + 64"},
        out_buffers=["output"], out_extent="channels", out_region=None,
        weights={"zero": ("channels + 64", "0")},     # concrete all-zeros padding row (contract)
        params=("xnn_qs8_rsum_params", {}),           # dummy struct (unused; &params must be valid)
        odd_tail_dim="channels",   # odd channel → scalar `*out += vgetq_lane` tail (captured via side-channel)
        elem=elem, kind=_kind(elem), out_elem=out_elem, out_kind=_kind(out_elem))


def _strided_slice_fixture() -> "FixtureSpec":
    # y[i] = x[i*stride] — pure strided gather, no arithmetic → full-domain (the
    # FP-aware compare is bit-exact for a copy). Two bounds (n_out, stride); x is
    # read at stride steps so its extent is n_out*stride.
    return FixtureSpec(
        dims={"n_out": [1, 2, 4, 5, 8], "stride": [1, 2, 3]},
        strides={},
        extents={"x": "n_out * stride * sizeof(float) + 64",
                 "y": "n_out * sizeof(float) + 64"},
        out_buffers=["y"], out_extent="n_out", out_region=None,
        elem="float", kind="F32")


def _dwconv2d_chw_fixture() -> "FixtureSpec":
    # 3x3 s1 p1 depthwise conv on ONE channel plane (CHW), direct 2D. input/output are
    # flat H×cols planes (input_width is a BYTE pitch). Output contiguous → flat compare.
    # `weights` = bias + 9 taps (symbolic). `zero` = CONCRETE all-zeros halo. padding_top==1.
    # Small fixed grid (not production sizes — intractable for cvc5 FP); conv is local +
    # size-invariant so it covers all behaviors. FP-mul ⇒ needs --input-range.
    return FixtureSpec(
        dims={"input_height": [1, 2, 3, 4, 5, 6], "input_width": [16, 20, 32]},  # input_width in BYTES
        strides={"padding_top": "1"},                 # asserted == 1
        extents={"input": "input_height * input_width + 256",   # flat H×cols plane + OOB pad
                 "weights": "10 * sizeof(float) + 64",          # bias + 3x3 taps
                 "output": "input_height * input_width + 256"},
        out_buffers=["output"],
        out_extent="input_height * input_width / sizeof(float)",  # H*cols contiguous elements
        out_region=None,
        weights={"zero": ("input_width + 64", "0.0f")},          # concrete all-zeros halo row
        params=_MINMAX_PARAMS["float"],
        elem="float", kind="F32")


def _conv_hwc2chw_fixture() -> "FixtureSpec":
    # 3x3 s2 p1 FULL conv, 3 input channels (RGB), HWC in → CHW out (MobileNet first layer).
    # `input` HWC interleaved; `weights` = bias + 3 ic × 3x3 per oc (28 floats/oc); `zero` =
    # CONCRETE all-zeros HWC halo. CHW output with contiguous strides → flat compare.
    # Derived: output_width=(input_width+1)/2, H_out=(input_height+1)/2 (stride 2). Small grid
    # (not the 224x224x3 production size — ~150k symbolic floats, hopeless for cvc5 FP); conv
    # is local + size-invariant so it covers production behavior. FP-mul ⇒ needs --input-range.
    # Budget-gated (cheapest-first until --timeout); symbolic weights are ~88s/shape and grow.
    return FixtureSpec(
        dims={"input_height": [1, 2, 3, 4, 5],
              "input_width": [2, 3, 4, 5, 7, 8],
              "output_channels": [1, 2, 3, 4, 5, 8]},
        strides={"output_y_start": "0",
                 "output_y_end": "(input_height + 1) / 2",          # H_out (stride 2)
                 "input_padding_top": "1",
                 "output_height_stride": "((input_width + 1) / 2) * sizeof(float)",                       # contiguous rows
                 "output_channel_stride": "((input_height + 1) / 2) * ((input_width + 1) / 2) * sizeof(float)"},  # contiguous planes
        extents={"input": "input_height * input_width * 3 * sizeof(float) + 256",   # HWC + OOB pad
                 # round output_channels up to a multiple of 4 — the kernel reads a FULL
                 # 4-channel block per group, else partial tiles read OOB weights → spurious CEX.
                 "weights": "((output_channels + 3) / 4) * 4 * 28 * sizeof(float) + 64",
                 "output": "output_channels * ((input_height + 1) / 2) * ((input_width + 1) / 2) * sizeof(float) + 64"},
        out_buffers=["output"],
        out_extent="output_channels * ((input_height + 1) / 2) * ((input_width + 1) / 2)",  # CHW contiguous
        out_region=None,
        weights={"zero": ("input_width * 3 * sizeof(float) + 64", "0.0f")},   # concrete all-zeros HWC halo row
        params=_MINMAX_PARAMS["float"],
        elem="float", kind="F32")


def _concat2_fixture() -> "FixtureSpec":
    # y = [a[0..na-1], b[0..nb-1]] — pure concatenation, full-domain. Two inputs,
    # one contiguous output of na+nb (both halves fully written).
    return FixtureSpec(
        dims={"na": [1, 2, 4, 5], "nb": [1, 2, 3, 8]},
        strides={},
        extents={"a": "na * sizeof(float) + 64",
                 "b": "nb * sizeof(float) + 64",
                 "y": "(na + nb) * sizeof(float) + 64"},
        out_buffers=["y"], out_extent="na + nb", out_region=None,
        elem="float", kind="F32")


def _split2_fixture() -> "FixtureSpec":
    # a = x[0..na-1]; b = x[na..na+nb-1] — pure split, full-domain. ONE input,
    # TWO contiguous outputs (a:na, b:nb) — exercises the multi-output compare.
    return FixtureSpec(
        dims={"na": [1, 2, 4, 5], "nb": [1, 2, 3, 8]},
        strides={},
        extents={"x": "(na + nb) * sizeof(float) + 64",
                 "a": "na * sizeof(float) + 64",
                 "b": "nb * sizeof(float) + 64"},
        out_buffers=["a", "b"], out_extent=None, out_region=None,
        out_extents={"a": "na", "b": "nb"},   # per-output element counts, ANDed
        elem="float", kind="F32")


def _vmulcaddc_fixture() -> "FixtureSpec":
    # 2-row per-channel: output = clamp(input*scale + bias). `channels` in BYTES.
    # Weights DUAL-PACKED (NEON scale[4]+bias[4] per 4-float tile; RVV per VLMAX(e32m4)
    # tile) from ONE shared symbolic logical set → both recover the same scale/bias at any
    # vlen. FP-mul → input-range.
    return FixtureSpec(
        dims={"rows": [1, 2, 3], "channels": [4, 16, 20, 32, 48]},   # BYTES; 20=5 floats (tail)
        strides={"input_stride": "channels", "output_stride": "channels"},   # tight (contiguous rows)
        extents={"input": "rows * channels + 64",
                 "output": "rows * channels + 64"},
        out_buffers=["output"], out_extent="rows * (channels / sizeof(float))", out_region=None,
        dual_weights={"weights": {"planes": "2",                         # plane0=scale, plane1=bias
                                  "ncols": "channels / sizeof(float)",   # logical channels
                                  "neon_tile": "4",                      # NEON fixed block
                                  "rvv_tile": "(vlen / 32) * 4",         # RVV VLMAX(e32m4)
                                  "rvv_packed": True}},                  # RVV advances by chunk (w += 2*vl)
        params=("xnn_f32_minmax_params", {"scalar.min": "-1e30f", "scalar.max": "1e30f"}),
        elem="float", kind="F32")


def _ibilinear_fixture() -> "FixtureSpec":
    # Bilinear interp (decomposed, no FMA → matched FP order). `input` is a T** table of
    # output_pixels*4 corner pointers. `weights` = alphah,alphav per pixel, broadcast both
    # sides → symbolic shared. FP sub/mul/add → input-range. No params struct.
    return FixtureSpec(
        dims={"channels": [1, 2, 4, 5, 8], "output_pixels": [1, 2]},
        strides={"input_offset": "0", "output_increment": "0"},
        extents={"weights": "output_pixels * 2 * sizeof(float) + 64",
                 "output": "output_pixels * channels * sizeof(float) + 64"},
        out_buffers=["output"], out_extent="output_pixels * channels", out_region=None,
        indirect={"input": {"count": "output_pixels * 4", "row": "input_offset + channels"}},
        elem="float", kind="F32")


def _match_fixture(sig, src=""):
    # `src` lets us read a size constant the signature can't reveal (igemm/igemm-ks3
    # and dwconv/dwconv-9p share identical signatures — only `ks`/tap-count differ).
    names = {p.name for p in sig.params}
    structs = {p.struct_name for p in sig.params if p.is_struct_ptr}
    if {"mr", "nc", "kc", "w", "c"} <= names:
        # Quantization and pointer-table arguments alone do not determine the
        # weight layout. Dispatch quantized families before generic f32 GEMM.
        if "xnn_qs8_qc8w_conv_minmax_params" in structs:
            return _qs8_qc8w_gemm_fixture()
        if "quantization_params" in names:
            if "xnn_f32_qc4w_minmax_params" in structs:
                return _qd8_qc4w_gemm_fixture()
            if "xnn_f32_minmax_params" in structs:
                if {"ks", "zero", "zero_data", "a_offset"} <= names:
                    return _qd8_qc8w_igemm_fixture()
                if "a_stride" in names:
                    return _qd8_qc8w_gemm_fixture()
            raise NotImplementedError("quantized GEMM signature needs an explicit weight-layout fixture")
    if {"input_height", "input_width", "padding_top"} <= names:
        return _dwconv2d_chw_fixture()    # 3x3 s1 p1 depthwise on a CHW plane (direct 2D)
    if {"input_height", "input_width", "output_y_start", "output_channels"} <= names:
        return _conv_hwc2chw_fixture()    # 3x3 s2 p1 c3 full conv, HWC in -> CHW out
    if {"input_stride", "output_stride", "block_width", "block_height"} <= names:
        elem = next((p.pointee for p in sig.params if p.is_pointer), "uint32_t")
        return _transpose_fixture(elem)   # element width from the buffer type
    if {"rows", "channels", "input_stride", "output_stride", "weights"} <= names:
        return _vmulcaddc_fixture()       # 2-row scale+bias+clamp (dual-packed weights)
    if ({"rows", "channels", "input_stride", "zero"} <= names
            and "output_stride" not in names and "weights" not in names):
        # rdsum: int8/uint8 input → int32/uint32 INOUT column-sum, concrete-zero padding.
        inp = next(p for p in sig.params
                   if p.is_pointer and p.points_to_const and p.name == "input")
        outp = next(p for p in sig.params
                    if p.is_pointer and not p.points_to_const and p.name == "output")
        ie = {"signed char": "int8_t", "unsigned char": "uint8_t"}.get(inp.pointee, inp.pointee)
        oe = {"int": "int32_t", "unsigned int": "uint32_t"}.get(outp.pointee, outp.pointee)
        return _rdsum_fixture(ie, oe)
    if ({"mr", "nc", "kc", "ks"} <= names
            and any(p.is_ptr_to_ptr for p in sig.params)):
        m = re.search(r'\bks\s*==\s*(\d+)', src)          # assert(ks == N)
        return _igemm_fixture(int(m.group(1)) if m else 1)
    if ({"channels", "output_width", "weights", "input_offset"} <= names
            and any(p.is_ptr_to_ptr for p in sig.params)):
        m = re.search(r'input\s*\[\s*ow\s*\*\s*(\d+)', src)  # input[ow * K + ...]
        return _dwconv_fixture(int(m.group(1)) if m else 3)
    if ({"output_pixels", "channels", "weights"} <= names
            and "kernel_elements" not in names
            and any(p.is_ptr_to_ptr for p in sig.params)):
        return _ibilinear_fixture()       # indirect 4-corner bilinear (f32)
    if {"n_out", "stride", "x", "y"} <= names and len(sig.params) == 4:
        return _strided_slice_fixture()   # pure strided gather (copy)
    if {"na", "nb", "a", "b", "y"} <= names and len(sig.params) == 5:
        return _concat2_fixture()         # pure concatenation (2 in → 1 out)
    if {"na", "nb", "x", "a", "b"} <= names and len(sig.params) == 5:
        return _split2_fixture()          # pure split (1 in → 2 out, multi-output compare)
    if {"mr", "nc", "kc", "a_stride", "cm_stride", "cn_stride"} <= names:
        return _gemm_fixture()
    if {"g", "nc", "kc", "nr", "kr", "sr", "extra_bytes"} <= names:
        return _packw_fixture()           # x32-packw NR=2 GOI weight packing (pure BV)
    if ({"output_pixels", "pooling_elements", "channels", "index"} <= names
            and any(p.is_ptr_to_ptr for p in sig.params)):
        return _argmaxpool_fixture()      # f32 dual-output: max values + argmax indices
    if ({"output_pixels", "kernel_elements", "channels", "input_offset"} <= names
            and any(p.is_ptr_to_ptr for p in sig.params)):
        # `const float**` pointee normalizes to "float *" — strip the inner `*`.
        # libclang canonicalizes int8_t→"signed char"; map back to the stdint name.
        ind = next(p.pointee for p in sig.params if p.is_ptr_to_ptr)
        elem = ind.replace("*", "").strip()
        elem = {"signed char": "int8_t", "unsigned char": "uint8_t"}.get(elem, elem)
        if elem in _MINMAX_PARAMS:        # f32/s8/u8 maxpool; f16 defers.
            return _maxpool_fixture(elem)
    return None


def generate_multidim(neon_path, rvv_path, name, neon, rvv, spec, input_range=None) -> str:
    weights = set(spec.weights)
    indirect = set(spec.indirect)
    dual = set(spec.dual_weights)
    param_names = {p.name for p in neon.params if p.is_struct_ptr}
    inputs = [p.name for p in neon.params
              if p.is_pointer and p.points_to_const and not p.is_struct_ptr
              and not p.is_ptr_to_ptr
              and p.name not in spec.dims and p.name not in weights and p.name not in dual]
    outputs = [p.name for p in neon.params
               if p.is_pointer and not p.points_to_const and not p.is_ptr_to_ptr
               and p.name not in spec.dims]
    elem = spec.elem
    oelem, okind = spec.out_elem, spec.out_kind   # output type (rdsum: int8 in, int32 out)
    ulp_tol = _ulp_tol_for(name)                  # 0 = bit-exact; >0 relaxes FP outputs to a ULP bound
    neon_src, rvv_src = open(neon_path).read(), open(rvv_path).read()
    decls = [f"    const size_t {s} = {e};" for s, e in spec.strides.items()]
    # Indirect inputs: `const T** name` is a table of `count` row pointers into one
    # shared symbolic buffer. Both kernels read the same table → same symbols, so
    # an intrinsic load resolves to identical bytes on each side.
    _ibind = "bindScalarRef" if elem in _FP_CTYPES else "bind"  # FP indirect rows read scalar-wise (RVV vfmacc_vf)
    for nm, spc in spec.indirect.items():
        cnt, row = spc["count"], spc["row"]
        decls += [
            f"    const size_t _{nm}_rows = ({cnt}), _{nm}_row = ({row});  // ptr count, elems/row",
            f"    std::vector<{elem}> {nm}_data(_{nm}_rows * _{nm}_row + 16, 0);",
            # +16 elem slack matches the backing pad so XNN_OOB_READS tail over-reads stay in-bounds
            f'    auto& _b_{nm} = ctx.registerBuffer("{nm}", (_{nm}_rows * _{nm}_row + 16) * sizeof({elem})); _b_{nm}.{_ibind}({nm}_data.data());',
            f"    std::vector<const {elem}*> {nm}_tbl(_{nm}_rows);",
            f"    for (size_t _k = 0; _k < _{nm}_rows; _k++) {nm}_tbl[_k] = {nm}_data.data() + _k * _{nm}_row;",
        ]
    # extents are byte-counts; size the typed backing array to cover them.
    nelem = lambda ext: f"({ext}) / sizeof({elem}) + 1"
    # FP inputs may be read scalar-wise (`*a0++` → `_vf_`); the NaN-payload
    # sentinel bridges those reads to the same symbolic bytes the intrinsic
    # loads see. Int inputs use the salt_scalar rewrite instead.
    bindm = "bindScalarRef" if elem in _FP_CTYPES else "bind"
    for b in inputs:                    # symbolic inputs (e.g. activations)
        ext = spec.extents[b]
        decls += [f"    std::vector<{elem}> {b}_arr({nelem(ext)}, 0);",
                  f'    auto& _b_{b} = ctx.registerBuffer("{b}", ({ext})); _b_{b}.{bindm}({b}_arr.data());']
    for b in outputs:
        ext = spec.extents[b]
        _oeb = spec.out_elems.get(b, oelem)         # per-output C type (argmaxpool: output=float, index=uint32_t)
        _onb = f"({ext}) / sizeof({_oeb}) + 1"      # backing count in that type
        # In-out / accumulator outputs (rdsum: `output += Σ`) load prior contents, so
        # both sides must start from ONE shared symbolic image; pure-write outputs keep
        # independent poison so a missing write is caught.
        inout = (_output_is_read(neon_src, b) or _output_is_read(rvv_src, b)
                 or b in spec.shared_out)   # unwritten holes (packw gaps) need one shared image too
        decls += [f"    std::vector<{_oeb}> {b}_neon_arr({_onb}, 0), {b}_rvv_arr({_onb}, 0);",
                  f'    auto& _b_{b}_neon = ctx.registerBuffer("{b}_neon", ({ext})); _b_{b}_neon.bind({b}_neon_arr.data());',
                  f'    auto& _b_{b}_rvv  = ctx.registerBuffer("{b}_rvv",  ({ext})); _b_{b}_rvv.bind({b}_rvv_arr.data());']
        if inout:
            decls.append(
                f'    for (size_t _i = 0; _i < ({ext}); _i++) '
                f'_b_{b}_rvv.setByte(_i, _b_{b}_neon.getByte(_i));  // shared init (in-out)')
    for b, (ext, fill) in spec.weights.items():   # concrete uniform weights (layout-invariant)
        decls += [f"    std::vector<{elem}> {b}_arr({nelem(ext)}, {fill});",
                  f'    ctx.registerConcreteBuffer("{b}", {b}_arr.data(), ({ext}));']
    ebits = _BYTES[elem] * 8
    # Dual-packed weights: one shared symbolic logical set `wlog` (plane-major:
    # wlog[p*N + col]) is placed into TWO physical buffers at each dialect's tile
    # offsets. `planes` = logical planes per column (vmulcaddc: 2 = scale,bias;
    # GEMM: 1+kc_floats = bias + weight rows). NEON tiles are uniform/padded (width
    # neon_tile); RVV tiles are `rvv_packed` (advance by chunk, vmulcaddc) or padded
    # (advance by full tile, GEMM `w += nr`). Both kernels recover wlog[p*N+col].
    for nm, dw in spec.dual_weights.items():
        P, N, NT, RT = dw["planes"], dw["ncols"], dw["neon_tile"], dw["rvv_tile"]
        packed = dw.get("rvv_packed", False)
        decls += [
            f"    const size_t _{nm}_P = ({P}), _{nm}_N = ({N});  // planes, logical columns",
            f'    auto& _wlog_{nm} = ctx.registerBuffer("{nm}_log", _{nm}_P * _{nm}_N * sizeof({elem}));',
            f"    const size_t _{nm}_NT = ({NT});",
            f"    std::vector<{elem}> {nm}_neon_arr(((_{nm}_N + _{nm}_NT - 1) / _{nm}_NT) * _{nm}_P * _{nm}_NT + 8, 0);",
            f'    auto& _wN_{nm} = ctx.registerBuffer("{nm}_neon", {nm}_neon_arr.size() * sizeof({elem})); _wN_{nm}.bind({nm}_neon_arr.data());',
            f"    size_t _{nm}_RT = ({RT}); if (_{nm}_RT < 1) _{nm}_RT = 1;",
            f"    std::vector<{elem}> {nm}_rvv_arr(((_{nm}_N + _{nm}_RT - 1) / _{nm}_RT) * _{nm}_P * _{nm}_RT + 8, 0);",
            f'    auto& _wR_{nm} = ctx.registerBuffer("{nm}_rvv", {nm}_rvv_arr.size() * sizeof({elem})); _wR_{nm}.bind({nm}_rvv_arr.data());',
            f"    for (size_t _col = 0; _col < _{nm}_N; _col++) {{",
            f"      size_t _t = _col / _{nm}_NT, _j = _col % _{nm}_NT;",
            f"      for (size_t _p = 0; _p < _{nm}_P; _p++) {{",
            f"        Term _v = _wlog_{nm}.loadScalar((_p * _{nm}_N + _col) * sizeof({elem}), {ebits});",
            f"        _wN_{nm}.storeScalar((_t * _{nm}_P * _{nm}_NT + _p * _{nm}_NT + _j) * sizeof({elem}), _v, {ebits});",
            f"      }}",
            f"    }}",
        ]
        if packed:   # RVV chunked: tile width vl=min(remaining,RT), offset advances by P*vl
            decls += [
                f"    {{ size_t _off = 0, _c = 0;",
                f"      while (_c < _{nm}_N) {{",
                f"        size_t _vl = (_{nm}_N - _c < _{nm}_RT) ? (_{nm}_N - _c) : _{nm}_RT;",
                f"        for (size_t _j = 0; _j < _vl; _j++)",
                f"          for (size_t _p = 0; _p < _{nm}_P; _p++) {{",
                f"            Term _v = _wlog_{nm}.loadScalar((_p * _{nm}_N + _c + _j) * sizeof({elem}), {ebits});",
                f"            _wR_{nm}.storeScalar((_off + _p * _vl + _j) * sizeof({elem}), _v, {ebits});",
                f"          }}",
                f"        _off += _{nm}_P * _vl; _c += _vl;",
                f"      }} }}",
            ]
        else:        # RVV padded: uniform tiles of width RT (advance by P*RT, like GEMM `w += nr`)
            decls += [
                f"    for (size_t _col = 0; _col < _{nm}_N; _col++) {{",
                f"      size_t _t = _col / _{nm}_RT, _j = _col % _{nm}_RT;",
                f"      for (size_t _p = 0; _p < _{nm}_P; _p++) {{",
                f"        Term _v = _wlog_{nm}.loadScalar((_p * _{nm}_N + _col) * sizeof({elem}), {ebits});",
                f"        _wR_{nm}.storeScalar((_t * _{nm}_P * _{nm}_RT + _p * _{nm}_RT + _j) * sizeof({elem}), _v, {ebits});",
                f"      }}",
                f"    }}",
            ]
    if spec.params:                     # concrete params struct (plain-C field reads)
        st, fields = spec.params
        decls.append(f"    {st} params{{}};")
        decls += [f"    params.{f} = {v};" for f, v in fields.items()]
        decls.append(f'    ctx.registerConcreteBuffer("params", &params, sizeof({st}));')
    for pname, (st, fields) in spec.extra_params.items():  # extra concrete param structs (qd8)
        decls.append(f"    {st} {pname}_v{{}};")
        decls += [f"    {pname}_v.{f} = {v};" for f, v in fields.items()]
        decls.append(f'    ctx.registerConcreteBuffer("{pname}", &{pname}_v, sizeof({st}));')
    if input_range and elem == "float":  # optional: restrict F32 inputs to finite [lo,hi]
        lo, hi = input_range
        for b in inputs:                  # element count within capacity (floor, no +1)
            decls += _emit_input_range(f"_b_{b}", f"({spec.extents[b]}) / sizeof({elem})", lo, hi)
        for nm in spec.indirect:          # indirect-input bytes also need the finite band
            decls += _emit_input_range(f"_b_{nm}", f"_{nm}_rows * _{nm}_row", lo, hi)
        for nm in spec.dual_weights:       # logical weights (shared by both packings)
            decls += _emit_input_range(f"_wlog_{nm}", f"_{nm}_P * _{nm}_N", lo, hi)
    decls += spec.raw_decls             # raw constraint lines (e.g. qd8 ksum ≡ 0 mod 16)
    cfg_tag = spec.config_tag or ("finite" if input_range else "symbolic")

    def call_args(side):
        out = []
        for p in neon.params:
            if p.name in inputs or p.name in weights:
                out.append(f"{p.name}_arr.data()")
            elif p.name in dual:        # dual-packed weights: each side gets its own layout
                out.append(f"{p.name}_neon_arr.data()" if side == "neon"
                           else f"{p.name}_rvv_arr.data()")
            elif p.name in indirect:
                out.append(f"{p.name}_tbl.data()")
            elif p.name in outputs:
                out.append(f"{p.name}_{side}_arr.data()")
            elif p.name in spec.extra_params:   # before param_names: both are struct ptrs
                out.append(f"&{p.name}_v")
            elif p.name in param_names:
                out.append("&params")
            else:                       # dim or stride → pass by name (local/arg)
                out.append(p.name)
        return ", ".join(out)

    if spec.out_extents:                # multi-output: AND a contiguous compare per output
        terms = [f"buffers_equal(ctx.tm, _b_{ob}_neon, _b_{ob}_rvv, {ext}, "
                 f"sizeof({spec.out_elems.get(ob, oelem)}), ElementKind::{_kind(spec.out_elems.get(ob, oelem))}, {ulp_tol})"
                 for ob, ext in spec.out_extents.items()]
        cmp_expr = terms[0]
        for t in terms[1:]:
            cmp_expr = f"ctx.land_({cmp_expr}, {t})"
    else:
        ob = spec.out_buffers[0]
        if spec.out_region:             # strided affine output region
            r = spec.out_region
            cmp_expr = (f"buffers_equal_strided(ctx.tm, _b_{ob}_neon, _b_{ob}_rvv, "
                        f"{r['rows']}, {r['cols']}, {r['row_stride']}, {r['col_stride']}, "
                        f"sizeof({oelem}), ElementKind::{okind}, {ulp_tol})")
        else:
            cmp_expr = (f"buffers_equal(ctx.tm, _b_{ob}_neon, _b_{ob}_rvv, "
                        f"{spec.out_extent}, sizeof({oelem}), ElementKind::{okind}, {ulp_tol})")
    # Counterexample witness: on SAT, scan the (first) output buffer for the first
    # differing element and extract both models, so the repair LLM gets an actionable
    # "channel C: NEON=x RVV=y" instead of an empty shape. Strided/multi-output regions
    # report the first diff in the leading region; contiguous outputs scan [0,count).
    obits = _BYTES[oelem] * 8
    if spec.out_extents:
        _wob, _wcount = next(iter(spec.out_extents.items()))[0], next(iter(spec.out_extents.values()))
        _woff = f"e * sizeof({oelem})"
    elif spec.out_region:
        r = spec.out_region
        _wob, _wcount = spec.out_buffers[0], f"({r['rows']}) * ({r['cols']})"
        _woff = f"(e / ({r['cols']})) * ({r['row_stride']}) + (e % ({r['cols']})) * ({r['col_stride']})"
    else:
        _wob, _wcount = spec.out_buffers[0], spec.out_extent
        _woff = f"e * sizeof({oelem})"
    _din = inputs[0] if (inputs and inputs[0] in spec.extents) else None
    _cexin = ((f"      fprintf(stderr, \"CEX_IN:\");\n"
               f"      for (size_t _e = 0; _e < ({spec.extents[_din]})/sizeof({elem}); _e++) "
               f"fprintf(stderr, \" %lu\", strtoul(ctx.solver->getValue(_b_{_din}.loadScalar(_e*sizeof({elem}), {ebits})).getBitVectorValue(10).c_str(), nullptr, 10));\n"
               f"      fprintf(stderr, \"\\n\");\n") if _din else "")
    # Under a ULP tolerance the first BIT-differing element may still be within
    # tol; flag the first element whose ULP distance actually EXCEEDS tol, so the
    # repair hint names a genuine violator. Exact (tol=0) keeps raw bit inequality.
    _store = f"fi = e; _nv = (long long)({oelem})_nu; _vv = (long long)({oelem})_vu; break;"
    if ulp_tol and oelem in _FP_CTYPES:
        _wb = obits - 1
        _wit_cmp = (
            f"        long long _ka = ((_nu >> {_wb}) & 1ULL) ? ((long long)(1ULL << {_wb}) - (long long)_nu) : (long long)_nu;\n"
            f"        long long _kb = ((_vu >> {_wb}) & 1ULL) ? ((long long)(1ULL << {_wb}) - (long long)_vu) : (long long)_vu;\n"
            f"        long long _ud = (_ka > _kb) ? (_ka - _kb) : (_kb - _ka);\n"
            f"        if (_ud > {ulp_tol}LL) {{ {_store} }}\n")
    else:
        _wit_cmp = f"        if (_nu != _vu) {{ {_store} }}\n"
    cex_witness = (
        f"    size_t fi = 0; long long _nv = 0, _vv = 0;\n"
        f"    for (size_t e = 0; e < ({_wcount}); e++) {{\n"
        f"        size_t _off = {_woff};\n"
        f"        Term _n = ctx.solver->getValue(_b_{_wob}_neon.loadScalar(_off, {obits}));\n"
        f"        Term _v = ctx.solver->getValue(_b_{_wob}_rvv.loadScalar(_off, {obits}));\n"
        f"        unsigned long long _nu = strtoull(_n.getBitVectorValue(10).c_str(), nullptr, 10);\n"
        f"        unsigned long long _vu = strtoull(_v.getBitVectorValue(10).c_str(), nullptr, 10);\n"
        + _wit_cmp +
        f"    }}\n"
        f"    if (std::getenv(\"SALT_CEX_DUMP\")) {{\n"
        + _cexin +
        f"      fprintf(stderr, \"CEX_NEON:\");\n"
        f"      for (size_t _e = 0; _e < ({_wcount}); _e++) "
        f"fprintf(stderr, \" %lu\", strtoul(ctx.solver->getValue(_b_{_wob}_neon.loadScalar(_e*sizeof({oelem}), {obits})).getBitVectorValue(10).c_str(), nullptr, 10));\n"
        f"      fprintf(stderr, \"\\nCEX_RVV:\");\n"
        f"      for (size_t _e = 0; _e < ({_wcount}); _e++) "
        f"fprintf(stderr, \" %lu\", strtoul(ctx.solver->getValue(_b_{_wob}_rvv.loadScalar(_e*sizeof({oelem}), {obits})).getBitVectorValue(10).c_str(), nullptr, 10));\n"
        f"      fprintf(stderr, \"\\n\"); fflush(stderr);\n"
        f"    }}"
    )
    # Odd-tail scalar store: rsum/rdsum write the final output lane via a native
    # `*out += vgetq_lane(...)` with no vector-store shim. vgetq_lane stashes the lane
    # in the scalar side-channel; reconstruct `prior + lane` into the NEON buffer's last
    # lane so the existing buffer compare covers the odd channel.
    if spec.odd_tail_dim:
        _otb, _od = spec.out_buffers[0], spec.odd_tail_dim
        scalar_tail_clear = "    ctx.clear_scalar_result();\n"
        scalar_tail_inject = (
            f"\n    if ((({_od}) & 1) && ctx.has_scalar_result()) {{\n"
            f"        size_t _olo = (({_od}) - 1) * sizeof({oelem});\n"
            f"        Term _oprior = _b_{_otb}_neon.loadScalar(_olo, {obits});\n"
            f"        _b_{_otb}_neon.storeScalar(_olo, ctx.add(_oprior, ctx.scalar_result()), {obits});\n"
            f"    }}"
        )
    else:
        scalar_tail_clear = scalar_tail_inject = ""
    grow = spec.grow_dim                       # dim to grow continuously (unbounded sweep), else None
    gcross = spec.grow_cross                    # (d0, d1) grown cross-product-wise (expanding square), else None
    inner_dims = [] if gcross else list(spec.dims)   # cross-product dims (the representative configs)
    if gcross:
        dims = list(gcross)                    # verify() takes both grown dims
    elif grow:
        dims = [grow] + inner_dims             # verify() still takes ALL dims
    else:
        dims = inner_dims
    dim_sig = ", ".join(f"size_t {d}" for d in dims)
    dim_call = ", ".join(dims)
    dimfmt = ",".join("%zu" for _ in dims)

    def nest(i):   # fixed cross-product grid (non-grow mode)
        if i == len(dims):
            # Each combo's query gets the remaining total budget; once it's spent,
            # the rest of the grid reports TIMEOUT without running.
            return (
                f'        if (budget > 0.0 && _rem() <= 0.0) {{\n'
                f'            printf("{{\\"status\\":\\"TIMEOUT\\",\\"dims\\":\\"{dimfmt}\\",\\"config\\":\\"{cfg_tag}\\"}}\\n", {dim_call});\n'
                f'        }} else {{\n'
                f'            int _r = verify({dim_call}, vlen, _rem());\n'
                f'            if (_r == 1) return 1;\n'
                f'        }}')
        d = dims[i]
        vals = ", ".join(str(v) for v in spec.dims[d])
        return (f"      for (size_t {d} : {{{vals}}}) {{\n{nest(i + 1)}\n      }}")

    def grow_inner(i):   # inner cross-product over the representative configs, with per-batch gate
        if i == len(inner_dims):
            return (
                "          if (budget > 0.0 && _rem() <= 0.0) {\n"
                f'              printf("{{\\"status\\":\\"TIMEOUT\\",\\"dims\\":\\"{dimfmt}\\",\\"config\\":\\"{cfg_tag}\\"}}\\n", {dim_call});\n'
                "              _batch_ok = false; break;\n"
                "          }\n"
                f"          int _r = verify({dim_call}, vlen, _rem());\n"
                "          if (_r == 1) return 1;\n"
                "          if (_r == 2) { _batch_ok = false; break; }"
            )
        d = inner_dims[i]
        vals = ", ".join(str(v) for v in spec.dims[d])
        return (f"        for (size_t {d} : {{{vals}}}) {{\n"
                "          if (!_batch_ok) break;\n"
                f"{grow_inner(i + 1)}\n"
                "        }")

    decls_str = "\n".join(decls)
    neon_body = _strip_simd_includes(neon_src)
    rvv_body = _strip_simd_includes(rvv_src)
    if spec.scalar_movs:
        neon_body = _rewrite_scalar_movs(neon_body)
        rvv_body = _rewrite_scalar_movs(rvv_body)
    if spec.index_reads:
        neon_body = _rewrite_index_reads(neon_body, spec.index_reads)
        rvv_body = _rewrite_index_reads(rvv_body, spec.index_reads)
    if spec.scalar_reads:
        neon_body = _rewrite_scalar_broadcast(neon_body, spec.scalar_reads)
        rvv_body = _rewrite_scalar_broadcast(rvv_body, spec.scalar_reads)
    neon_adapters = _neon_void_load_adapters(neon_body)
    pre_defines_str = ("\n".join(spec.pre_defines) + "\n") if spec.pre_defines else ""
    if gcross:
        d0, d1 = gcross
        # Cross-product growth: expand a square frontier. At level _n verify every shape with
        # max(d0,d1)=_n — the new `d0=_n` column (d1=1.._n) and `d1=_n` row (d0=1.._n-1) — so
        # after level N the full N×N grid is verified. Advance only if the whole frontier
        # passes; stop on counterexample (halt) or budget (TIMEOUT → PARTIAL "up to N×N").
        main_loop = (
            "    size_t _grow_last = 0;\n"
            f"    for (size_t _n = _gstart; (_gmax == 0 || _n <= _gmax); _n++) {{\n"
            "      bool _batch_ok = true;\n"
            f"      {{ size_t {d0} = _n;\n"
            f"        for (size_t {d1} = 1; {d1} <= _n && _batch_ok; {d1}++) {{\n"
            "          if (budget > 0.0 && _rem() <= 0.0) {\n"
            f'            printf("{{\\"status\\":\\"TIMEOUT\\",\\"dims\\":\\"{dimfmt}\\",\\"config\\":\\"{cfg_tag}\\"}}\\n", {dim_call});\n'
            "            _batch_ok = false; break;\n"
            "          }\n"
            f"          int _r = verify({dim_call}, vlen, _rem());\n"
            "          if (_r == 1) return 1;\n"
            "          if (_r == 2) { _batch_ok = false; break; }\n"
            "        }\n"
            "      }\n"
            f"      {{ size_t {d1} = _n;\n"
            f"        for (size_t {d0} = 1; {d0} < _n && _batch_ok; {d0}++) {{\n"
            "          if (budget > 0.0 && _rem() <= 0.0) {\n"
            f'            printf("{{\\"status\\":\\"TIMEOUT\\",\\"dims\\":\\"{dimfmt}\\",\\"config\\":\\"{cfg_tag}\\"}}\\n", {dim_call});\n'
            "            _batch_ok = false; break;\n"
            "          }\n"
            f"          int _r = verify({dim_call}, vlen, _rem());\n"
            "          if (_r == 1) return 1;\n"
            "          if (_r == 2) { _batch_ok = false; break; }\n"
            "        }\n"
            "      }\n"
            "      if (!_batch_ok) break;\n"
            "      _grow_last = _n;\n"
            "    }"
        )
        probes_block = ""
    elif grow:
        # Continuous-growth sweep: grow `grow` from _gstart, unbounded (or to _gmax),
        # verifying ALL representative inner configs per value; advance only if the whole
        # batch passes. Stop on counterexample (halt) or budget (a config prints TIMEOUT →
        # PARTIAL = "verified up to here"). Unbounded ⇒ only TIMEOUT/COUNTEREXAMPLE exit.
        main_loop = (
            "    size_t _grow_last = 0;\n"
            f"    for (size_t {grow} = _gstart; (_gmax == 0 || {grow} <= _gmax); {grow}++) {{\n"
            "      bool _batch_ok = true;\n"
            f"{grow_inner(0)}\n"
            "      if (!_batch_ok) break;\n"
            f"      _grow_last = {grow};\n"
            "    }"
        )
        probes_block = ""
    else:
        main_loop = nest(0)
        # Sparse probe shapes appended after the cross-product grid (e.g. deep-row
        # flush-boundary checks pinned to one channel width — see _rdsum_fixture).
        probe_lines = []
        for _pr in spec.probes:
            _pv = ", ".join(f"(size_t){_pr[d]}" for d in dims)   # size_t for %zu / verify() args
            probe_lines.append(
                f'      if (budget > 0.0 && _rem() <= 0.0) {{\n'
                f'          printf("{{\\"status\\":\\"TIMEOUT\\",\\"dims\\":\\"{dimfmt}\\",\\"config\\":\\"{cfg_tag}\\"}}\\n", {_pv});\n'
                f'      }} else {{\n'
                f'          int _r = verify({_pv}, vlen, _rem());\n'
                f'          if (_r == 1) return 1;\n'
                f'      }}')
        probes_block = ("\n" + "\n".join(probe_lines)) if probe_lines else ""
    # Growth mode reads start/max-grow from argv[1]/argv[2] (orchestrator min/max_batch),
    # defaults to a finite budget so an unbounded sweep can't spin forever.
    if gcross or grow:
        budget_default = "600.0"
        grow_argv = ("    size_t _gstart = (argc > 1) ? (size_t)atoi(argv[1]) : 1;\n"
                     "    size_t _gmax   = (argc > 2) ? (size_t)atoi(argv[2]) : 0;   // 0 = unbounded\n")
        if gcross:
            final_status = (f'    printf("{{\\"status\\":\\"ALL_VERIFIED\\",\\"grow_cross\\":\\"{gcross[0]}x{gcross[1]}\\",\\"reached\\":%zu}}\\n", _grow_last);')
        else:
            final_status = (f'    printf("{{\\"status\\":\\"ALL_VERIFIED\\",\\"grow_dim\\":\\"{grow}\\",\\"reached\\":%zu}}\\n", _grow_last);')
    else:
        budget_default = "0.0"
        grow_argv = ""
        final_status = '    printf("{\\"status\\":\\"ALL_VERIFIED\\",\\"start\\":0,\\"end\\":0,\\"configs\\":1}\\n");'
    return f"""// AUTO-GENERATED by emit.py — multi-dim harness ({name}).
#include "salt.hpp"
#include <cassert>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <vector>
using namespace salt;

#define restrict

// Symbolic accessors for rewritten scalar derefs: reads (`*p`) and stores (`*p = v`).
template <typename T>
static inline SymbolicScalar<T> salt_scalar(const T* p) {{
    auto& _sb = g_ctx->findBuffer((const void*)p);
    return SymbolicScalar<T>(_sb, _sb.ptrToByteOffset((const void*)p));
}}
template <typename T>
struct SaltDeref {{
    SymbolicBuffer& b; size_t off;
    SaltDeref& operator=(const SymbolicScalar<T>& v) {{
        b.storeScalar(off, v.term(), SymTraits<T>::bits); return *this;
    }}
}};
template <typename T>
static inline SaltDeref<T> salt_deref(T* p) {{
    auto& _sb = g_ctx->findBuffer((const void*)p);
    return SaltDeref<T>{{_sb, _sb.ptrToByteOffset((const void*)p)}};
}}

{pre_defines_str}namespace neon_kernel {{
{neon_adapters}
{neon_body}
}} // namespace neon_kernel

namespace rvv_kernel {{
{rvv_body}
}} // namespace rvv_kernel

int verify({dim_sig}, size_t vlen, double timeout_s) {{
    VerificationContext ctx(vlen);
    g_ctx = &ctx;
{decls_str}

{scalar_tail_clear}    neon_kernel::{neon.func_name}({call_args("neon")});{scalar_tail_inject}
    rvv_kernel ::{rvv.func_name}({call_args("rvv")});

    Term eq = {cmp_expr};
    ctx.assert_(ctx.lnot_(eq));
    if (timeout_s > 0) ctx.set_query_timeout_ms((uint64_t)(timeout_s * 1000.0));
    printf("{{\\"status\\":\\"SOLVING\\",\\"dims\\":\\"{dimfmt}\\",\\"config\\":\\"{cfg_tag}\\"}}\\n", {dim_call});
    CheckResult _c = ctx.check();
    if (_c == CheckResult::Unsat) {{
        printf("{{\\"status\\":\\"VERIFIED\\",\\"dims\\":\\"{dimfmt}\\",\\"config\\":\\"{cfg_tag}\\"}}\\n", {dim_call});
        return 0;
    }}
    if (_c == CheckResult::Unknown) {{
        printf("{{\\"status\\":\\"TIMEOUT\\",\\"dims\\":\\"{dimfmt}\\",\\"config\\":\\"{cfg_tag}\\"}}\\n", {dim_call});
        return 2;
    }}
{cex_witness}
    printf("{{\\"status\\":\\"COUNTEREXAMPLE\\",\\"dims\\":\\"{dimfmt}\\",\\"config\\":\\"{cfg_tag}\\",\\"fail_index\\":%zu,\\"neon_out\\":%lld,\\"rvv_out\\":%lld}}\\n", {dim_call}, fi, _nv, _vv);
    return 1;
}}

int main(int argc, char** argv) {{
    setvbuf(stdout, NULL, _IOLBF, 0);   // line-buffer so per-batch status streams over a pipe
    size_t vlen   = (argc > 3) ? (size_t)atoi(argv[3]) : 256;
    double budget = (argc > 4) ? atof(argv[4]) : {budget_default};     // TOTAL wall-clock budget (s); 0 = none
    auto _t0 = std::chrono::steady_clock::now();
    auto _rem = [&]() -> double {{                         // seconds left in the total budget (0 = no limit)
        if (budget <= 0.0) return 0.0;
        double e = std::chrono::duration<double>(std::chrono::steady_clock::now() - _t0).count();
        return budget - e;
    }};
{grow_argv}{main_loop}{probes_block}
{final_status}
    return 0;
}}
"""


def generate_harness(neon_path: str, rvv_path: str, name: str,
                     params_mode: str = "symbolic", input_range=None,
                     reference_isa: str = "neon") -> str:
    if reference_isa not in ("neon", "rvv"):
        raise ValueError("reference_isa must be neon or rvv")
    neon = parse_signature(neon_path, "test_rvv" if reference_isa == "rvv" else "test_neon")
    rvv = parse_signature(rvv_path, "test_rvv")
    if len(neon.params) != len(rvv.params):
        raise ValueError(f"signature arity mismatch: {len(neon.params)} vs {len(rvv.params)}")
    if reference_isa == "rvv":
        for a, b in zip(neon.params, rvv.params):
            # Current scalar rewrites use argument names from the reference.
            if a.name != b.name:
                raise NotImplementedError("RVV argument names must match for scalar rewrites")
            if (a.type_spelling, a.pointee, a.is_pointer, a.points_to_const, a.is_ptr_to_ptr,
                a.is_struct_ptr, a.is_int_scalar) != (
                b.type_spelling, b.pointee, b.is_pointer, b.points_to_const, b.is_ptr_to_ptr,
                b.is_struct_ptr, b.is_int_scalar):
                raise ValueError(f"RVV signature mismatch: {a.name} vs {b.name}")
    _fx = _match_fixture(neon, open(neon_path).read())   # multi-dim fixture family?
    if _fx is not None:
        if reference_isa == "rvv":
            raise NotImplementedError(
                "RVV-to-RVV multidimensional workloads need an explicit shape fixture; "
                "the NEON/RVV fixture sweep is not an optimization workload proof")
        if _fx.config_tag and _fx.config_tag.startswith("qc8w_"):
            if params_mode == "symbolic":
                raise NotImplementedError(
                    "qc8w fixtures use three concrete parameter profiles; "
                    "symbolic-params verification is not implemented")
            if input_range is not None:
                raise NotImplementedError(
                    "qc8w fixtures constrain packed FP planes explicitly; "
                    "input-range applies to homogeneous FP inputs only")
        return generate_multidim(neon_path, rvv_path, name, neon, rvv, _fx, input_range)
    roles = resolve_roles(neon)
    ulp_tol = 0 if reference_isa == "rvv" else _ulp_tol_for(name)   # 0 = bit-exact; >0 relaxes FP outputs to a ULP bound

    # `const void* params` (e.g. f32-f16-vcvt) is parsed as a const pointer and
    # lands in roles.inputs with pointee "void" — but it's an opaque, unused
    # param, not data. Strip it; the kernel call passes nullptr for it.
    void_param_names = {p.name for p in roles.inputs if p.pointee == "void"}
    roles.inputs = [p for p in roles.inputs if p.pointee != "void"]

    if roles.indirect:
        raise NotImplementedError("indirect (T**) inputs not yet supported")
    if len(roles.params) > 1:
        raise NotImplementedError("multiple params structs not yet supported")

    if params_mode not in ("symbolic", "concrete"):
        raise ValueError(f"params_mode must be 'symbolic' or 'concrete', got {params_mode!r}")

    # --- param-struct handling (user-selected mode; default symbolic) ---
    params_names = {p.name for p in roles.params}
    params_setup: list[str] = []
    config_pre = ""             # code emitted before verify() (concrete config table)
    cfg_param = ""              # extra verify() arg in concrete mode
    config_str = '"symbolic"'   # C expr for the verdict's config tag
    n_configs = 1
    is_concrete = False
    sym_param_rewrite = None    # (struct, pname, leaves) when symbolic-int rewrite applies
    if roles.params:
        st = roles.params[0].struct_name
        leaves = parse_struct_leaves(_XNN_MIN_H, st)
        cls = classify_param_struct(leaves)
        if cls == "none":                  # empty/dummy struct (xnn_f32_default_params)
            params_setup.append(f"    {st} params{{}};")
            config_str = '"no-params"'
        elif params_mode == "concrete":    # float OR int → concrete edge configs
            paths, combos = _gen_configs(leaves, struct_name=st)
            if not combos:
                raise NotImplementedError(f"no concrete configs for {st}")
            config_pre = _emit_config_table(st, paths, combos)
            # Register as a concrete buffer so intrinsic param-loads
            # (e.g. vld1_dup_f32(&params->scalar.x)) resolve via findBuffer.
            params_setup += [f"    {st} params{{}};", "    _set_params(params, cfg);",
                             f'    ctx.registerConcreteBuffer("params", &params, sizeof({st}));']
            cfg_param, config_str, n_configs, is_concrete = \
                ", size_t cfg", "_cfg_name(cfg)", len(combos), True
        elif cls == "float":               # symbolic all-float → sentinel
            params_setup += [f"    {st} params{{}};",
                             f'    auto& _b_params = ctx.registerBuffer("params", sizeof({st}));',
                             "    _b_params.bindScalarRef(&params);"]
        else:                              # symbolic int — or mixed int+float
            # Int leaves rewrite to salt_param<int>() (symbolic BV); float leaves
            # to salt_param<float>() → SymbolicScalar<float>, which the FP _vf_
            # overloads (core.hpp) consume. Both load from the same symbolic
            # params buffer at disjoint offsets.
            pname = roles.params[0].name
            params_setup += [f"    {st} params{{}};",
                             f'    auto& _b_params = ctx.registerBuffer("params", sizeof({st}));',
                             "    _b_params.bind(&params);"]
            params_setup += _emit_param_constraints(st, leaves)   # validity (shift∈[0,31], …)
            _ranges = get_param_ranges(name)                      # per-field [lo,hi] bounds
            if _ranges:
                params_setup += _emit_param_ranges(st, leaves, _ranges)
            sym_param_rewrite = (st, pname, leaves)               # rewrite params->field in bodies
    if void_param_names and not roles.params:    # only param was the opaque const void*
        config_str = '"no-params"'
    if len(roles.bounds) != 1:
        raise NotImplementedError(f"elementwise slice needs exactly one bound; got "
                                  f"{[p.name for p in roles.bounds]}")
    if not roles.outputs:
        raise ValueError("no output buffer found")
    bound = roles.bounds[0].name

    neon_src = open(neon_path).read()
    rvv_src = open(rvv_path).read()
    # Partition outputs: a native `*name <op>=` store is a scalar reduction (rsum/raddstore).
    # Array (vector-store) outputs are buffer-compared. A PURE reduction (no array output)
    # uses the scalar-result side-channel. A HYBRID (array + reduction — raddstoreexpminusmax:
    # output[] exp values + the `sum` horizontal reduce) compares the array(s) and DEFERS the
    # reduction: it's a horizontal reduce accumulated in a native float, not capturable as one
    # Term — and order-sensitive — so verify the exp output[] now, leave the sum for later.
    _red_outs = {p.name for p in roles.outputs
                 if re.search(r'\*\s*' + re.escape(p.name) + r'\s*[-+*/|&^]?=', neon_src + rvv_src)}
    if reference_isa == "rvv" and _red_outs:
        raise NotImplementedError(
            "RVV scalar reduction stores are not fully modeled; refusing a partial output proof")
    arr_outs = [p for p in roles.outputs if p.name not in _red_outs]
    byte_unit, unit_type = _detect_byte_unit(neon_src, bound)
    unit_bytes = 1
    if byte_unit:
        if unit_type not in _BYTES:
            raise NotImplementedError(f"byte-unit element type {unit_type!r} unknown")
        unit_bytes = _BYTES[unit_type]
        # `batch` is the byte-extent of the INPUT domain (measured in unit_type),
        # so every input must be unit_bytes wide for "batch / sizeof(unit)" to be
        # the element count N. OUTPUTS may be a different width — a convert kernel
        # narrows/widens (e.g. f32-f16-vcvt: float in, uint16 out; qu8-f32-vcvt:
        # uint8 in, float out) but still writes N elements; each output is sized
        # by its own pointee and compared with its own kind.
        if unit_bytes > 1:
            for p in roles.inputs:
                if _BYTES.get(p.pointee) != unit_bytes:
                    raise NotImplementedError("mixed input element sizes with byte-unit batch not yet supported")

    input_names = {p.name for p in roles.inputs}
    output_names = {p.name for p in roles.outputs}

    # Split-complex kernels (f32-vcmul) carve each buffer into [real | imag] via
    # `(uintptr_t) ptr + batch`, so every buffer spans split_mult*bound elements
    # and the output compare must cover both halves (not just [0, bound)).
    split_mult = 2 if re.search(
        r'\(\s*uintptr_t\s*\)\s*\w+\s*\+\s*' + re.escape(bound) + r'\b',
        neon_src + rvv_src) else 1
    cap_expr = f"{bound} + 16" if split_mult == 1 else f"{bound} * {split_mult} + 16"
    cmp_count = bound if split_mult == 1 else f"{bound} * {split_mult}"

    # buffer setup
    decls = []
    for p in roles.inputs:
        ct = p.pointee
        decls.append(f'    std::vector<{ct}> {p.name}_arr(cap, ({ct})0);')
        decls.append(f'    auto& _b_{p.name} = ctx.registerBuffer("{p.name}", cap * sizeof({ct}));'
                     f' _b_{p.name}.bind({p.name}_arr.data());')
    for p in roles.outputs:
        ct = p.pointee
        inout = _output_is_read(neon_src, p.name) or _output_is_read(rvv_src, p.name)
        decls.append(f'    std::vector<{ct}> {p.name}_neon_arr(cap, ({ct})0), {p.name}_rvv_arr(cap, ({ct})0);')
        decls.append(f'    auto& _b_{p.name}_neon = ctx.registerBuffer("{p.name}_neon", cap * sizeof({ct}));'
                     f' _b_{p.name}_neon.bind({p.name}_neon_arr.data());')
        decls.append(f'    auto& _b_{p.name}_rvv  = ctx.registerBuffer("{p.name}_rvv",  cap * sizeof({ct}));'
                     f' _b_{p.name}_rvv.bind({p.name}_rvv_arr.data());')
        if inout:
            # In-out / accumulator: both sides share one symbolic initial image
            # (pure outputs keep independent poison so a missing write is caught).
            decls.append(
                f'    for (size_t _i = 0; _i < cap * sizeof({ct}); _i++) '
                f'_b_{p.name}_rvv.setByte(_i, _b_{p.name}_neon.getByte(_i));  // shared init (in-out)')

    decls.extend(params_setup)
    # The sweep variable {bound} is always an *element* count; for byte-unit
    # kernels convert it to the byte count the kernel expects.
    if byte_unit:
        decls.append(f"    const size_t _kbound = {bound} * {unit_bytes};  // elements -> bytes")
    bound_call = "_kbound" if byte_unit else bound
    if input_range:                     # optional: restrict F32 inputs to finite [lo,hi]
        lo, hi = input_range
        for p in roles.inputs:
            if p.pointee == "float":
                decls += _emit_input_range(f"_b_{p.name}", "cap", lo, hi)
        if config_str == '"symbolic"':
            config_str = '"finite"'

    # positional call args (inputs shared; outputs differ neon/rvv)
    def call_args(side: str) -> str:
        out = []
        for p in neon.params:
            if p.name in input_names:
                out.append(f"{p.name}_arr.data()")
            elif p.name in output_names:
                out.append(f"{p.name}_{side}_arr.data()")
            elif p.name in params_names:
                out.append("&params")
            elif p.name in void_param_names:
                out.append("nullptr")
            elif p.name == bound:
                out.append(bound_call)
            else:
                out.append(p.name)
        return ", ".join(out)

    # output comparison over the logical region [0, bound) per ARRAY output
    cmps = []
    for p in arr_outs:
        cmps.append(f'        buffers_equal(ctx.tm, _b_{p.name}_neon, _b_{p.name}_rvv, '
                    f'{cmp_count}, sizeof({p.pointee}), ElementKind::{"UINT" if reference_isa == "rvv" else _kind(p.pointee)}, {ulp_tol})')
    cmp_expr = cmps[0] if cmps else ""
    for term in cmps[1:]:
        cmp_expr = f"ctx.land_({cmp_expr}, {term})"

    # counterexample scan: first differing element of the first array output
    first_out = arr_outs[0] if arr_outs else roles.outputs[0]
    fo_ct = first_out.pointee
    fo_bits = _BYTES[first_out.pointee] * 8
    # Witness predicate: under a ULP tolerance, flag the first element whose ULP
    # distance EXCEEDS tol (not the first bit-differing one). Exact (tol=0) keeps
    # raw decimal-string inequality.
    if ulp_tol and fo_ct in _FP_CTYPES:
        _wb = fo_bits - 1
        _lwit = (
            f'        unsigned long long _nu = strtoull(n.getBitVectorValue(10).c_str(), nullptr, 10);\n'
            f'        unsigned long long _vu = strtoull(v.getBitVectorValue(10).c_str(), nullptr, 10);\n'
            f'        long long _ka = ((_nu >> {_wb}) & 1ULL) ? ((long long)(1ULL << {_wb}) - (long long)_nu) : (long long)_nu;\n'
            f'        long long _kb = ((_vu >> {_wb}) & 1ULL) ? ((long long)(1ULL << {_wb}) - (long long)_vu) : (long long)_vu;\n'
            f'        long long _ud = (_ka > _kb) ? (_ka - _kb) : (_kb - _ka);\n'
            f'        if (_ud > {ulp_tol}LL) {{ fi = e; break; }}\n')
    else:
        _lwit = f'        if (n.getBitVectorValue(10) != v.getBitVectorValue(10)) {{ fi = e; break; }}\n'

    # Scalar-reduction output (rsum): the kernel writes its result via a scalar
    # accumulate `*output += vmv_x_s/vget_lane(...)`, NOT a vector store — so it
    # never reaches the symbolic output buffer.  Detect the `*output <op>=` store
    # (not the `T* output` param decl) and compare the captured reduction sum
    # (stashed in ctx by the scalar-extract shims) instead of the (unwritten,
    # unconstrained) output buffer.
    out0 = roles.outputs[0].name
    # Pure reduction (rsum: the only output is a `*out +=`) → scalar side-channel compare.
    # Hybrid (array output(s) + a separate reduction) → arr_outs buffer-compare above, with
    # the reduction deferred (not in arr_outs, so not compared).
    is_scalar_reduction = bool(_red_outs) and not arr_outs
    if is_scalar_reduction:
        kernel_calls = (
            f'    ctx.clear_scalar_result();\n'
            f'    neon_kernel::{neon.func_name}({call_args("neon")});\n'
            f'    Term _neon_red = ctx.scalar_result();\n'
            f'    ctx.clear_scalar_result();\n'
            f'    rvv_kernel ::{rvv.func_name}({call_args("rvv")});\n'
            f'    Term _rvv_red = ctx.scalar_result();'
        )
        cmp_expr = "ctx.equal(_neon_red, _rvv_red)"
        cex_block = (
            '    printf("{\\"status\\":\\"COUNTEREXAMPLE\\",\\"batch\\":%zu,\\"vlen\\":%zu,'
            '\\"config\\":\\"%s\\",\\"fail_index\\":0}\\n", ' + bound + ', vlen, ' + config_str + ');\n'
            '    return 1;'
        )
    else:
        kernel_calls = (
            f'    neon_kernel::{neon.func_name}({call_args("neon")});\n'
            f'    rvv_kernel ::{rvv.func_name}({call_args("rvv")});'
        )
        cex_block = (
            f'    size_t fi = 0;\n'
            f'    for (size_t e = 0; e < {cmp_count}; e++) {{\n'
            f'        Term n = ctx.solver->getValue(_b_{first_out.name}_neon.loadScalar(e * sizeof({fo_ct}), {fo_bits}));\n'
            f'        Term v = ctx.solver->getValue(_b_{first_out.name}_rvv.loadScalar(e * sizeof({fo_ct}), {fo_bits}));\n'
            + _lwit +
            f'    }}\n'
            '    printf("{\\"status\\":\\"COUNTEREXAMPLE\\",\\"batch\\":%zu,\\"vlen\\":%zu,'
            '\\"config\\":\\"%s\\",\\"fail_index\\":%zu}\\n", ' + bound + ', vlen, ' + config_str + ', fi);\n'
            '    return 1;'
        )

    decls_str = "\n".join(decls)
    neon_body = _strip_simd_includes(neon_src)
    rvv_body = _strip_simd_includes(rvv_src)
    # Scalar-broadcast inputs (`*input_b`) → symbolic accessor, so the broadcast
    # constant is symbolic rather than the concrete backing (which would be 0).
    scalar_bcast = (_scalar_broadcast_inputs(neon_src, input_names) |
                    _scalar_broadcast_inputs(rvv_src, input_names))
    if scalar_bcast:
        neon_body = _rewrite_scalar_broadcast(neon_body, scalar_bcast)
        rvv_body = _rewrite_scalar_broadcast(rvv_body, scalar_bcast)
    if sym_param_rewrite:
        _st, _pn, _lv = sym_param_rewrite
        neon_body = _rewrite_symbolic_params(neon_body, _st, _pn, _lv)
        rvv_body = _rewrite_symbolic_params(rvv_body, _st, _pn, _lv)

    if is_concrete:
        main_loop = f"""    size_t _last = start ? start - 1 : 0;
    for (size_t cfg = 0; cfg < {n_configs}; cfg++) {{
      for (size_t b = start; (end == 0 || b <= end); b++) {{
        if (budget > 0.0 && _rem() <= 0.0) {{ printf("{{\\"status\\":\\"TIMEOUT\\",\\"batch\\":%zu,\\"vlen\\":%zu}}\\n", b, vlen); goto _done; }}
        int r = verify(b, vlen, cfg, _rem());   // per-query limit = remaining total budget
        if (r == 1) return 1;   // counterexample — stop
        if (r == 2) break;      // batch hit the budget — larger batches only get harder; next config
        if (b > _last) _last = b;
      }}
    }}
_done:
    printf("{{\\"status\\":\\"ALL_VERIFIED\\",\\"start\\":%zu,\\"end\\":%zu,\\"configs\\":{n_configs}}}\\n", start, _last);"""
    else:
        main_loop = f"""    size_t _last = start ? start - 1 : 0;
    for (size_t b = start; (end == 0 || b <= end); b++) {{
        if (budget > 0.0 && _rem() <= 0.0) {{ printf("{{\\"status\\":\\"TIMEOUT\\",\\"batch\\":%zu,\\"vlen\\":%zu}}\\n", b, vlen); break; }}
        int r = verify(b, vlen, _rem());        // per-query limit = remaining total budget
        if (r == 1) return 1;   // counterexample — stop
        if (r == 2) break;      // batch hit the budget — larger batches only get harder
        _last = b;
    }}
    printf("{{\\"status\\":\\"ALL_VERIFIED\\",\\"start\\":%zu,\\"end\\":%zu,\\"configs\\":1}}\\n", start, _last);"""

    return f"""// AUTO-GENERATED by emit.py — uniform harness (no Shape/profile).
#include "salt.hpp"
#include <cassert>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <vector>
using namespace salt;

#define restrict          // C-only keyword; this harness compiles as C++

// Symbolic accessor for scalar-broadcast input reads (`*input_b`).
template <typename T>
static inline SymbolicScalar<T> salt_scalar(const T* p) {{
    auto& _sb = g_ctx->findBuffer((const void*)p);
    return SymbolicScalar<T>(_sb, _sb.ptrToByteOffset((const void*)p));
}}
// Symbolic accessor for params-struct field reads (`params->scalar.x`).
template <typename T>
static inline SymbolicScalar<T> salt_param(const void* base, size_t off) {{
    auto& _pb = g_ctx->findBuffer(base);
    return SymbolicScalar<T>(_pb, _pb.ptrToByteOffset(base) + off);
}}

namespace neon_kernel {{
{neon_body}
}} // namespace neon_kernel

namespace rvv_kernel {{
{rvv_body}
}} // namespace rvv_kernel

{config_pre}
// returns 0=VERIFIED, 1=COUNTEREXAMPLE, 2=TIMEOUT/UNKNOWN
int verify(size_t {bound}, size_t vlen{cfg_param}, double timeout_s) {{
    VerificationContext ctx(vlen);
    g_ctx = &ctx;
    const size_t cap = {cap_expr};   // over-allocate; exact size not needed
{decls_str}

{kernel_calls}

    Term eq = {cmp_expr};
    ctx.assert_(ctx.lnot_(eq));
    if (timeout_s > 0) ctx.set_query_timeout_ms((uint64_t)(timeout_s * 1000.0));
    printf("{{\\"status\\":\\"SOLVING\\",\\"batch\\":%zu,\\"vlen\\":%zu,\\"config\\":\\"%s\\"}}\\n", {bound}, vlen, {config_str});
    CheckResult _r = ctx.check();
    if (_r == CheckResult::Unsat) {{
        printf("{{\\"status\\":\\"VERIFIED\\",\\"batch\\":%zu,\\"vlen\\":%zu,\\"config\\":\\"%s\\"}}\\n", {bound}, vlen, {config_str});
        return 0;
    }}
    if (_r == CheckResult::Unknown) {{   // solver gave up (e.g. per-query timeout) — NOT a counterexample
        printf("{{\\"status\\":\\"TIMEOUT\\",\\"batch\\":%zu,\\"vlen\\":%zu,\\"config\\":\\"%s\\"}}\\n", {bound}, vlen, {config_str});
        return 2;
    }}
{cex_block}
}}

int main(int argc, char** argv) {{
    setvbuf(stdout, NULL, _IOLBF, 0);   // line-buffer so per-batch status streams over a pipe
    if (argc < 3) {{ fprintf(stderr, "Usage: %s <start> <end(0=unbounded)> [vlen] [time_budget_s]\\n", argv[0]); return 2; }}
    size_t start = (size_t)atoi(argv[1]);
    size_t end   = (size_t)atoi(argv[2]);                 // 0 = unbounded: sweep until the time budget
    size_t vlen  = (argc > 3) ? (size_t)atoi(argv[3]) : 256;
    double budget = (argc > 4) ? atof(argv[4]) : 0.0;     // TOTAL wall-clock budget (s); 0 = none
    if (end == 0 && budget <= 0.0) budget = 600.0;        // unbounded needs a budget — default 10 min
    auto _t0 = std::chrono::steady_clock::now();
    auto _rem = [&]() -> double {{                         // seconds left in the total budget (0 = no limit)
        if (budget <= 0.0) return 0.0;
        double e = std::chrono::duration<double>(std::chrono::steady_clock::now() - _t0).count();
        return budget - e;
    }};
{main_loop}
    return 0;
}}
"""
