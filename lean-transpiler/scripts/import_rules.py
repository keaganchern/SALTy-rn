#!/usr/bin/env python3
"""Development-only importer. Runtime parsing and lowering are entirely in Lean.

Import only the corpus's reachable neon2rvv wrappers, then apply explicit local
repairs. Generated sources are checked in; no Python/reference clone is needed
to build or use the transpiler. This is a bootstrap tool, not the C frontend.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "lean-transpiler/Transpiler/Rules.lean"
HEADER = ROOT / "neon2rvv/neon2rvv.h"


def propagate_nan(operands, lanes, result):
    """Default ARM FPCR: first signaling NaN, else first quiet NaN.

    Keep the original sign/payload and quiet signaling inputs. Integer masks
    avoid letting RVV floating-point arithmetic canonicalize the selected NaN.
    A result without a NaN operand (e.g. 0/0) remains the hardware default NaN.
    Operand order is the ACLE instruction order, not a compiler's reordered FMA.
    Reference: QEMU v8.2.2 fpu/softfloat-specialize.c.inc, pickNaN/pickNaNMulAdd.
    """
    code = []
    for op in operands:
        code += [
            f"  vuint32m1_t u{op} = __riscv_vreinterpret_v_f32m1_u32m1({op});",
            f"  vbool32_t {op}_nan = __riscv_vmsgtu_vx_u32m1_b32(__riscv_vand_vx_u32m1(u{op}, 0x7FFFFFFF, {lanes}), 0x7F800000, {lanes});",
            f"  vbool32_t {op}_snan = __riscv_vmand_mm_b32({op}_nan, __riscv_vmseq_vx_u32m1_b32(__riscv_vand_vx_u32m1(u{op}, 0x00400000, {lanes}), 0, {lanes}), {lanes});",
        ]
    code += [f"  vuint32m1_t r = __riscv_vreinterpret_v_f32m1_u32m1({result});"]
    for kind in ["nan", "snan"]:
        for op in reversed(operands):
            code += [f"  r = __riscv_vmerge_vvm_u32m1(r, __riscv_vor_vx_u32m1(u{op}, 0x00400000, {lanes}), {op}_{kind}, {lanes});"]
    return "\n".join(code) + "\n"


def generate():
    header = HEADER.read_text()
    functions = {}
    for match in re.finditer(r"^FORCE_INLINE\s+\w+\s+(\w+)\([^;]*?\)\s*\{", header, re.M):
        end, depth = match.end(), 1
        while depth:
            depth += (header[end] == "{") - (header[end] == "}")
            end += 1
        functions[match[1]] = header[match.start():end].replace("FORCE_INLINE", "static inline", 1)

    # Quantized tails store 16/32 bits through byte-aligned output pointers.
    # NEON lane stores permit this; a typed scalar dereference introduces C
    # alignment/aliasing UB (caught by Zig's O0 alignment sanitizer). Copy the
    # extracted scalar's representation without imposing a stronger alignment.
    for bits, lanes in [(16, 4), (32, 2)]:
        functions[f"vst1_lane_u{bits}"] = f"""static inline void vst1_lane_u{bits}(void *a, uint{bits}x{lanes}_t b, const int lane) {{
  vuint{bits}m1_t shifted = __riscv_vslidedown_vx_u{bits}m1(b, lane, {lanes});
  uint{bits}_t value = __riscv_vmv_x_s_u{bits}m1_u{bits}(shifted);
  __builtin_memcpy(a, &value, sizeof(value));
}}"""

    # Keep separate rounding steps for non-fused multiply accumulate/subtract.
    for name, op in [("vmlaq_f32", "vaddq_f32"), ("vmlsq_f32", "vsubq_f32")]:
        functions[name] = f"""static inline float32x4_t {name}(float32x4_t a, float32x4_t b, float32x4_t c) {{
  float32x4_t product = vmulq_f32(b, c);
  return {op}(a, product);
}}"""

    # Avoid intermediate overflow when both inputs are INT16_MIN.
    functions["vqrdmulhq_s16"] = """static inline int16x8_t vqrdmulhq_s16(int16x8_t a, int16x8_t b) {
  return __riscv_vsmul_vv_i16m1(a, b, __RISCV_VXRM_RNU, 8);
}"""
    # ARM variable shifts interpret the signed low byte; large rounded right
    # shifts and large left shifts produce zero, unlike RVV's masked counts.
    functions["vrshlq_s32"] = """static inline int32x4_t vrshlq_s32(int32x4_t a, int32x4_t b) {
  vint32m1_t shift = __riscv_vsra_vx_i32m1(__riscv_vsll_vx_i32m1(b, 24, 4), 24, 4);
  vuint32m1_t leftCount = __riscv_vreinterpret_v_i32m1_u32m1(shift);
  vuint32m1_t rightCount = __riscv_vreinterpret_v_i32m1_u32m1(__riscv_vneg_v_i32m1(shift, 4));
  vint32m1_t left = __riscv_vsll_vv_i32m1(a, leftCount, 4);
  vint32m1_t right = __riscv_vssra_vv_i32m1(a, rightCount, __RISCV_VXRM_RNU, 4);
  vint32m1_t result = __riscv_vmerge_vvm_i32m1(right, left, __riscv_vmsge_vx_i32m1_b32(shift, 0, 4), 4);
  vbool32_t large = __riscv_vmor_mm_b32(__riscv_vmsge_vx_i32m1_b32(shift, 32, 4), __riscv_vmsle_vx_i32m1_b32(shift, -32, 4), 4);
  return __riscv_vmerge_vxm_i32m1(result, 0, large, 4);
}"""

    # All floating arithmetic, not just min/max, needs explicit propagation:
    # RVV arithmetic otherwise produces a canonical NaN and loses its payload.
    for op in ["add", "sub", "mul", "div", "min", "max"]:
        for q, lanes in [("", 2), ("q", 4)]:
            name = f"v{op}{q}_f32"
            functions[name] = (
                f"static inline float32x{lanes}_t {name}(float32x{lanes}_t a, float32x{lanes}_t b) {{\n"
                + propagate_nan(["a", "b"], lanes, f"__riscv_vf{op}_vv_f32m1(a, b, {lanes})")
                + "  return __riscv_vreinterpret_v_u32m1_f32m1(r);\n}")

    functions["vsqrtq_f32"] = (
        "static inline float32x4_t vsqrtq_f32(float32x4_t a) {\n"
        + propagate_nan(["a"], 4, "__riscv_vfsqrt_v_f32m1(a, 4)")
        + "  return __riscv_vreinterpret_v_u32m1_f32m1(r);\n}")

    for q, lanes in [("", 2), ("q", 4)]:
        functions[f"vfma{q}_f32"] = (
            f"static inline float32x{lanes}_t vfma{q}_f32(float32x{lanes}_t a, float32x{lanes}_t b, float32x{lanes}_t c) {{\n"
            + propagate_nan(["a", "b", "c"], lanes, f"__riscv_vfmacc_vv_f32m1(a, b, c, {lanes})")
            # ARM FPMulAdd overrides a quiet-NaN addend when 0*infinity is
            # invalid; a signaling-NaN addend still propagates its payload.
            + f"""  vuint32m1_t ab = __riscv_vand_vx_u32m1(ub, 0x7FFFFFFF, {lanes});
  vuint32m1_t ac = __riscv_vand_vx_u32m1(uc, 0x7FFFFFFF, {lanes});
  vbool32_t invalid_product = __riscv_vmor_mm_b32(
    __riscv_vmand_mm_b32(__riscv_vmseq_vx_u32m1_b32(ab, 0, {lanes}), __riscv_vmseq_vx_u32m1_b32(ac, 0x7F800000, {lanes}), {lanes}),
    __riscv_vmand_mm_b32(__riscv_vmseq_vx_u32m1_b32(ac, 0, {lanes}), __riscv_vmseq_vx_u32m1_b32(ab, 0x7F800000, {lanes}), {lanes}), {lanes});
  vbool32_t override_nan = __riscv_vmand_mm_b32(invalid_product, __riscv_vmandn_mm_b32(a_nan, a_snan, {lanes}), {lanes});
  r = __riscv_vmerge_vxm_u32m1(r, 0x7FC00000, override_nan, {lanes});
  return __riscv_vreinterpret_v_u32m1_f32m1(r);
}}""")
    for suffix, lanes in [("lane", 2), ("laneq", 4)]:
        name = f"vfmaq_{suffix}_f32"
        functions[name] = f"""static inline float32x4_t {name}(float32x4_t a, float32x4_t b, float32x{lanes}_t v, const int lane) {{
  float32x4_t c = __riscv_vrgather_vx_f32m1(v, lane, 4);
  return vfmaq_f32(a, b, c);
}}"""

    # Keep the NEON pairwise tree, without adding an extra +0 accumulator.
    for name, lanes in [("vaddv_f32", 2), ("vaddvq_f32", 4)]:
        functions[name] = f"""static inline float32_t {name}(float32x{lanes}_t a) {{
  vfloat32m1_t pairs = vadd{'q' if lanes == 4 else ''}_f32(a, __riscv_vslidedown_vx_f32m1(a, 1, {lanes}));
""" + ("  pairs = vaddq_f32(pairs, __riscv_vslidedown_vx_f32m1(pairs, 2, 4));\n" if lanes == 4 else "") + "  return __riscv_vfmv_f_s_f32m1_f32(pairs);\n}"
    functions["vpadd_f32"] = functions["vpadd_f32"].replace(
        "__riscv_vfadd_vv_f32m1(ab, ab_s, 4)", "vaddq_f32(ab, ab_s)")

    for name, offset in [("vzip1q_f32", 0), ("vzip2q_f32", 2)]:
        functions[name] = f"""static inline float32x4_t {name}(float32x4_t a, float32x4_t b) {{
  vuint32m1_t ids = __riscv_vid_v_u32m1(4);
  vuint32m1_t indexes = __riscv_vadd_vx_u32m1(__riscv_vsrl_vx_u32m1(ids, 1, 4), {offset}, 4);
  vbool32_t odd = __riscv_vmsne_vx_u32m1_b32(__riscv_vand_vx_u32m1(ids, 1, 4), 0, 4);
  return __riscv_vmerge_vvm_f32m1(__riscv_vrgather_vv_f32m1(a, indexes, 4), __riscv_vrgather_vv_f32m1(b, indexes, 4), odd, 4);
}}"""

    calls = set()
    for path in (ROOT / "kernels/source").glob("*.c"):
        source = re.sub(r"/\*.*?\*/|//[^\n]*", "", path.read_text(), flags=re.S)
        calls.update(re.findall(r"\b(v\w+_[a-z]\d+)\s*\(", source))
    seen, todo = set(), list(calls)
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        if name not in functions:
            raise RuntimeError(f"Missing lowering: {name}")
        seen.add(name)
        references = set(re.findall(r"\b(v\w+_[a-z]\d+)\s*\(", functions[name]))
        todo.extend(references - seen)

    aliases = sorted(set(re.findall(r"^typedef\s+(v\w+_t)\s+(\w+_t);", header, re.M)))
    out = ["-- Generated by scripts/import_rules.py; see NOTICE and LICENSE.neon2rvv.",
           "-- Wrapper bodies are parsed into Expr/Stmt nodes by Lean before lowering.",
           "namespace Transpiler", "def vectorAliases : List (String × String) := ["]
    out += [f"  ({json.dumps(neon)}, {json.dumps(rvv)})," for rvv, neon in aliases]
    out[-1] = out[-1].rstrip(",")
    out += ["]", "def ruleSources : List (String × String) := ["]
    out += [f"  ({json.dumps(name)}, {json.dumps(functions[name])})," for name in sorted(seen)]
    out[-1] = out[-1].rstrip(",")
    out += ["]", "end Transpiler", ""]
    OUT.write_text("\n".join(out))
    print(f"Generated {len(seen)} wrappers ({len(calls)} corpus intrinsics) in {OUT}")


if __name__ == "__main__":
    generate()
