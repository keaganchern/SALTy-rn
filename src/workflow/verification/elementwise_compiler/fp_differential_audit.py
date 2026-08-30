"""Reproducible architecture-oracle audit for high-risk FP intrinsics.

The checked intrinsic registry remains the source of exact capability identities.
This command joins each subject to its C call sites, pinned authority metadata and
Lean symbol, evaluates the Lean value model, and runs an independent architecture
probe when the current host has a supported backend.  Missing backends are evidence:
they produce explicit, content-addressed ``blocked`` records rather than a pass.
"""

from __future__ import annotations

import argparse
import csv
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

from ..lean_backend.descriptor import canonical_spec_digest, canonical_spec_record
from ..lean_backend.intrinsic_index import CANONICAL_INTRINSIC_INDEX
from .schema import canonical_json, canonical_sha256


SCHEMA_VERSION = 2
ARTIFACT_KIND = "fp-intrinsic-differential-audit"
EVIDENCE_LEVEL = "L3-sampled"
COVERAGE_SCOPE = (
    "listed-boundary-vectors-only;not-exhaustive;pure-active-lane-value;"
    "flags-traps-memory-and-full-ISA-refinement-excluded"
)

REVIEW_FAMILY_PATTERN = re.compile(r"^FP[0-4]-")
EXPECTED_EXACT_SUBJECTS = 28


class FPDifferentialAuditError(RuntimeError):
    """The exact corpus, evaluator, architecture probe, or evidence is malformed."""


@dataclass(frozen=True, slots=True)
class VectorCase:
    case_id: str
    inputs: tuple[int, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(
    command: Sequence[str], *, cwd: Path, timeout: int = 120
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FPDifferentialAuditError(f"expected JSON object: {path}")
    return value


def load_exact_subjects(corpus: Path) -> tuple[dict[str, Any], ...]:
    """Join every FP0--FP4 exact subject without collapsing equal spellings."""

    registry = _load_json(corpus / "IntrinsicRegistry.json")
    audit = _load_json(corpus / "IntrinsicAudit.json")
    plan = _load_json(corpus / "IntrinsicReviewPlan.json")
    audit_by_id = {row["capability_id"]: row for row in audit["variants"]}
    plan_by_id: dict[str, tuple[str, dict[str, Any]]] = {}
    for family in plan["families"]:
        family_name = family["family"]
        if REVIEW_FAMILY_PATTERN.match(family_name) is None:
            continue
        for planned in family["subjects"]:
            capability_id = planned["capability_id"]
            if capability_id in plan_by_id:
                raise FPDifferentialAuditError(
                    f"duplicate exact FP review-plan subject: {capability_id}"
                )
            plan_by_id[capability_id] = (family_name, planned)
    if len(plan_by_id) != EXPECTED_EXACT_SUBJECTS:
        raise FPDifferentialAuditError(
            f"FP0--FP4 exact set changed: {len(plan_by_id)}/{EXPECTED_EXACT_SUBJECTS}"
        )

    descriptor_by_digest = {
        canonical_spec_digest(variant.spec): canonical_spec_record(variant.spec)
        for variant in CANONICAL_INTRINSIC_INDEX.variants
    }
    subjects: list[dict[str, Any]] = []
    for variant in registry["variants"]:
        capability = variant["capability"]
        capability_id = capability["capability_id"]
        if capability_id not in plan_by_id:
            continue
        if capability_id not in audit_by_id:
            raise FPDifferentialAuditError(
                f"exact capability lacks IntrinsicAudit row: {capability_id}"
            )
        row = audit_by_id[capability_id]
        for field in (
            "architecture",
            "spelling",
            "function_type",
            "semantic_symbol",
        ):
            if row[field] != capability[field]:
                raise FPDifferentialAuditError(
                    f"registry/audit mismatch for {capability_id}: {field}"
                )
        family_name, planned = plan_by_id[capability_id]
        descriptor_digest = planned["descriptor_sha256"]
        descriptor = descriptor_by_digest.get(descriptor_digest)
        if descriptor is None:
            raise FPDifferentialAuditError(
                f"configured descriptor is absent: {capability_id} {descriptor_digest}"
            )
        parameters = descriptor["signature"]["parameters"]
        operand_mapping = []
        for argument in descriptor.get("lean_arguments", []):
            source_index = argument["source_index"]
            operand_mapping.append(
                {
                    **argument,
                    "source_parameter": parameters[source_index]["name"],
                }
            )
        subjects.append(
            {
                "capability": capability,
                "audit": row,
                "review_family": family_name,
                "planned": planned,
                "descriptor": {
                    "descriptor_sha256": descriptor_digest,
                    "shape": descriptor["shape"],
                    "argument_count": len(parameters),
                    "parameters": parameters,
                    "immediate_constraints": descriptor["immediate_constraints"],
                    "operand_mapping": operand_mapping,
                },
            }
        )
    subjects.sort(key=lambda item: item["capability"]["capability_id"])
    found = {item["capability"]["capability_id"] for item in subjects}
    if found != set(plan_by_id):
        raise FPDifferentialAuditError(
            f"FP0--FP4 registry join changed: missing={sorted(set(plan_by_id)-found)}, "
            f"extra={sorted(found-set(plan_by_id))}, count={len(subjects)}"
        )
    return tuple(subjects)


def _matrix_id(spelling: str) -> str:
    groups = (
        (("vabs", "vfabs"), "fp32-abs-v1"),
        (("vbsl",), "fp32-bitselect-v1"),
        (("vcalt",), "fp32-abs-less-than-v1"),
        (("vfsgnj",), "fp32-sign-inject-v1"),
        (("vmerge",), "fp32-mask-merge-v1"),
        (("vmfgt",), "fp32-ordered-greater-than-v1"),
        (("vmfne",), "fp32-not-equal-v1"),
        (("vmax", "vfmax"), "fp32-max-v1"),
        (("vmin", "vfmin"), "fp32-min-v1"),
        (("vadd", "vfadd"), "fp32-add-v1"),
        (("vsub", "vfsub"), "fp32-sub-v1"),
        (("vmul", "vfmul"), "fp32-mul-v1"),
        (("vdiv", "vfdiv"), "fp32-div-v1"),
        (("vsqrt", "vfsqrt"), "fp32-sqrt-v1"),
        (("vcvtq_f32_s32", "vfcvt_f_x"), "i32-to-f32-rne-v1"),
        (("vfcvt_x_f",), "f32-to-i32-rne-v1"),
    )
    for needles, matrix_id in groups:
        if any(needle in spelling for needle in needles):
            return matrix_id
    raise FPDifferentialAuditError(f"no FP case matrix for {spelling}")


def _cases(spelling: str, capability_id: str) -> tuple[VectorCase, ...]:
    prefix = f"{re.sub(r'[^a-z0-9]+', '-', spelling.lower()).strip('-')}-{capability_id.rsplit(':', 1)[1]}"
    if _matrix_id(spelling) == "fp32-abs-v1":
        values = (
            ("negative-normal", 0xBF800000),
            ("positive-normal", 0x3F800000),
            ("negative-zero", 0x80000000),
            ("smallest-subnormal", 0x00000001),
            ("negative-infinity", 0xFF800000),
            ("qnan-payload", 0xFFC12345),
            ("snan-payload", 0xFFA12345),
        )
        return tuple(VectorCase(f"{prefix}-{name}", (value,)) for name, value in values)
    if _matrix_id(spelling) == "fp32-bitselect-v1":
        values = (
            ("all-left", 0xFFFFFFFF, 0x7FC12345, 0xBF800000),
            ("all-right", 0x00000000, 0x7FC12345, 0xBF800000),
            ("alternating", 0xAAAAAAAA, 0x7FC12345, 0x80000000),
        )
        return tuple(VectorCase(f"{prefix}-{name}", inputs) for name, *inputs in values)
    if _matrix_id(spelling) == "fp32-mask-merge-v1":
        values = (
            ("false", 0x7FC12345, 0xBF800000, 0),
            ("true", 0x7FC12345, 0xBF800000, 1),
            ("signed-zero-false", 0x80000000, 0x00000000, 0),
            ("signed-zero-true", 0x80000000, 0x00000000, 1),
        )
        return tuple(VectorCase(f"{prefix}-{name}", inputs) for name, *inputs in values)
    if _matrix_id(spelling) == "fp32-sign-inject-v1":
        values = (
            ("positive-from-negative", 0x3F800000, 0xBF000000),
            ("negative-from-positive", 0xBF800000, 0x3F000000),
            ("qnan-sign", 0x7FC12345, 0xBF800000),
            ("zero-sign", 0x00000000, 0x80000000),
        )
        return tuple(VectorCase(f"{prefix}-{name}", inputs) for name, *inputs in values)
    if _matrix_id(spelling) in {
        "fp32-abs-less-than-v1",
        "fp32-ordered-greater-than-v1",
        "fp32-not-equal-v1",
    }:
        values = (
            ("less", 0x3F800000, 0x40000000),
            ("greater", 0x40000000, 0x3F800000),
            ("equal", 0x3F800000, 0x3F800000),
            ("signed-zero", 0x80000000, 0x00000000),
            ("qnan-left", 0x7FC12345, 0x3F800000),
            ("snan-right", 0x3F800000, 0x7FA12345),
            ("opposite-sign-abs", 0xBF800000, 0x3F800000),
        )
        return tuple(VectorCase(f"{prefix}-{name}", inputs) for name, *inputs in values)
    if _matrix_id(spelling) in {"fp32-max-v1", "fp32-min-v1"}:
        values = (
            ("ordered", 0x3F800000, 0x40000000),
            ("signed-zero-lr", 0x80000000, 0x00000000),
            ("signed-zero-rl", 0x00000000, 0x80000000),
            ("qnan-left", 0x7FC12345, 0x3F800000),
            ("qnan-right", 0x3F800000, 0x7FC12345),
            ("snan-left", 0x7FA12345, 0x3F800000),
            ("both-nan", 0x7FC12345, 0x7FC54321),
        )
        return tuple(VectorCase(f"{prefix}-{name}", inputs) for name, *inputs in values)
    if "sqrt" in spelling:
        values = (
            ("normal", 0x40800000),
            ("positive-zero", 0x00000000),
            ("negative-zero", 0x80000000),
            ("smallest-subnormal", 0x00000001),
            ("positive-infinity", 0x7F800000),
            ("negative-invalid", 0xBF800000),
            ("qnan-payload", 0x7FC12345),
            ("snan-payload", 0x7FA12345),
        )
        return tuple(VectorCase(f"{prefix}-{name}", (value,)) for name, value in values)
    if spelling in {"vcvtq_f32_s32", "__riscv_vfcvt_f_x_v_f32m8"}:
        values = (
            ("zero", 0),
            ("one", 1),
            ("minus-one", -1),
            ("exact-24-bit", 16777216),
            ("round-24-bit", 16777217),
            ("int32-max", 2147483647),
            ("int32-min", -2147483648),
        )
        return tuple(
            VectorCase(f"{prefix}-{name}", (value & 0xFFFFFFFF,))
            for name, value in values
        )
    if spelling == "__riscv_vfcvt_x_f_v_i32m8":
        values = (
            ("tie-even-half", 0x3F000000),
            ("above-half", 0x3F000001),
            ("tie-odd-1-5", 0x3FC00000),
            ("tie-even-2-5", 0x40200000),
            ("negative-tie", 0xBFC00000),
            ("qnan", 0x7FC12345),
            ("positive-infinity", 0x7F800000),
            ("negative-infinity", 0xFF800000),
            ("positive-overflow", 0x4F000000),
            ("negative-limit", 0xCF000000),
        )
        return tuple(VectorCase(f"{prefix}-{name}", (value,)) for name, value in values)

    binary = [
        ("normal", 0x3F800000, 0x40000000),
        ("signed-zero", 0x80000000, 0x00000000),
        ("subnormal", 0x00000001, 0x3F000000),
        ("qnan-payload", 0x7FC12345, 0x3F800000),
        ("snan-payload", 0x7FA12345, 0x3F800000),
    ]
    if "add" in spelling:
        binary.extend(
            [
                ("invalid-infinities", 0x7F800000, 0xFF800000),
                ("overflow", 0x7F7FFFFF, 0x7F7FFFFF),
            ]
        )
    elif "sub" in spelling:
        binary.extend(
            [
                ("invalid-infinities", 0x7F800000, 0x7F800000),
                ("cancellation", 0x3F800001, 0x3F800000),
            ]
        )
    elif "mul" in spelling:
        binary.extend(
            [
                ("invalid-zero-infinity", 0x00000000, 0x7F800000),
                ("overflow", 0x7F7FFFFF, 0x40000000),
            ]
        )
    elif "div" in spelling:
        binary.extend(
            [
                ("invalid-zero-zero", 0x00000000, 0x00000000),
                ("divide-by-zero", 0xBF800000, 0x00000000),
            ]
        )
    return tuple(
        VectorCase(f"{prefix}-{name}", (left, right)) for name, left, right in binary
    )


def _lean_expression(symbol: str, inputs: Sequence[int]) -> str:
    args = [f"(0x{value:08X} : BitVec 32)" for value in inputs]
    if symbol.endswith(("vabsq_f32", "vfabs_v_f32", "vsqrtq_f32", "vfsqrt_v_f32")):
        invocation = f"{symbol} [{args[0]}]"
    elif symbol.endswith("vcvtq_f32_s32") or symbol.endswith("vfcvt_f_x_v_f32"):
        invocation = f"{symbol} [{args[0]}]"
    elif symbol.endswith("vfcvt_x_f_v_i32_rne"):
        invocation = f"{symbol} [{args[0]}]"
    elif symbol.endswith("vbslq_f32"):
        invocation = f"{symbol} [{args[0]}] [{args[1]}] [{args[2]}]"
    elif symbol.endswith("vmerge_vvm_f32"):
        mask = "true" if inputs[2] else "false"
        invocation = f"{symbol} [{args[0]}] [{args[1]}] [{mask}]"
    elif "_vf_" in symbol:
        invocation = f"{symbol} [{args[0]}] {args[1]}"
    else:
        invocation = f"{symbol} [{args[0]}] [{args[1]}]"
    if symbol.endswith(("vmfgt_vf_f32", "vmfne_vv_f32")):
        return f"if ({invocation}).headD false then 1 else 0"
    return f"(({invocation}).headD 0).toNat"


def evaluate_lean(
    root: Path, subjects: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, int], dict[str, Any]]:
    lean_root = root / "src/verification_bw/lean"
    lake = shutil.which("lake")
    if lake is None:
        raise FPDifferentialAuditError("Lean evaluator is required but lake is absent")
    lines = ["import SALT.Intrinsics.Neon", "import SALT.Intrinsics.RVV", ""]
    for subject in subjects:
        symbol = subject["capability"]["semantic_symbol"]
        for case in _cases(
            subject["capability"]["spelling"], subject["capability"]["capability_id"]
        ):
            expression = _lean_expression(symbol, case.inputs)
            lines.append(f'#eval IO.println s!"FPDIFF|{case.case_id}|{{{expression}}}"')
    source = "\n".join(lines) + "\n"
    with tempfile.TemporaryDirectory(prefix="saltyrn-fp-lean-") as directory:
        path = Path(directory) / "FPDifferentialAudit.lean"
        path.write_text(source, encoding="utf-8")
        completed = _run([lake, "env", "lean", str(path)], cwd=lean_root, timeout=180)
    if completed.returncode != 0:
        raise FPDifferentialAuditError(
            f"Lean evaluator failed:\n{completed.stdout}\n{completed.stderr}"
        )
    results: dict[str, int] = {}
    for line in completed.stdout.splitlines():
        if not line.startswith("FPDIFF|"):
            continue
        _, case_id, value = line.split("|", 2)
        results[case_id] = int(value)
    expected_count = sum(
        len(_cases(item["capability"]["spelling"], item["capability"]["capability_id"]))
        for item in subjects
    )
    if len(results) != expected_count:
        raise FPDifferentialAuditError(
            f"Lean evaluator returned {len(results)}/{expected_count} cases"
        )
    return results, {
        "backend": "lean-kernel-evaluator",
        "command": ["lake", "env", "lean", "<temporary>/FPDifferentialAudit.lean"],
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "status": "passed",
    }


def _neon_operation(spelling: str) -> str:
    operations = {
        "vaddq_f32": "vaddq_f32(a, b)",
        "vsubq_f32": "vsubq_f32(a, b)",
        "vmulq_f32": "vmulq_f32(a, b)",
        "vdivq_f32": "vdivq_f32(a, b)",
    }
    if spelling in operations:
        return operations[spelling]
    raise FPDifferentialAuditError(f"not a binary Neon arithmetic spelling: {spelling}")


def _neon_probe_source(subjects: Sequence[Mapping[str, Any]]) -> str:
    neon = [item for item in subjects if item["capability"]["architecture"] == "neon"]
    calls: list[str] = []
    for subject in neon:
        spelling = subject["capability"]["spelling"]
        capability_id = subject["capability"]["capability_id"]
        for case in _cases(spelling, capability_id):
            values = ", ".join(f"UINT32_C(0x{value:08X})" for value in case.inputs)
            if spelling == "vabsq_f32":
                expression = f"run_abs({values})"
            elif spelling == "vbslq_f32":
                expression = f"run_bsl({values})"
            elif spelling == "vcaltq_f32":
                expression = f"run_calt({values})"
            elif spelling == "vmaxq_f32":
                expression = f"run_vmax({values})"
            elif spelling == "vminq_f32":
                expression = f"run_vmin({values})"
            elif spelling == "vsqrtq_f32":
                expression = f"run_sqrt({values})"
            elif spelling == "vcvtq_f32_s32":
                expression = f"run_i32_to_f32({values})"
            else:
                expression = f"run_{spelling.removesuffix('q_f32')}({values})"
            calls.append(
                f'  printf("FPDIFF|{case.case_id}|%08" PRIX32 "\\n", {expression});'
            )
    return f"""#if !defined(__aarch64__)
#error "native Neon FP differential probe requires AArch64"
#endif
#include <arm_neon.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

#define NOINLINE __attribute__((noinline))

static float32x4_t as_f32(uint32_t value) {{
  return vreinterpretq_f32_u32(vdupq_n_u32(value));
}}
static uint32_t bits0(float32x4_t value) {{
  return vgetq_lane_u32(vreinterpretq_u32_f32(value), 0);
}}
static NOINLINE uint32_t run_vadd(uint32_t x, uint32_t y) {{
  const float32x4_t a = as_f32(x), b = as_f32(y);
  return bits0({_neon_operation("vaddq_f32")});
}}
static NOINLINE uint32_t run_vsub(uint32_t x, uint32_t y) {{
  const float32x4_t a = as_f32(x), b = as_f32(y);
  return bits0({_neon_operation("vsubq_f32")});
}}
static NOINLINE uint32_t run_vmul(uint32_t x, uint32_t y) {{
  const float32x4_t a = as_f32(x), b = as_f32(y);
  return bits0({_neon_operation("vmulq_f32")});
}}
static NOINLINE uint32_t run_vdiv(uint32_t x, uint32_t y) {{
  const float32x4_t a = as_f32(x), b = as_f32(y);
  return bits0({_neon_operation("vdivq_f32")});
}}
static NOINLINE uint32_t run_abs(uint32_t x) {{
  return bits0(vabsq_f32(as_f32(x)));
}}
static NOINLINE uint32_t run_bsl(uint32_t mask, uint32_t x, uint32_t y) {{
  return bits0(vbslq_f32(vdupq_n_u32(mask), as_f32(x), as_f32(y)));
}}
static NOINLINE uint32_t run_calt(uint32_t x, uint32_t y) {{
  const uint32x4_t value = vcaltq_f32(as_f32(x), as_f32(y));
  return vgetq_lane_u32(value, 0);
}}
static NOINLINE uint32_t run_vmax(uint32_t x, uint32_t y) {{
  return bits0(vmaxq_f32(as_f32(x), as_f32(y)));
}}
static NOINLINE uint32_t run_vmin(uint32_t x, uint32_t y) {{
  return bits0(vminq_f32(as_f32(x), as_f32(y)));
}}
static NOINLINE uint32_t run_sqrt(uint32_t x) {{
  return bits0(vsqrtq_f32(as_f32(x)));
}}
static NOINLINE uint32_t run_i32_to_f32(uint32_t x) {{
  const int32x4_t value = vreinterpretq_s32_u32(vdupq_n_u32(x));
  return bits0(vcvtq_f32_s32(value));
}}

int main(void) {{
  uint64_t saved_fpcr;
  __asm__ volatile("mrs %0, fpcr" : "=r"(saved_fpcr));
  const uint64_t reviewed_fpcr = saved_fpcr &
      ~((UINT64_C(1) << 1) | (UINT64_C(3) << 22) |
        (UINT64_C(1) << 24) | (UINT64_C(1) << 25) |
        (UINT64_C(0x1F) << 8) | (UINT64_C(1) << 15));
  __asm__ volatile("msr fpcr, %0\\nisb" : : "r"(reviewed_fpcr) : "memory");
{chr(10).join(calls)}
  __asm__ volatile("msr fpcr, %0\\nisb" : : "r"(saved_fpcr) : "memory");
  return 0;
}}
"""


def _tool_version(command: str) -> str:
    completed = _run([command, "--version"], cwd=Path.cwd(), timeout=30)
    text = (completed.stdout or completed.stderr).splitlines()
    return text[0] if text else "version unavailable"


def run_native_neon(
    root: Path, subjects: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, int], dict[str, Any]]:
    machine = platform.machine().lower()
    clang = shutil.which("clang")
    source = _neon_probe_source(subjects)
    base = {
        "backend": "native-aarch64-neon",
        "host_machine": machine,
        "compiler": clang,
        "probe_source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
    }
    if machine not in {"arm64", "aarch64"}:
        return {}, {**base, "status": "blocked", "blocked_reason": "host-not-aarch64"}
    if clang is None:
        return {}, {**base, "status": "blocked", "blocked_reason": "clang-not-found"}
    with tempfile.TemporaryDirectory(prefix="saltyrn-fp-neon-") as directory:
        directory_path = Path(directory)
        source_path = directory_path / "probe.c"
        binary_path = directory_path / "probe"
        assembly_path = directory_path / "probe.s"
        source_path.write_text(source, encoding="utf-8")
        command = [
            clang,
            "-std=c11",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-ffp-contract=off",
            str(source_path),
            "-o",
            str(binary_path),
        ]
        compiled = _run(command, cwd=root)
        if compiled.returncode != 0:
            return {}, {
                **base,
                "status": "blocked",
                "blocked_reason": "native-probe-compile-failed",
                "compiler_stderr": compiled.stderr,
            }
        assembly = _run(command[:-2] + ["-S", "-o", str(assembly_path)], cwd=root)
        executed = _run([str(binary_path)], cwd=root)
        if executed.returncode != 0:
            raise FPDifferentialAuditError(
                f"native Neon probe failed:\n{executed.stdout}\n{executed.stderr}"
            )
        results: dict[str, int] = {}
        for line in executed.stdout.splitlines():
            if line.startswith("FPDIFF|"):
                _, case_id, value = line.split("|", 2)
                results[case_id] = int(value, 16)
        evidence = {
            **base,
            "status": "passed",
            "compiler_version": _tool_version(clang),
            "command": [
                "clang",
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-ffp-contract=off",
                "<temporary>/probe.c",
                "-o",
                "<temporary>/probe",
            ],
            "binary_sha256": _sha256(binary_path),
            "assembly_sha256": (
                _sha256(assembly_path) if assembly.returncode == 0 else None
            ),
            "stdout_sha256": hashlib.sha256(
                executed.stdout.encode("utf-8")
            ).hexdigest(),
        }
    return results, evidence


def _rvv_instruction(spelling: str) -> tuple[str, str, str]:
    """Return setup kind, exact RVV instruction, and result extraction kind."""

    table = {
        "__riscv_vfabs_v_f32m8": ("v", "vfsgnjx.vv v24, v8, v8", "vector"),
        "__riscv_vfadd_vf_f32m8": ("vf", "vfadd.vf v24, v8, ft0", "vector"),
        "__riscv_vfadd_vv_f32m8": ("vv", "vfadd.vv v24, v8, v16", "vector"),
        "__riscv_vfsub_vf_f32m8": ("vf", "vfsub.vf v24, v8, ft0", "vector"),
        "__riscv_vfsub_vv_f32m8": ("vv", "vfsub.vv v24, v8, v16", "vector"),
        "__riscv_vfmul_vf_f32m8": ("vf", "vfmul.vf v24, v8, ft0", "vector"),
        "__riscv_vfmul_vv_f32m8": ("vv", "vfmul.vv v24, v8, v16", "vector"),
        "__riscv_vfsgnj_vv_f32m8": ("vv", "vfsgnj.vv v24, v8, v16", "vector"),
        "__riscv_vmerge_vvm_f32m8": ("vvm", "vmerge.vvm v24, v8, v16, v0", "vector"),
        "__riscv_vmfgt_vf_f32m8_b4": ("vf", "vmfgt.vf v0, v8, ft0", "mask"),
        "__riscv_vmfne_vv_f32m8_b4": ("vv", "vmfne.vv v0, v8, v16", "mask"),
        "__riscv_vfmax_vv_f32m8": ("vv", "vfmax.vv v24, v8, v16", "vector"),
        "__riscv_vfmin_vv_f32m8": ("vv", "vfmin.vv v24, v8, v16", "vector"),
        "__riscv_vfdiv_vv_f32m8": ("vv", "vfdiv.vv v24, v8, v16", "vector"),
        "__riscv_vfsqrt_v_f32m8": ("v", "vfsqrt.v v24, v8", "vector"),
        "__riscv_vfcvt_f_x_v_f32m8": ("v", "vfcvt.f.x.v v24, v8", "vector"),
        "__riscv_vfcvt_x_f_v_i32m8": ("v", "vfcvt.x.f.v v24, v8", "vector"),
    }
    if spelling not in table:
        raise FPDifferentialAuditError(
            f"unsupported RVV FP oracle spelling: {spelling}"
        )
    return table[spelling]


def _rvv_probe_source(subjects: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        ".option norvc",
        ".section .text",
        ".globl _start",
        "_start:",
        "  li t0, 0x6600",  # mstatus.FS=Dirty and mstatus.VS=Dirty.
        "  csrs mstatus, t0",
        "  fsrmi zero, 0",  # RNE.
        "  li t0, 1",
        "  vsetvli t1, t0, e32, m8, ta, ma",
    ]
    for subject in subjects:
        capability = subject["capability"]
        if capability["architecture"] != "rvv":
            continue
        setup, instruction, result_kind = _rvv_instruction(capability["spelling"])
        for case in _cases(capability["spelling"], capability["capability_id"]):
            lines.extend(
                [
                    f"  # FPDIFF {case.case_id}",
                    f"  li t2, 0x{case.inputs[0]:08X}",
                    "  vmv.s.x v8, t2",
                ]
            )
            if setup == "vv":
                lines.extend(
                    [
                        f"  li t2, 0x{case.inputs[1]:08X}",
                        "  vmv.s.x v16, t2",
                    ]
                )
            elif setup == "vf":
                lines.extend(
                    [
                        f"  li t2, 0x{case.inputs[1]:08X}",
                        "  fmv.w.x ft0, t2",
                    ]
                )
            elif setup == "vvm":
                lines.extend(
                    [
                        f"  li t2, 0x{case.inputs[1]:08X}",
                        "  vmv.s.x v16, t2",
                        f"  li t2, 0x{case.inputs[2]:08X}",
                        "  vmv.v.x v0, t2",
                    ]
                )
            result = "vcpop.m a0, v0" if result_kind == "mask" else "vmv.x.s a0, v24"
            lines.extend([f"  {instruction}", f"  {result}"])
    lines.extend(["done:", "  j done", ""])
    return "\n".join(lines)


def run_spike_rvv(
    root: Path, subjects: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, int], dict[str, Any]]:
    spike = shutil.which("spike")
    linker = shutil.which("riscv64-elf-ld")
    clang_candidates = [
        Path("/opt/homebrew/opt/llvm/bin/clang"),
        Path(shutil.which("clang") or ""),
    ]
    cross_clang = next((str(path) for path in clang_candidates if path.is_file()), None)
    source = _rvv_probe_source(subjects)
    tools = {"cross_clang": cross_clang, "linker": linker, "spike": spike}
    base = {
        "backend": "spike-rvv-isa",
        "tools": tools,
        "probe_source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "isa": "rv64gcv_zvl128b",
        "fp_environment": "mstatus.FS=Dirty,mstatus.VS=Dirty,frm=RNE,vl=1,e32,m8,ta,ma",
    }
    missing = [name for name, path in tools.items() if path is None]
    if missing:
        return {}, {
            **base,
            "status": "blocked",
            "blocked_reason": "missing-rvv-toolchain:" + ",".join(missing),
        }
    with tempfile.TemporaryDirectory(prefix="saltyrn-fp-rvv-") as directory:
        directory_path = Path(directory)
        source_path = directory_path / "probe.S"
        object_path = directory_path / "probe.o"
        elf_path = directory_path / "probe.elf"
        source_path.write_text(source, encoding="utf-8")
        compile_command = [
            cross_clang,
            "--target=riscv64-unknown-elf",
            "-march=rv64gcv_zvl128b",
            "-menable-experimental-extensions",
            "-c",
            str(source_path),
            "-o",
            str(object_path),
        ]
        compiled = _run(compile_command, cwd=root)
        if compiled.returncode != 0:
            return {}, {
                **base,
                "status": "blocked",
                "blocked_reason": "rvv-cross-assembly-failed",
                "compiler_stderr": compiled.stderr,
            }
        link_command = [
            linker,
            "-Ttext=0x80001000",
            "-e",
            "_start",
            str(object_path),
            "-o",
            str(elf_path),
        ]
        linked = _run(link_command, cwd=root)
        if linked.returncode != 0:
            return {}, {
                **base,
                "status": "blocked",
                "blocked_reason": "rvv-bare-metal-link-failed",
                "linker_stderr": linked.stderr,
            }
        spike_command = [
            spike,
            "--isa=rv64gcv_zvl128b",
            "--pc=0x80001000",
            "--instructions=1000",
            "-l",
            "--log-commits",
            str(elf_path),
        ]
        executed = _run(spike_command, cwd=root, timeout=180)
        log = executed.stdout + executed.stderr
        if executed.returncode != 0:
            return {}, {
                **base,
                "status": "blocked",
                "blocked_reason": "spike-execution-failed",
                "spike_log_tail": log[-4000:],
            }
        values = [
            int(match, 16) & 0xFFFFFFFF
            for match in re.findall(r"x10\s+0x([0-9a-fA-F]{16})", log)
        ]
        cases = [
            case
            for subject in subjects
            if subject["capability"]["architecture"] == "rvv"
            for case in _cases(
                subject["capability"]["spelling"],
                subject["capability"]["capability_id"],
            )
        ]
        if len(values) != len(cases):
            raise FPDifferentialAuditError(
                f"Spike returned {len(values)}/{len(cases)} RVV case values"
            )
        results = {
            case.case_id: value for case, value in zip(cases, values, strict=True)
        }
        evidence = {
            **base,
            "status": "passed",
            "compiler_version": _tool_version(cross_clang),
            "linker_version": _tool_version(linker),
            "spike_version": _tool_version(spike),
            "compile_command": [
                "clang",
                "--target=riscv64-unknown-elf",
                "-march=rv64gcv_zvl128b",
                "-menable-experimental-extensions",
                "-c",
                "<temporary>/probe.S",
            ],
            "link_command": [
                "riscv64-elf-ld",
                "-Ttext=0x80001000",
                "-e",
                "_start",
                "<temporary>/probe.o",
            ],
            "run_command": [
                "spike",
                "--isa=rv64gcv_zvl128b",
                "--pc=0x80001000",
                "--instructions=1000",
                "-l",
                "--log-commits",
                "<temporary>/probe.elf",
            ],
            "elf_sha256": _sha256(elf_path),
            "commit_log_sha256": hashlib.sha256(log.encode("utf-8")).hexdigest(),
        }
    return results, evidence


def _definition_evidence(root: Path, symbol: str) -> dict[str, Any]:
    architecture = "Neon" if ".Neon." in symbol else "RVV"
    path = root / f"src/verification_bw/lean/SALT/Intrinsics/{architecture}.lean"
    name = symbol.rsplit(".", 1)[1]
    pattern = re.compile(rf"^def\s+{re.escape(name)}\b")
    lines = path.read_text(encoding="utf-8").splitlines()
    line_number = next(
        (index for index, line in enumerate(lines, 1) if pattern.match(line)), None
    )
    if line_number is None:
        raise FPDifferentialAuditError(f"Lean definition is absent: {symbol}")
    fp32 = root / "src/verification_bw/lean/SALT/Intrinsics/FP32.lean"
    return {
        "symbol": symbol,
        "definition_path": path.relative_to(root).as_posix(),
        "definition_line": line_number,
        "definition_file_sha256": _sha256(path),
        "fp32_support_path": fp32.relative_to(root).as_posix(),
        "fp32_support_sha256": _sha256(fp32),
    }


def _c_calls(
    root: Path, architecture: str, spelling: str, programs: Sequence[str]
) -> list[dict[str, Any]]:
    side = "source" if architecture == "neon" else "target"
    result: list[dict[str, Any]] = []
    for program in programs:
        path = root / f"kernels/{side}/{program}.c"
        if not path.is_file():
            raise FPDifferentialAuditError(f"audited kernel source is absent: {path}")
        file_sha256 = _sha256(path)
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if re.search(rf"\b{re.escape(spelling)}\s*\(", line):
                result.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "line": line_number,
                        "text": line.strip(),
                        "file_sha256": file_sha256,
                    }
                )
    if not result:
        raise FPDifferentialAuditError(f"no real C call found for {spelling}")
    return result


def _authority_evidence(root: Path, evidence: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(evidence)
    path = root / str(evidence["path"])
    copied["local_file_available"] = path.is_file()
    copied["local_file_matches_recorded_sha256"] = (
        _sha256(path) == evidence["file_sha256"] if path.is_file() else False
    )
    if not path.is_file():
        copied["local_blocked_reason"] = "pinned-authority-file-not-present-in-checkout"
    return copied


def build_audit(root: Path) -> dict[str, Any]:
    corpus = root / "verification/elementwise-compiler"
    subjects = load_exact_subjects(corpus)
    lean_results, lean_backend = evaluate_lean(root, subjects)
    neon_results, neon_backend = run_native_neon(root, subjects)
    rvv_results, rvv_backend = run_spike_rvv(root, subjects)
    matrix_users: dict[str, list[str]] = {}
    for subject in subjects:
        capability = subject["capability"]
        matrix_users.setdefault(_matrix_id(capability["spelling"]), []).append(
            capability["capability_id"]
        )
    rows: list[dict[str, Any]] = []
    for subject in subjects:
        capability = subject["capability"]
        audit = subject["audit"]
        architecture = capability["architecture"]
        backend = neon_backend if architecture == "neon" else rvv_backend
        cases: list[dict[str, Any]] = []
        for case in _cases(capability["spelling"], capability["capability_id"]):
            expected = lean_results[case.case_id]
            actual = (
                neon_results.get(case.case_id)
                if architecture == "neon"
                else rvv_results.get(case.case_id)
            )
            if backend["status"] == "blocked":
                verdict = "blocked"
            else:
                verdict = "passed" if actual == expected else "mismatch"
            cases.append(
                {
                    "case_id": case.case_id,
                    "inputs_bits": [f"0x{value:08X}" for value in case.inputs],
                    "expected_bits": f"0x{expected:08X}",
                    "actual_bits": None if actual is None else f"0x{actual:08X}",
                    "verdict": verdict,
                }
            )
        status = (
            "blocked"
            if backend["status"] == "blocked"
            else (
                "mismatch"
                if any(case["verdict"] == "mismatch" for case in cases)
                else "passed"
            )
        )
        row = {
            "capability_id": capability["capability_id"],
            "review_family": subject["review_family"],
            "architecture": architecture,
            "spelling": capability["spelling"],
            "function_type": capability["function_type"],
            "architecture_conditions": audit["architecture_conditions"],
            "descriptor": subject["descriptor"],
            "c_calls": _c_calls(
                root, architecture, capability["spelling"], audit["programs"]
            ),
            "official_pinned_source": _authority_evidence(
                root, audit["primary_evidence"]
            ),
            "official_selector": {
                "api": audit["primary_evidence"]["selector"],
                "isa": audit["primary_evidence"].get(
                    "isa_selector", audit["primary_evidence"].get("instruction")
                ),
            },
            "lean": _definition_evidence(root, capability["semantic_symbol"]),
            "oracle_backend": backend,
            "evidence_level": EVIDENCE_LEVEL,
            "coverage_scope": COVERAGE_SCOPE,
            "case_matrix": {
                "matrix_id": _matrix_id(capability["spelling"]),
                "reused": len(matrix_users[_matrix_id(capability["spelling"])]) > 1,
                "reused_by_capability_ids": sorted(
                    matrix_users[_matrix_id(capability["spelling"])]
                ),
                "reuse_scope": (
                    "input-tuples-only;each-exact-capability-has-independent-case-ids,"
                    "Lean-evaluation,architecture-execution,and-evidence-digest"
                ),
            },
            "cases": cases,
            "status": status,
        }
        row["evidence_sha256"] = canonical_sha256(row)
        rows.append(row)
    counts = {
        "subjects": len(rows),
        "passed_subjects": sum(row["status"] == "passed" for row in rows),
        "blocked_subjects": sum(row["status"] == "blocked" for row in rows),
        "mismatch_subjects": sum(row["status"] == "mismatch" for row in rows),
        "test_vectors": sum(len(row["cases"]) for row in rows),
        "executed_vectors": sum(
            case["actual_bits"] is not None for row in rows for case in row["cases"]
        ),
        "blocked_vectors": sum(
            case["verdict"] == "blocked" for row in rows for case in row["cases"]
        ),
    }
    record = {
        "artifact_kind": ARTIFACT_KIND,
        "schema_version": SCHEMA_VERSION,
        "evidence_level": EVIDENCE_LEVEL,
        "coverage_scope": COVERAGE_SCOPE,
        "verdict_definition": (
            "passed means every listed test vector matched its architecture oracle; "
            "it is sampled differential evidence, not a proof of the full intrinsic"
        ),
        "registry_path": "verification/elementwise-compiler/IntrinsicRegistry.json",
        "registry_file_sha256": _sha256(corpus / "IntrinsicRegistry.json"),
        "registry_sha256": _load_json(corpus / "IntrinsicRegistry.json")[
            "registry_sha256"
        ],
        "intrinsic_audit_path": "verification/elementwise-compiler/IntrinsicAudit.json",
        "intrinsic_audit_file_sha256": _sha256(corpus / "IntrinsicAudit.json"),
        "intrinsic_audit_sha256": _load_json(corpus / "IntrinsicAudit.json")[
            "audit_sha256"
        ],
        "review_plan_path": "verification/elementwise-compiler/IntrinsicReviewPlan.json",
        "review_plan_file_sha256": _sha256(corpus / "IntrinsicReviewPlan.json"),
        "review_plan_sha256": _load_json(corpus / "IntrinsicReviewPlan.json")[
            "plan_sha256"
        ],
        "lean_backend": lean_backend,
        "toolchain_inventory": {
            "native_neon": neon_backend,
            "rvv": rvv_backend,
        },
        "ledger_projection_path": (
            "verification/elementwise-compiler/FPDifferentialAuditLedger.csv"
        ),
        "ledger_join_key": "capability_id",
        "counts": counts,
        "subjects": rows,
    }
    validate_audit(record)
    record["audit_sha256"] = canonical_sha256(record)
    return record


def render_ledger_projection(record: Mapping[str, Any]) -> str:
    """Project stable join fields for the exact master semantic ledger."""

    fields = (
        "capability_id",
        "evidence_level",
        "coverage_scope",
        "differential_test_status",
        "oracle_backend",
        "executed_vectors",
        "total_vectors",
        "mismatch_found",
        "evidence_path",
        "evidence_sha256",
        "full_intrinsic_proof",
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for subject in sorted(record["subjects"], key=lambda row: row["capability_id"]):
        executed = sum(case["actual_bits"] is not None for case in subject["cases"])
        writer.writerow(
            {
                "capability_id": subject["capability_id"],
                "evidence_level": subject["evidence_level"],
                "coverage_scope": subject["coverage_scope"],
                "differential_test_status": f"{subject['status']}-sampled",
                "oracle_backend": subject["oracle_backend"]["backend"],
                "executed_vectors": executed,
                "total_vectors": len(subject["cases"]),
                "mismatch_found": "yes" if subject["status"] == "mismatch" else "no",
                "evidence_path": "verification/elementwise-compiler/FPDifferentialAudit.json",
                "evidence_sha256": subject["evidence_sha256"],
                "full_intrinsic_proof": "no",
            }
        )
    return stream.getvalue()


def validate_audit(record: Mapping[str, Any]) -> None:
    if (
        record.get("artifact_kind") != ARTIFACT_KIND
        or record.get("schema_version") != SCHEMA_VERSION
    ):
        raise FPDifferentialAuditError("invalid differential-audit kind/schema")
    if record.get("evidence_level") != EVIDENCE_LEVEL:
        raise FPDifferentialAuditError("differential audit must be labeled L3-sampled")
    if record.get("coverage_scope") != COVERAGE_SCOPE:
        raise FPDifferentialAuditError("differential audit coverage scope changed")
    subjects = record.get("subjects")
    if not isinstance(subjects, list) or len(subjects) != EXPECTED_EXACT_SUBJECTS:
        raise FPDifferentialAuditError(
            f"differential audit must contain {EXPECTED_EXACT_SUBJECTS} subjects"
        )
    capability_ids: set[str] = set()
    for row in subjects:
        if not isinstance(row, dict):
            raise FPDifferentialAuditError("differential subject must be an object")
        capability_id = row.get("capability_id")
        if not isinstance(capability_id, str) or capability_id in capability_ids:
            raise FPDifferentialAuditError("differential capability IDs must be unique")
        capability_ids.add(capability_id)
        digest = row.get("evidence_sha256")
        unsigned = dict(row)
        unsigned.pop("evidence_sha256", None)
        if digest != canonical_sha256(unsigned):
            raise FPDifferentialAuditError(
                f"subject evidence digest mismatch: {capability_id}"
            )
        if row.get("status") not in {"passed", "blocked", "mismatch"}:
            raise FPDifferentialAuditError(f"invalid subject status: {capability_id}")
        if (
            row.get("evidence_level") != EVIDENCE_LEVEL
            or row.get("coverage_scope") != COVERAGE_SCOPE
        ):
            raise FPDifferentialAuditError(
                f"subject lacks sampled-evidence scope: {capability_id}"
            )
        descriptor = row.get("descriptor")
        if (
            not isinstance(descriptor, dict)
            or descriptor.get("descriptor_sha256") is None
        ):
            raise FPDifferentialAuditError(
                f"subject lacks descriptor trace: {capability_id}"
            )
        matrix = row.get("case_matrix")
        if not isinstance(matrix, dict) or capability_id not in matrix.get(
            "reused_by_capability_ids", []
        ):
            raise FPDifferentialAuditError(
                f"subject lacks exact matrix binding: {capability_id}"
            )
        cases = row.get("cases")
        if not isinstance(cases, list) or not cases:
            raise FPDifferentialAuditError(f"subject lacks cases: {capability_id}")
        for case in cases:
            if case.get("verdict") not in {"passed", "blocked", "mismatch"}:
                raise FPDifferentialAuditError(f"invalid case verdict: {capability_id}")
            expected = case.get("expected_bits")
            actual = case.get("actual_bits")
            if (
                not isinstance(expected, str)
                or re.fullmatch(r"0x[0-9A-F]{8}", expected) is None
            ):
                raise FPDifferentialAuditError(
                    f"invalid expected bits: {capability_id}"
                )
            if actual is not None and (
                not isinstance(actual, str)
                or re.fullmatch(r"0x[0-9A-F]{8}", actual) is None
            ):
                raise FPDifferentialAuditError(f"invalid actual bits: {capability_id}")


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("verification/elementwise-compiler/FPDifferentialAudit.json"),
    )
    parser.add_argument(
        "--ledger-output",
        type=Path,
        default=Path("verification/elementwise-compiler/FPDifferentialAuditLedger.csv"),
        help="stable capability_id-keyed projection for the canonical master ledger",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    ledger_output = (
        args.ledger_output
        if args.ledger_output.is_absolute()
        else root / args.ledger_output
    )
    record = build_audit(root)
    rendered = canonical_json(record, pretty=True)
    ledger_rendered = render_ledger_projection(record)
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise FPDifferentialAuditError(f"stale differential audit: {output}")
        if (
            not ledger_output.is_file()
            or ledger_output.read_text(encoding="utf-8") != ledger_rendered
        ):
            raise FPDifferentialAuditError(
                f"stale differential ledger projection: {ledger_output}"
            )
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        ledger_output.parent.mkdir(parents=True, exist_ok=True)
        ledger_output.write_text(ledger_rendered, encoding="utf-8")
    print(json.dumps(record["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
