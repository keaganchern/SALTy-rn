"""Traceable sampled audit for plain and broadcast-normalized integer semantics.

The subject set is the exact current I0/I1 review-plan partition.  Four former
unused Neon max/min contextual descriptors were removed after their faithful
vector-vector replacements collapsed into existing exact capabilities.  Every row is joined by
``capability_id`` to its canonical descriptor, real C call sites, pinned
architecture selector and Lean definition.  I0 rows receive sampled Lean versus
architecture execution.  I1 rows are deliberately conditional: the source C
operation is vector-vector while the reviewed lowering unbroadcasts one operand.
The audit therefore also records producer provenance and a fail-closed mutation
probe.  It never calls sampled evidence an exhaustive proof.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import io
import json
import platform
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from workflow.verification.lean_backend.binding import (
    OperandProvenanceError,
    bind_kernel,
    build_manifest,
)
from workflow.verification.lean_backend.descriptor import canonical_spec_digest
from workflow.verification.lean_backend.frontend import parse_kernel
from workflow.verification.lean_backend.intrinsic_index import CANONICAL_INTRINSIC_INDEX
from workflow.verification.lean_backend.schema import (
    OperandTransform,
    ScalarType,
    SemanticIntrinsic,
    VectorType,
)

from .schema import canonical_json, canonical_sha256


SCHEMA_VERSION = 1
ARTIFACT_KIND = "plain-integer-intrinsic-differential-audit"
EVIDENCE_LEVEL = "L3-sampled"
FAMILIES = frozenset({"I0-integer-plain", "I1-integer-broadcast-normalized"})
LEGACY_CONTEXTUAL_IDS: frozenset[str] = frozenset()
COVERAGE_SCOPE = (
    "listed-boundary-vectors-only;not-exhaustive;pure-active-lane-value;"
    "uniform-vector-operands-for-unbroadcast-rows;flags-memory-inactive-lanes-"
    "tail-mask-and-full-ISA-refinement-excluded"
)


class PlainIntegerDifferentialAuditError(RuntimeError):
    """The inventory, trace, evaluator or architecture probe is malformed."""


@dataclass(frozen=True, slots=True)
class PlainCase:
    case_id: str
    inputs: tuple[int, ...]
    input_widths: tuple[int, ...]
    output_width: int
    observed_lane: int = 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PlainIntegerDifferentialAuditError(f"expected JSON object: {path}")
    return value


def _run(
    command: Sequence[str], *, cwd: Path, timeout: int = 240
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command), cwd=cwd, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, timeout=timeout,
    )


def _tool_version(command: str) -> str:
    completed = _run([command, "--version"], cwd=Path.cwd(), timeout=30)
    lines = (completed.stdout or completed.stderr).splitlines()
    return lines[0] if lines else "version unavailable"


def _variant_specs() -> dict[str, SemanticIntrinsic]:
    result: dict[str, SemanticIntrinsic] = {}
    for variant in CANONICAL_INTRINSIC_INDEX.variants:
        spec = variant.spec
        if isinstance(spec, SemanticIntrinsic):
            digest = canonical_spec_digest(spec)
            if digest in result and result[digest] != spec:
                raise PlainIntegerDifferentialAuditError("descriptor digest collision")
            result[digest] = spec
    return result


def load_exact_subjects(root: Path) -> tuple[dict[str, Any], ...]:
    """Join all current I0/I1 exact rows after legacy descriptor cleanup."""

    corpus = root / "verification/elementwise-compiler"
    plan = _load_json(corpus / "IntrinsicReviewPlan.json")
    audit = _load_json(corpus / "IntrinsicAudit.json")
    registry = _load_json(corpus / "IntrinsicRegistry.json")
    family_by_id: dict[str, str] = {}
    for family in plan["families"]:
        if family["family"] not in FAMILIES:
            continue
        for subject in family["subjects"]:
            capability_id = subject["capability_id"]
            if capability_id in family_by_id:
                raise PlainIntegerDifferentialAuditError(
                    f"duplicate review-plan subject: {capability_id}"
                )
            family_by_id[capability_id] = family["family"]
    if len(family_by_id) != 65:
        raise PlainIntegerDifferentialAuditError(
            f"I0/I1 current subject count changed: {len(family_by_id)}"
        )

    audit_by_id = {row["capability_id"]: row for row in audit["variants"]}
    capability_by_id = {
        row["capability"]["capability_id"]: row["capability"]
        for row in registry["variants"]
    }
    specs = _variant_specs()
    selected = set(family_by_id)
    if selected - set(audit_by_id) or selected - set(capability_by_id):
        raise PlainIntegerDifferentialAuditError(
            "plain-integer subject is absent from audit or registry"
        )
    subjects: list[dict[str, Any]] = []
    for capability_id in sorted(selected):
        capability = capability_by_id[capability_id]
        audit_row = audit_by_id[capability_id]
        spec = specs.get(capability["descriptor_sha256"])
        if spec is None:
            raise PlainIntegerDifferentialAuditError(
                f"canonical semantic descriptor absent: {capability_id}"
            )
        for field in ("architecture", "spelling", "function_type", "semantic_symbol"):
            if capability[field] != audit_row[field]:
                raise PlainIntegerDifferentialAuditError(
                    f"registry/audit mismatch for {capability_id}: {field}"
                )
        if spec.lean_name != capability["semantic_symbol"]:
            raise PlainIntegerDifferentialAuditError(
                f"descriptor/registry Lean symbol mismatch: {capability_id}"
            )
        legacy = capability_id in LEGACY_CONTEXTUAL_IDS
        subjects.append(
            {
                "capability": capability,
                "audit": audit_row,
                "spec": spec,
                "semantic_family": (
                    "LEGACY-unused-broadcast-normalized-maxmin"
                    if legacy else family_by_id[capability_id]
                ),
                "subject_scope": (
                    "explicit-unused-cleanup-candidate" if legacy else "current-exact"
                ),
            }
        )
    if len(subjects) != 65:
        raise PlainIntegerDifferentialAuditError("plain-integer selected set changed")
    return tuple(subjects)


def _element_width(value_type: object) -> int:
    if isinstance(value_type, VectorType):
        return value_type.element.bit_width
    if isinstance(value_type, ScalarType) and value_type.bit_width is not None:
        return value_type.bit_width
    raise PlainIntegerDifferentialAuditError(f"unsupported sampled value type: {value_type!r}")


def _semantic_parameters(spec: SemanticIntrinsic) -> tuple[object, ...]:
    return tuple(
        spec.signature.parameters[arg.source_index].type for arg in spec.lean_arguments
    )


def _is_mask_type(value_type: object) -> bool:
    return isinstance(value_type, VectorType) and value_type.c_spelling.startswith("vbool")


def _case_prefix(subject: Mapping[str, Any]) -> str:
    capability = subject["capability"]
    spelling = re.sub(r"[^a-z0-9]+", "-", capability["spelling"].lower()).strip("-")
    return f"{spelling}-{capability['capability_id'].rsplit(':', 1)[1]}"


def _make_cases(subject: Mapping[str, Any]) -> tuple[PlainCase, ...]:
    spec: SemanticIntrinsic = subject["spec"]
    widths = tuple(
        1 if _is_mask_type(type_) else _element_width(type_)
        for type_ in _semantic_parameters(spec)
    )
    result = spec.signature.result
    output_width = 1 if _is_mask_type(result) else _element_width(result)
    prefix = _case_prefix(subject)

    def bounded(value: int, width: int) -> int:
        return value & ((1 << width) - 1)

    if len(widths) == 1:
        width = widths[0]
        raw = (0, 1, (1 << (width - 1)) - 1, 1 << (width - 1), (1 << width) - 1)
        values = tuple((value,) for value in raw)
    elif len(widths) == 2:
        width = max(widths)
        raw = (
            (0, 0), (1, (1 << width) - 1), ((1 << width) - 1, 1),
            (1 << (width - 1), (1 << width) - 1),
            ((1 << width) - 1, 1 << (width - 1)),
            (0x55, 0xAA),
        )
        values = raw
    elif len(widths) == 3:
        width = max(widths)
        raw = (
            (0, 1, 0), (0, 1, 1), ((1 << width) - 1, 1, 1),
            (1 << (width - 1), (1 << width) - 1, 1), (0x55, 0xAA, 1),
        )
        values = raw
    else:
        raise PlainIntegerDifferentialAuditError(
            f"unsupported semantic arity for {spec.spelling}: {len(widths)}"
        )
    return tuple(
        PlainCase(
            case_id=f"{prefix}-{index}",
            inputs=tuple(bounded(value, width) for value, width in zip(row, widths)),
            input_widths=widths,
            output_width=output_width,
        )
        for index, row in enumerate(values)
    )


def _bv(value: int, width: int) -> str:
    return f"(0x{value:0{(width + 3) // 4}X} : BitVec {width})"


def _lean_expression(subject: Mapping[str, Any], case: PlainCase) -> str:
    spec: SemanticIntrinsic = subject["spec"]
    arguments: list[str] = []
    for position, (lean_argument, type_) in enumerate(
        zip(spec.lean_arguments, _semantic_parameters(spec), strict=True)
    ):
        value = case.inputs[position]
        width = case.input_widths[position]
        if _is_mask_type(type_):
            expression = "[true]" if value else "[false]"
        elif lean_argument.transform is OperandTransform.IDENTITY:
            expression = (
                f"[{_bv(value, width)}]" if isinstance(type_, VectorType) else _bv(value, width)
            )
        elif lean_argument.transform is OperandTransform.UNBROADCAST:
            if not isinstance(type_, VectorType):
                raise PlainIntegerDifferentialAuditError("unbroadcast source is not a vector")
            expression = _bv(value, width)
        else:
            raise PlainIntegerDifferentialAuditError(
                f"unsupported P3 transform: {lean_argument.transform.value}"
            )
        arguments.append(expression)
    invocation = f"{spec.lean_name} {' '.join(arguments)}"
    if _is_mask_type(spec.signature.result):
        return f"if ({invocation}).getD {case.observed_lane} false then 1 else 0"
    zero = _bv(0, case.output_width)
    return f"(({invocation}).getD {case.observed_lane} {zero}).toNat"


def evaluate_lean(
    root: Path, subjects: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, int], dict[str, Any]]:
    lake = shutil.which("lake")
    if lake is None:
        raise PlainIntegerDifferentialAuditError("Lean evaluator requires lake")
    source_lines = ["import SALT.Intrinsics.Neon", "import SALT.Intrinsics.RVV", ""]
    for subject in subjects:
        for case in _make_cases(subject):
            source_lines.append(
                f'#eval IO.println s!"PLAININT|{case.case_id}|{{{_lean_expression(subject, case)}}}"'
            )
    source = "\n".join(source_lines) + "\n"
    with tempfile.TemporaryDirectory(prefix="saltyrn-plain-int-lean-") as directory:
        path = Path(directory) / "PlainIntegerDifferentialAudit.lean"
        path.write_text(source, encoding="utf-8")
        completed = _run(
            [lake, "env", "lean", str(path)],
            cwd=root / "src/verification_bw/lean",
        )
    if completed.returncode != 0:
        raise PlainIntegerDifferentialAuditError(
            f"Lean evaluator failed:\n{completed.stdout}\n{completed.stderr}"
        )
    values: dict[str, int] = {}
    for line in completed.stdout.splitlines():
        if line.startswith("PLAININT|"):
            _, case_id, value = line.split("|", 2)
            values[case_id] = int(value)
    expected = sum(len(_make_cases(subject)) for subject in subjects)
    if len(values) != expected:
        raise PlainIntegerDifferentialAuditError(
            f"Lean evaluator returned {len(values)}/{expected} values"
        )
    return values, {
        "backend": "lean-kernel-evaluator",
        "command": ["lake", "env", "lean", "<temporary>/PlainIntegerDifferentialAudit.lean"],
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "status": "passed",
    }


_NEON_DUP = {
    "int8x8_t": "vdup_n_s8", "int8x16_t": "vdupq_n_s8",
    "uint8x8_t": "vdup_n_u8", "uint8x16_t": "vdupq_n_u8",
    "int16x4_t": "vdup_n_s16", "int16x8_t": "vdupq_n_s16",
    "uint16x4_t": "vdup_n_u16", "uint16x8_t": "vdupq_n_u16",
    "int32x2_t": "vdup_n_s32", "int32x4_t": "vdupq_n_s32",
    "uint32x2_t": "vdup_n_u32", "uint32x4_t": "vdupq_n_u32",
}
_NEON_GET = {
    "int8x8_t": "vget_lane_s8", "int8x16_t": "vgetq_lane_s8",
    "uint8x8_t": "vget_lane_u8", "uint8x16_t": "vgetq_lane_u8",
    "int16x4_t": "vget_lane_s16", "int16x8_t": "vgetq_lane_s16",
    "uint16x4_t": "vget_lane_u16", "uint16x8_t": "vgetq_lane_u16",
    "int32x2_t": "vget_lane_s32", "int32x4_t": "vgetq_lane_s32",
    "uint32x2_t": "vget_lane_u32", "uint32x4_t": "vgetq_lane_u32",
}


def _neon_wrapper(index: int, subject: Mapping[str, Any]) -> str:
    spec: SemanticIntrinsic = subject["spec"]
    declarations: list[str] = []
    arguments: list[str] = []
    input_index = 0
    names = ("a", "b", "c")
    for parameter in spec.signature.parameters:
        type_ = parameter.type
        if not isinstance(type_, VectorType):
            raise PlainIntegerDifferentialAuditError(
                f"unexpected Neon scalar parameter: {spec.spelling}"
            )
        helper = _NEON_DUP.get(type_.c_spelling)
        if helper is None:
            raise PlainIntegerDifferentialAuditError(
                f"unsupported Neon vector type: {type_.c_spelling}"
            )
        scalar = names[input_index]
        declarations.append(
            f"  {type_.c_spelling} p{input_index} = {helper}(({type_.element.c_spelling}){scalar});"
        )
        arguments.append(f"p{input_index}")
        input_index += 1
    result_type = spec.signature.result
    if not isinstance(result_type, VectorType) or result_type.c_spelling not in _NEON_GET:
        raise PlainIntegerDifferentialAuditError(f"unsupported Neon result: {spec.spelling}")
    getter = _NEON_GET[result_type.c_spelling]
    return (
        f"static NOINLINE uint64_t run_{index}(uint64_t a, uint64_t b, uint64_t c) {{\n"
        + "  (void)a; (void)b; (void)c;\n"
        + "\n".join(declarations)
        + f"\n  {result_type.c_spelling} result = {spec.spelling}({', '.join(arguments)});\n"
        + f"  return (uint64_t)({result_type.element.c_spelling}){getter}(result, 0);\n"
        + "}\n"
    )


def _neon_probe_source(subjects: Sequence[Mapping[str, Any]]) -> tuple[str, tuple[PlainCase, ...]]:
    neon = [item for item in subjects if item["capability"]["architecture"] == "neon"]
    wrappers = [_neon_wrapper(index, subject) for index, subject in enumerate(neon)]
    calls: list[str] = []
    cases: list[PlainCase] = []
    for index, subject in enumerate(neon):
        for case in _make_cases(subject):
            cases.append(case)
            values = list(case.inputs) + [0, 0, 0]
            calls.append(
                f'  printf("PLAININT|{case.case_id}|%016" PRIX64 "\\n", '
                f"run_{index}(UINT64_C(0x{values[0]:016X}), "
                f"UINT64_C(0x{values[1]:016X}), UINT64_C(0x{values[2]:016X})));"
            )
    source = f'''#if !defined(__aarch64__)
#error "native plain-integer probe requires AArch64"
#endif
#include <arm_neon.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

#define NOINLINE __attribute__((noinline))

{chr(10).join(wrappers)}
int main(void) {{
{chr(10).join(calls)}
  return 0;
}}
'''
    return source, tuple(cases)


def run_native_neon(
    root: Path, subjects: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, int], dict[str, Any]]:
    source, cases = _neon_probe_source(subjects)
    machine = platform.machine().lower()
    clang = shutil.which("clang")
    base = {
        "backend": "native-aarch64-neon-c-intrinsics",
        "host_machine": machine,
        "probe_source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "state_scope": "active-lane-value-only",
    }
    if machine not in {"arm64", "aarch64"}:
        return {}, {**base, "status": "blocked", "blocked_reason": "host-not-aarch64"}
    if clang is None:
        return {}, {**base, "status": "blocked", "blocked_reason": "clang-not-found"}
    with tempfile.TemporaryDirectory(prefix="saltyrn-plain-int-neon-") as directory:
        directory_path = Path(directory)
        source_path = directory_path / "probe.c"
        binary_path = directory_path / "probe"
        assembly_path = directory_path / "probe.s"
        source_path.write_text(source, encoding="utf-8")
        command = [
            clang, "-std=c11", "-O0", "-Wall", "-Wextra", "-Werror",
            "-Wl,-no_uuid", str(source_path), "-o", str(binary_path),
        ]
        compiled = _run(command, cwd=root)
        if compiled.returncode != 0:
            return {}, {
                **base, "status": "blocked", "blocked_reason": "native-probe-compile-failed",
                "compiler_stderr": compiled.stderr,
            }
        assembly = _run(
            [clang, "-std=c11", "-O0", "-S", str(source_path), "-o", str(assembly_path)],
            cwd=root,
        )
        if assembly.returncode != 0:
            raise PlainIntegerDifferentialAuditError("native Neon assembly emission failed")
        assembly_text = assembly_path.read_text(encoding="utf-8")
        required_mnemonics = sorted(
            {
                str(subject["audit"]["primary_evidence"]["instruction"])
                .split(None, 1)[0]
                .lower()
                for subject in subjects
                if subject["capability"]["architecture"] == "neon"
            }
        )
        missing_mnemonics = [
            mnemonic
            for mnemonic in required_mnemonics
            if re.search(rf"\b{re.escape(mnemonic)}\b", assembly_text.lower()) is None
        ]
        executed = _run([str(binary_path)], cwd=root)
        if executed.returncode != 0:
            raise PlainIntegerDifferentialAuditError("native Neon probe execution failed")
        results: dict[str, int] = {}
        width_by_id = {case.case_id: case.output_width for case in cases}
        for line in executed.stdout.splitlines():
            if line.startswith("PLAININT|"):
                _, case_id, value = line.split("|", 2)
                results[case_id] = int(value, 16) & ((1 << width_by_id[case_id]) - 1)
        if len(results) != len(cases):
            raise PlainIntegerDifferentialAuditError(
                f"native Neon returned {len(results)}/{len(cases)} values"
            )
        evidence = {
            **base, "status": "passed", "compiler_version": _tool_version(clang),
            "compile_command": ["clang", "-std=c11", "-O0", "<temporary>/probe.c"],
            "official_instruction_mnemonics_checked": required_mnemonics,
            "direct_mnemonics_present": [
                mnemonic for mnemonic in required_mnemonics if mnemonic not in missing_mnemonics
            ],
            "direct_mnemonics_absent_due_to_compiler_lowering": missing_mnemonics,
            "binary_sha256": _sha256(binary_path),
            "assembly_sha256": _sha256(assembly_path) if assembly.returncode == 0 else None,
        }
    return results, evidence


def _rvv_suffix(type_: VectorType) -> str:
    matched = re.fullmatch(r"v(u?int)(8|16|32)m(2|4|8)_t", type_.c_spelling)
    if matched is None:
        raise PlainIntegerDifferentialAuditError(f"unsupported RVV vector: {type_.c_spelling}")
    signed = "u" if matched.group(1).startswith("u") else "i"
    return f"{signed}{matched.group(2)}m{matched.group(3)}"


def _rvv_wrapper(index: int, subject: Mapping[str, Any]) -> str:
    spec: SemanticIntrinsic = subject["spec"]
    result = spec.signature.result
    if not isinstance(result, VectorType):
        raise PlainIntegerDifferentialAuditError(f"unsupported RVV result: {spec.spelling}")
    result_mask = _is_mask_type(result)
    sew = 32 if result_mask else result.element.bit_width
    if result_mask:
        for parameter in spec.signature.parameters:
            if isinstance(parameter.type, VectorType) and not _is_mask_type(parameter.type):
                sew = parameter.type.element.bit_width
                break
    declarations = [f"  size_t vl = __riscv_vsetvl_e{sew}m8(1);"]
    arguments: list[str] = []
    input_index = 0
    names = ("a", "b", "c")
    for parameter in spec.signature.parameters:
        type_ = parameter.type
        if isinstance(type_, ScalarType) and type_.c_spelling == "size_t":
            arguments.append("vl")
            continue
        scalar = names[input_index]
        if isinstance(type_, VectorType) and _is_mask_type(type_):
            declarations.append(
                f"  {type_.c_spelling} p{input_index} = ({scalar} & 1) ? "
                "__riscv_vmset_m_b4(vl) : __riscv_vmclr_m_b4(vl);"
            )
        elif isinstance(type_, VectorType):
            suffix = _rvv_suffix(type_)
            declarations.append(
                f"  {type_.c_spelling} p{input_index} = __riscv_vmv_v_x_{suffix}"
                f"(({type_.element.c_spelling}){scalar}, vl);"
            )
        elif isinstance(type_, ScalarType):
            declarations.append(
                f"  {type_.c_spelling} p{input_index} = ({type_.c_spelling}){scalar};"
            )
        else:
            raise PlainIntegerDifferentialAuditError(
                f"unsupported RVV parameter for {spec.spelling}: {type_!r}"
            )
        arguments.append(f"p{input_index}")
        input_index += 1
    body = "\n".join(declarations)
    body += f"\n  {result.c_spelling} result = {spec.spelling}({', '.join(arguments)});\n"
    if result_mask:
        body += "  return (uint64_t)__riscv_vcpop_m_b4(result, vl);"
    else:
        suffix = _rvv_suffix(result)
        body += (
            f"  {result.element.c_spelling} output = 0;\n"
            f"  __riscv_vse{result.element.bit_width}_v_{suffix}(&output, result, vl);\n"
            "  return (uint64_t)output;"
        )
    return (
        f"NOINLINE uint64_t run_{index}(uint64_t a, uint64_t b, uint64_t c) {{\n"
        f"{body}\n}}\n"
    )


def _rvv_probe_sources(
    subjects: Sequence[Mapping[str, Any]],
) -> tuple[str, str, tuple[PlainCase, ...]]:
    rvv = [item for item in subjects if item["capability"]["architecture"] == "rvv"]
    wrappers = [_rvv_wrapper(index, subject) for index, subject in enumerate(rvv)]
    cases: list[PlainCase] = []
    start = [
        ".option norvc", ".text", ".globl _start", "_start:",
        "  li sp, 0x80020000", "  li t0, 0x600", "  csrs mstatus, t0",
    ]
    for index, subject in enumerate(rvv):
        for case in _make_cases(subject):
            cases.append(case)
            values = list(case.inputs) + [0, 0, 0]
            start.extend(
                [
                    f"  # PLAININT {case.case_id}",
                    f"  li a0, 0x{values[0]:016X}",
                    f"  li a1, 0x{values[1]:016X}",
                    f"  li a2, 0x{values[2]:016X}",
                    f"  call run_{index}", "  mv s1, a0",
                ]
            )
    start.extend(["done:", "  j done", ""])
    c_source = f'''#include <riscv_vector.h>
#include <stddef.h>
#include <stdint.h>

#define NOINLINE __attribute__((noinline))

{chr(10).join(wrappers)}
'''
    return c_source, "\n".join(start), tuple(cases)


def run_spike_rvv(
    root: Path, subjects: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, int], dict[str, Any]]:
    spike = shutil.which("spike")
    linker = shutil.which("riscv64-elf-ld")
    objdump = shutil.which("riscv64-elf-objdump")
    clang_candidates = [
        Path("/opt/homebrew/opt/llvm/bin/clang"),
        Path(shutil.which("clang-20") or ""), Path(shutil.which("clang") or ""),
    ]
    cross_clang = next((str(path) for path in clang_candidates if path.is_file()), None)
    c_source, start_source, cases = _rvv_probe_sources(subjects)
    tools = {"cross_clang": cross_clang, "linker": linker, "objdump": objdump, "spike": spike}
    base = {
        "backend": "spike-rvv-c-intrinsics", "tools": tools,
        "probe_c_source_sha256": hashlib.sha256(c_source.encode()).hexdigest(),
        "probe_start_source_sha256": hashlib.sha256(start_source.encode()).hexdigest(),
        "isa": "rv64gcv_zvl128b", "state_scope": "active-lane-value-only;vl=1",
    }
    missing = [name for name, path in tools.items() if path is None]
    if missing:
        return {}, {**base, "status": "blocked", "blocked_reason": "missing-rvv-toolchain:" + ",".join(missing)}
    with tempfile.TemporaryDirectory(prefix="saltyrn-plain-int-rvv-") as directory:
        directory_path = Path(directory)
        c_path, start_path = directory_path / "probe.c", directory_path / "start.S"
        c_object, start_object = directory_path / "probe.o", directory_path / "start.o"
        elf_path, disassembly_path = directory_path / "probe.elf", directory_path / "probe.disassembly.txt"
        c_path.write_text(c_source, encoding="utf-8")
        start_path.write_text(start_source, encoding="utf-8")
        common = [cross_clang, "--target=riscv64-unknown-elf", "-march=rv64gcv_zvl128b", "-mabi=lp64d"]
        compiled_c = _run(common + ["-O0", "-ffreestanding", "-c", str(c_path), "-o", str(c_object)], cwd=root)
        compiled_start = _run(common + ["-c", str(start_path), "-o", str(start_object)], cwd=root)
        if compiled_c.returncode != 0 or compiled_start.returncode != 0:
            return {}, {
                **base, "status": "blocked", "blocked_reason": "rvv-c-intrinsic-cross-compile-failed",
                "compiler_stderr": compiled_c.stderr + compiled_start.stderr,
            }
        linked = _run(
            [linker, "-Ttext=0x80001000", "-e", "_start", "--no-relax", str(start_object), str(c_object), "-o", str(elf_path)],
            cwd=root,
        )
        if linked.returncode != 0:
            return {}, {**base, "status": "blocked", "blocked_reason": "rvv-bare-metal-link-failed", "linker_stderr": linked.stderr}
        disassembled = _run([objdump, "-d", str(elf_path)], cwd=root)
        if disassembled.returncode != 0:
            return {}, {**base, "status": "blocked", "blocked_reason": "rvv-disassembly-failed"}
        normalized = disassembled.stdout.replace(str(directory_path), "<temporary>")
        disassembly_path.write_text(normalized, encoding="utf-8")
        for subject in subjects:
            if subject["capability"]["architecture"] != "rvv":
                continue
            selector = subject["audit"]["primary_evidence"]["isa_selector"]
            if selector not in disassembled.stdout:
                vector_lines = [
                    line.strip()
                    for line in disassembled.stdout.splitlines()
                    if re.search(r"\bv(?:m|w|s|z|a|o|r)[a-z0-9.]+\b", line)
                ]
                raise PlainIntegerDifferentialAuditError(
                    f"compiled RVV probe lacks selector {selector}; "
                    f"vector instructions={vector_lines[:80]!r}"
                )
        instruction_limit = max(10000, len(cases) * 140)
        command = [
            spike, "--isa=rv64gcv_zvl128b", "--pc=0x80001000",
            f"--instructions={instruction_limit}", "-l", "--log-commits", str(elf_path),
        ]
        executed = _run(command, cwd=root)
        log = executed.stdout + executed.stderr
        if executed.returncode != 0:
            return {}, {**base, "status": "blocked", "blocked_reason": "spike-execution-failed", "spike_log_tail": log[-4000:]}
        pattern = re.compile(
            r"\([^)]*\)\s+(?:mv|addi)\s+s1,\s*a0(?:,\s*0)?\n"
            r"core\s+0:\s+3\s+[^\n]*\bx9\s+0x([0-9a-fA-F]{16})"
        )
        values = [int(value, 16) for value in pattern.findall(log)]
        if len(values) != len(cases):
            raise PlainIntegerDifferentialAuditError(
                f"Spike returned {len(values)}/{len(cases)} marked values"
            )
        results = {
            case.case_id: value & ((1 << case.output_width) - 1)
            for case, value in zip(cases, values, strict=True)
        }
        evidence = {
            **base, "status": "passed", "compiler_version": _tool_version(cross_clang),
            "linker_version": _tool_version(linker), "objdump_version": _tool_version(objdump),
            "spike_version": _tool_version(spike), "elf_sha256": _sha256(elf_path),
            "disassembly_sha256": _sha256(disassembly_path),
            "commit_log_sha256": hashlib.sha256(log.encode()).hexdigest(),
        }
    return results, evidence


def _definition_evidence(root: Path, symbol: str) -> dict[str, Any]:
    architecture = "Neon" if ".Neon." in symbol else "RVV"
    path = root / f"src/verification_bw/lean/SALT/Intrinsics/{architecture}.lean"
    name = symbol.rsplit(".", 1)[1]
    pattern = re.compile(rf"^def\s+{re.escape(name)}\b")
    lines = path.read_text(encoding="utf-8").splitlines()
    line = next((index for index, text in enumerate(lines, 1) if pattern.match(text)), None)
    if line is None:
        raise PlainIntegerDifferentialAuditError(f"Lean definition absent: {symbol}")
    definition = lines[line - 1]
    cursor = line
    while cursor < len(lines) and (cursor == line or lines[cursor].startswith(" ")):
        definition += "\n" + lines[cursor]
        cursor += 1
    return {
        "symbol": symbol, "definition_path": path.relative_to(root).as_posix(),
        "definition_line": line, "definition_file_sha256": _sha256(path),
        "definition_sha256": hashlib.sha256(definition.encode()).hexdigest(),
    }


def _c_calls(root: Path, audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    side = "source" if audit["architecture"] == "neon" else "target"
    calls: list[dict[str, Any]] = []
    for program in audit["programs"]:
        path = root / f"kernels/{side}/{program}.c"
        digest = _sha256(path)
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(rf"\b{re.escape(audit['spelling'])}\s*\(", line):
                calls.append({
                    "path": path.relative_to(root).as_posix(), "line": number,
                    "text": line.strip(), "file_sha256": digest,
                })
    if audit["used"] and not calls:
        raise PlainIntegerDifferentialAuditError(
            f"used exact row lacks real C call: {audit['capability_id']}"
        )
    return calls


def _authority_evidence(root: Path, evidence: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(evidence)
    path = root / str(evidence["path"])
    result["local_file_available"] = path.is_file()
    result["local_file_matches_recorded_sha256"] = (
        path.is_file() and _sha256(path) == evidence["file_sha256"]
    )
    if not path.is_file():
        result["local_blocked_reason"] = "pinned-authority-file-not-present-in-checkout"
    return result


def _descriptor_lowering(spec: SemanticIntrinsic) -> list[dict[str, Any]]:
    return [
        {
            "source_argument_index": argument.source_index,
            "source_parameter": spec.signature.parameters[argument.source_index].name,
            "source_type": spec.signature.parameters[argument.source_index].type.c_spelling,
            "transform": argument.transform.value,
        }
        for argument in spec.lean_arguments
    ]


def _broadcast_provenance_audit(root: Path) -> dict[str, Any]:
    facade = root / "src/workflow/verification/lean_backend/facade/qs8_vadd_minmax.h"
    neon_path = root / "kernels/source/qs8-vadd-minmax.c"
    rvv_path = root / "kernels/target/qs8-vadd-minmax.c"
    neon = parse_kernel(neon_path, facade=facade)
    rvv = parse_kernel(rvv_path, facade=facade)
    manifest = build_manifest(neon, rvv, workspace_root=root)
    spellings = {"vmulq_s32", "vmlaq_s32", "vqaddq_s16"}
    occurrences: list[dict[str, Any]] = []
    for call in manifest["kernels"]["neon"]["calls"]:
        if call["spelling"] not in spellings:
            continue
        transformed = [
            {
                "argument_index": index,
                "source_text": argument["source_text"],
                "transform_provenance": argument["transform_provenance"],
            }
            for index, argument in enumerate(call["arguments"])
            if argument["transform_provenance"] is not None
        ]
        if len(transformed) != 1:
            raise PlainIntegerDifferentialAuditError(
                f"unexpected I1 provenance count: {call['node_id']}"
            )
        occurrences.append({
            "spelling": call["spelling"], "node_id": call["node_id"],
            "source": call["source"], "transformed_argument": transformed[0],
        })
    if {item["spelling"] for item in occurrences} != spellings:
        raise PlainIntegerDifferentialAuditError("I1 provenance spellings incomplete")

    target = next(call for call in neon.calls if call.spelling == "vmlaq_s32")
    arguments = list(target.arguments)
    source_index = 2
    arguments[source_index] = dataclasses.replace(
        arguments[source_index], dependencies=("vacc0123@0",), source_text="vacc0123"
    )
    mutated_calls = tuple(
        dataclasses.replace(
            call, arguments=tuple(arguments),
            dependencies=tuple(dict.fromkeys(d for arg in arguments for d in arg.dependencies)),
        ) if call.node_id == target.node_id else call
        for call in neon.calls
    )
    mutation = dataclasses.replace(neon, calls=mutated_calls)
    try:
        bind_kernel(mutation, workspace_root=root)
    except OperandProvenanceError as error:
        rejection = {
            "status": "passed-rejected", "error_type": type(error).__name__,
            "mutated_consumer": target.spelling, "mutated_argument_index": source_index,
            "replacement_source_text": "vacc0123", "message": str(error),
        }
    else:
        raise PlainIntegerDifferentialAuditError("non-broadcast I1 mutation was accepted")
    return {
        "positive_manifest_path": "generated-in-memory-from-kernels/source/qs8-vadd-minmax.c",
        "positive_occurrences": occurrences,
        "nonuniform_vector_mutation": rejection,
        "claim": (
            "current I1 lowering is valid only when the transformed vector is proven to come "
            "from a reviewed broadcast; a non-broadcast producer fails closed"
        ),
    }


def build_audit(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    corpus = root / "verification/elementwise-compiler"
    subjects = load_exact_subjects(root)
    lean_results, lean_backend = evaluate_lean(root, subjects)
    neon_results, neon_backend = run_native_neon(root, subjects)
    rvv_results, rvv_backend = run_spike_rvv(root, subjects)
    provenance = _broadcast_provenance_audit(root)
    rows: list[dict[str, Any]] = []
    for subject in subjects:
        capability, audit, spec = subject["capability"], subject["audit"], subject["spec"]
        backend = neon_backend if capability["architecture"] == "neon" else rvv_backend
        actuals = neon_results if capability["architecture"] == "neon" else rvv_results
        cases: list[dict[str, Any]] = []
        for case in _make_cases(subject):
            expected = lean_results[case.case_id]
            actual = actuals.get(case.case_id)
            verdict = "blocked" if backend["status"] == "blocked" else (
                "passed" if actual == expected else "mismatch"
            )
            cases.append({
                "case_id": case.case_id,
                "inputs_bits": [
                    f"0x{value:0{(width + 3) // 4}X}"
                    for value, width in zip(case.inputs, case.input_widths)
                ],
                "input_widths": list(case.input_widths), "observed_lane": case.observed_lane,
                "output_width": case.output_width,
                "expected_bits": f"0x{expected:0{(case.output_width + 3) // 4}X}",
                "actual_bits": None if actual is None else f"0x{actual:0{(case.output_width + 3) // 4}X}",
                "verdict": verdict,
            })
        contextual = any(
            argument.transform is OperandTransform.UNBROADCAST
            for argument in spec.lean_arguments
        )
        execution_status = "blocked" if backend["status"] == "blocked" else (
            "mismatch" if any(case["verdict"] == "mismatch" for case in cases) else "passed"
        )
        status = "conditional" if contextual and execution_status == "passed" else execution_status
        cleanup = capability["capability_id"] in LEGACY_CONTEXTUAL_IDS
        row = {
            "capability_id": capability["capability_id"],
            "semantic_family": subject["semantic_family"], "subject_scope": subject["subject_scope"],
            "registry_used": bool(audit["used"]), "architecture": capability["architecture"],
            "spelling": capability["spelling"], "function_type": capability["function_type"],
            "descriptor_sha256": capability["descriptor_sha256"],
            "descriptor_operand_lowering": _descriptor_lowering(spec),
            "c_calls": _c_calls(root, audit),
            "official_pinned_source": _authority_evidence(root, audit["primary_evidence"]),
            "lean": _definition_evidence(root, capability["semantic_symbol"]),
            "oracle_backend": backend, "evidence_level": EVIDENCE_LEVEL,
            "coverage_scope": COVERAGE_SCOPE,
            "context_condition": (
                "transformed vector operand must have reviewed uniform-broadcast provenance"
                if contextual else None
            ),
            "cleanup_recommendation": (
                "replace with faithful vector-vector identity descriptor and collapse into the existing correct capability"
                if cleanup else (
                    "migrate to vector-vector Lean semantics plus identity operand lowering"
                    if contextual else None
                )
            ),
            "cases": cases, "execution_status": execution_status, "status": status,
        }
        row["evidence_sha256"] = canonical_sha256(row)
        rows.append(row)
    counts = {
        "subjects": len(rows), "current_subjects": sum(row["subject_scope"] == "current-exact" for row in rows),
        "legacy_cleanup_candidates": sum(row["subject_scope"] == "explicit-unused-cleanup-candidate" for row in rows),
        "passed_subjects": sum(row["status"] == "passed" for row in rows),
        "conditional_subjects": sum(row["status"] == "conditional" for row in rows),
        "blocked_subjects": sum(row["status"] == "blocked" for row in rows),
        "mismatch_subjects": sum(row["status"] == "mismatch" for row in rows),
        "test_vectors": sum(len(row["cases"]) for row in rows),
        "executed_vectors": sum(case["actual_bits"] is not None for row in rows for case in row["cases"]),
    }
    record = {
        "artifact_kind": ARTIFACT_KIND, "schema_version": SCHEMA_VERSION,
        "evidence_level": EVIDENCE_LEVEL, "coverage_scope": COVERAGE_SCOPE,
        "verdict_definition": (
            "passed means every listed boundary vector matched the recorded architecture oracle; "
            "conditional additionally requires the stated broadcast provenance; this is sampled L3 evidence, not a full proof"
        ),
        "selected_semantic_families": sorted(FAMILIES),
        "explicit_legacy_cleanup_capability_ids": sorted(LEGACY_CONTEXTUAL_IDS),
        "registry_path": "verification/elementwise-compiler/IntrinsicRegistry.json",
        "registry_sha256": _load_json(corpus / "IntrinsicRegistry.json")["registry_sha256"],
        "registry_file_sha256": _sha256(corpus / "IntrinsicRegistry.json"),
        "intrinsic_audit_path": "verification/elementwise-compiler/IntrinsicAudit.json",
        "intrinsic_audit_sha256": _load_json(corpus / "IntrinsicAudit.json")["audit_sha256"],
        "intrinsic_audit_file_sha256": _sha256(corpus / "IntrinsicAudit.json"),
        "review_plan_path": "verification/elementwise-compiler/IntrinsicReviewPlan.json",
        "review_plan_file_sha256": _sha256(corpus / "IntrinsicReviewPlan.json"),
        "lean_backend": lean_backend,
        "toolchain_inventory": {"native_neon": neon_backend, "rvv": rvv_backend},
        "broadcast_provenance_audit": provenance,
        "ledger_projection_path": "verification/elementwise-compiler/PlainIntegerDifferentialAuditLedger.csv",
        "ledger_join_key": "capability_id", "counts": counts, "subjects": rows,
    }
    validate_audit(record)
    record["audit_sha256"] = canonical_sha256(record)
    return record


def render_ledger_projection(record: Mapping[str, Any]) -> str:
    fields = (
        "capability_id", "semantic_family", "subject_scope", "registry_used",
        "evidence_level", "coverage_scope", "differential_test_status",
        "context_condition", "oracle_backend", "executed_vectors", "total_vectors",
        "mismatch_found", "cleanup_recommendation", "evidence_path",
        "evidence_sha256", "full_intrinsic_proof",
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in sorted(record["subjects"], key=lambda item: item["capability_id"]):
        writer.writerow({
            "capability_id": row["capability_id"], "semantic_family": row["semantic_family"],
            "subject_scope": row["subject_scope"], "registry_used": "yes" if row["registry_used"] else "no",
            "evidence_level": EVIDENCE_LEVEL, "coverage_scope": COVERAGE_SCOPE,
            "differential_test_status": row["status"] + "-sampled",
            "context_condition": row["context_condition"] or "",
            "oracle_backend": row["oracle_backend"]["backend"],
            "executed_vectors": sum(case["actual_bits"] is not None for case in row["cases"]),
            "total_vectors": len(row["cases"]),
            "mismatch_found": "yes" if row["execution_status"] == "mismatch" else "no",
            "cleanup_recommendation": row["cleanup_recommendation"] or "",
            "evidence_path": "verification/elementwise-compiler/PlainIntegerDifferentialAudit.json",
            "evidence_sha256": row["evidence_sha256"], "full_intrinsic_proof": "no",
        })
    return stream.getvalue()


def validate_audit(record: Mapping[str, Any]) -> None:
    if record.get("artifact_kind") != ARTIFACT_KIND or record.get("schema_version") != 1:
        raise PlainIntegerDifferentialAuditError("invalid plain-integer audit kind/schema")
    if record.get("evidence_level") != EVIDENCE_LEVEL or record.get("coverage_scope") != COVERAGE_SCOPE:
        raise PlainIntegerDifferentialAuditError("plain-integer evidence scope changed")
    rows = record.get("subjects")
    if not isinstance(rows, list) or len(rows) != 65:
        raise PlainIntegerDifferentialAuditError("plain-integer audit must contain 65 subjects")
    seen: set[str] = set()
    for row in rows:
        capability_id = row.get("capability_id")
        if not isinstance(capability_id, str) or capability_id in seen:
            raise PlainIntegerDifferentialAuditError("capability IDs must be unique")
        seen.add(capability_id)
        unsigned = dict(row)
        digest = unsigned.pop("evidence_sha256", None)
        if digest != canonical_sha256(unsigned):
            raise PlainIntegerDifferentialAuditError(f"subject digest mismatch: {capability_id}")
        if row.get("status") not in {"passed", "conditional", "blocked", "mismatch"}:
            raise PlainIntegerDifferentialAuditError(f"invalid status: {capability_id}")
        if not row.get("descriptor_operand_lowering") or not row.get("lean"):
            raise PlainIntegerDifferentialAuditError(f"missing lowering/Lean trace: {capability_id}")
        if row.get("registry_used") and not row.get("c_calls"):
            raise PlainIntegerDifferentialAuditError(f"used row lacks C calls: {capability_id}")
        if row.get("subject_scope") == "explicit-unused-cleanup-candidate":
            if capability_id not in LEGACY_CONTEXTUAL_IDS or row.get("cleanup_recommendation") is None:
                raise PlainIntegerDifferentialAuditError("legacy cleanup judgment absent")
        cases = row.get("cases")
        if not isinstance(cases, list) or not cases:
            raise PlainIntegerDifferentialAuditError(f"subject lacks sampled cases: {capability_id}")
        for case in cases:
            if case.get("verdict") not in {"passed", "blocked", "mismatch"}:
                raise PlainIntegerDifferentialAuditError(f"invalid case verdict: {capability_id}")


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output", type=Path,
        default=Path("verification/elementwise-compiler/PlainIntegerDifferentialAudit.json"),
    )
    parser.add_argument(
        "--ledger-output", type=Path,
        default=Path("verification/elementwise-compiler/PlainIntegerDifferentialAuditLedger.csv"),
    )
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    output = arguments.output if arguments.output.is_absolute() else root / arguments.output
    ledger = arguments.ledger_output if arguments.ledger_output.is_absolute() else root / arguments.ledger_output
    record = build_audit(root)
    rendered, projected = canonical_json(record, pretty=True), render_ledger_projection(record)
    if arguments.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise PlainIntegerDifferentialAuditError(f"stale plain-integer audit: {output}")
        if not ledger.is_file() or ledger.read_text(encoding="utf-8") != projected:
            raise PlainIntegerDifferentialAuditError(f"stale plain-integer ledger: {ledger}")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(projected, encoding="utf-8")
    print(json.dumps(record["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
