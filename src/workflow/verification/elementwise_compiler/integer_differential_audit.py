"""Sampled architecture-oracle audit for P1 integer intrinsic semantics.

The exact subject set is the intersection of the current canonical registry and
the I2/I3 rows in the semantic-audit ledger.  Each subject is joined by exact
``capability_id`` to its real kernel calls, pinned authority metadata and Lean
symbol.  Lean values are compared with native AArch64 Neon intrinsics or real RVV
C intrinsics compiled by LLVM and executed by Spike.

This is L3 sampled value evidence, not an exhaustive test or a correspondence
proof.  Neon ``FPSR.QC`` and RVV ``vxsat`` are explicitly outside its claim.
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

from .schema import canonical_json, canonical_sha256


SCHEMA_VERSION = 1
ARTIFACT_KIND = "integer-intrinsic-differential-audit"
EVIDENCE_LEVEL = "L3-sampled"
P1_FAMILIES = frozenset(
    {
        "I2-integer-saturating-narrow-shift",
        "I3-integer-mode-sensitive-rounding",
    }
)
REPAIRED_REGRESSION_FAMILY = "REPAIRED-vssra-shift-mask-regression"
REPAIRED_REGRESSION_CAPABILITY_IDS = frozenset(
    {"intrinsic:rvv:__riscv_vssra_vx_i32m8:19e343bce1b4b97b"}
)
COVERAGE_SCOPE = (
    "listed-boundary-vectors-only;not-exhaustive;pure-active-lane-value;"
    "FPSR.QC-and-vxsat-excluded;inactive-lanes-tail-mask-memory-and-full-ISA-"
    "refinement-excluded"
)
STATE_EXCLUSIONS = (
    "Neon FPSR.QC is neither observed nor compared",
    "RVV vxsat is neither observed nor compared",
    "only the listed active lane value is compared",
)


class IntegerDifferentialAuditError(RuntimeError):
    """The exact inventory, evaluator, probe or evidence is malformed."""


@dataclass(frozen=True, slots=True)
class IntegerCase:
    case_id: str
    inputs: tuple[int, ...]
    input_widths: tuple[int, ...]
    output_width: int
    shift: int | None = None
    mode: int | None = None
    observed_lane: int = 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(
    command: Sequence[str], *, cwd: Path, timeout: int = 180
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
        raise IntegerDifferentialAuditError(f"expected JSON object: {path}")
    return value


def _tool_version(command: str) -> str:
    completed = _run([command, "--version"], cwd=Path.cwd(), timeout=30)
    lines = (completed.stdout or completed.stderr).splitlines()
    return lines[0] if lines else "version unavailable"


def _constraints_by_index(audit: Mapping[str, Any]) -> dict[int, tuple[int, ...]]:
    constraints: dict[int, tuple[int, ...]] = {}
    for item in audit["immediate_constraints"]:
        index = item["argument_index"]
        values = tuple(item["allowed_values"])
        if not values or index in constraints:
            raise IntegerDifferentialAuditError("malformed or duplicate immediate constraint")
        constraints[index] = values
    return constraints


def load_exact_subjects(
    root: Path, corpus: Path | None = None
) -> tuple[dict[str, Any], ...]:
    """Dynamically join every current I2/I3 semantic capability by exact ID."""

    corpus = corpus or root / "verification/elementwise-compiler"
    registry = _load_json(corpus / "IntrinsicRegistry.json")
    audit = _load_json(corpus / "IntrinsicAudit.json")
    review_plan = _load_json(corpus / "IntrinsicReviewPlan.json")
    family_by_id = {
        subject["capability_id"]: family["family"]
        for family in review_plan["families"]
        if family["family"] in P1_FAMILIES
        for subject in family["subjects"]
    }
    audit_by_id = {row["capability_id"]: row for row in audit["variants"]}
    subjects: list[dict[str, Any]] = []
    for variant in registry["variants"]:
        capability = variant["capability"]
        capability_id = capability["capability_id"]
        semantic_family = family_by_id.get(capability_id)
        repaired_regression = capability_id in REPAIRED_REGRESSION_CAPABILITY_IDS
        if semantic_family is None and not repaired_regression:
            continue
        if capability["role"] != "semantic" or capability["semantic_symbol"] is None:
            raise IntegerDifferentialAuditError(
                f"P1 subject is not an exact semantic capability: {capability_id}"
            )
        if capability_id not in audit_by_id:
            raise IntegerDifferentialAuditError(
                f"P1 capability lacks IntrinsicAudit row: {capability_id}"
            )
        audit_row = audit_by_id[capability_id]
        for field in ("architecture", "spelling", "function_type", "semantic_symbol"):
            if audit_row[field] != capability[field]:
                raise IntegerDifferentialAuditError(
                    f"registry/audit mismatch for {capability_id}: {field}"
                )
        subjects.append(
            {
                "capability": capability,
                "audit": audit_row,
                "semantic_family": (
                    semantic_family
                    if semantic_family is not None
                    else REPAIRED_REGRESSION_FAMILY
                ),
                "subject_scope": (
                    "current-P1-exact"
                    if semantic_family is not None
                    else "explicit-repaired-regression-unused"
                ),
            }
        )
    subjects.sort(key=lambda item: item["capability"]["capability_id"])
    if not subjects:
        raise IntegerDifferentialAuditError("current registry has no I2/I3 P1 subjects")
    subject_ids = {item["capability"]["capability_id"] for item in subjects}
    if len(subject_ids) != len(subjects):
        raise IntegerDifferentialAuditError("duplicate exact P1 capability ID")
    missing_regressions = REPAIRED_REGRESSION_CAPABILITY_IDS - subject_ids
    if missing_regressions:
        raise IntegerDifferentialAuditError(
            f"explicit repaired-regression capability disappeared: {sorted(missing_regressions)}"
        )
    return tuple(subjects)


def _case_prefix(capability: Mapping[str, Any]) -> str:
    spelling = re.sub(r"[^a-z0-9]+", "-", capability["spelling"].lower()).strip("-")
    return f"{spelling}-{capability['capability_id'].rsplit(':', 1)[1]}"


def _signed_bits(value: int, width: int) -> int:
    return value & ((1 << width) - 1)


def _make_cases(subject: Mapping[str, Any]) -> tuple[IntegerCase, ...]:
    capability = subject["capability"]
    audit = subject["audit"]
    spelling = capability["spelling"]
    prefix = _case_prefix(capability)

    def one(
        name: str,
        values: Sequence[int],
        widths: Sequence[int],
        output_width: int,
        *,
        shift: int | None = None,
        mode: int | None = None,
        observed_lane: int = 0,
    ) -> IntegerCase:
        if len(values) != len(widths):
            raise AssertionError("integer case width mismatch")
        return IntegerCase(
            case_id=f"{prefix}-{name}",
            inputs=tuple(value & ((1 << width) - 1) for value, width in zip(values, widths)),
            input_widths=tuple(widths),
            output_width=output_width,
            shift=shift,
            mode=mode,
            observed_lane=observed_lane,
        )

    if spelling == "vqmovn_high_s32":
        values = (-2147483648, -32769, -32768, -32767, 32767, 32768, 2147483647)
        return tuple(
            one(str(value), (value,), (32,), 16, observed_lane=4) for value in values
        )
    if spelling == "vqmovn_s16":
        values = (-32768, -129, -128, -127, 0, 127, 128, 32767)
        return tuple(one(str(value), (value,), (16,), 8) for value in values)
    if spelling == "vqmovn_s32":
        values = (-2147483648, -32769, -32768, -32767, 0, 32767, 32768, 2147483647)
        return tuple(one(str(value), (value,), (32,), 16) for value in values)
    if spelling == "vqmovun_s16":
        values = (-32768, -1, 0, 1, 255, 256, 32767)
        return tuple(one(str(value), (value,), (16,), 8) for value in values)
    if spelling == "vqrdmulhq_s16":
        pairs = (
            (0, 32767),
            (1, 16384),
            (-1, 16384),
            (16384, 16384),
            (-16384, 16384),
            (32767, 32767),
            (-32768, 32767),
            (-32768, -32768),
        )
        return tuple(
            one(f"{left}-{right}", (left, right), (16, 16), 16)
            for left, right in pairs
        )
    if spelling == "vqsubq_s32":
        pairs = (
            (0, 0),
            (1, -1),
            (-1, 1),
            (2147483647, -1),
            (-2147483648, 1),
            (2147483647, -2147483648),
            (-2147483648, 2147483647),
        )
        return tuple(
            one(f"{left}-{right}", (left, right), (32, 32), 32)
            for left, right in pairs
        )
    if spelling == "vrshlq_s32":
        pairs = (
            (1, -64),
            (-1, -65),
            (-2147483648, -32),
            (2147483647, -31),
            (3, -1),
            (-3, -1),
            (1, 0),
            (1, 1),
            (1, 31),
            (1, 32),
            (1, 64),
            (1, 127),
        )
        return tuple(
            one(f"{value}-{count}", (value, count), (32, 32), 32)
            for value, count in pairs
        )
    if spelling == "vshlq_n_s16":
        shifts = _constraints_by_index(audit).get(1)
        if shifts != (7,):
            raise IntegerDifferentialAuditError("vshlq_n_s16 exact shift changed")
        values = (-32768, -1, 0, 1, 255, 32767)
        return tuple(one(str(value), (value,), (16,), 16, shift=7) for value in values)
    if spelling == "vshrn_n_u32":
        shifts = _constraints_by_index(audit).get(1)
        if shifts is None:
            raise IntegerDifferentialAuditError("vshrn_n_u32 lacks exact shifts")
        values = (0, 1, 0x1FFF, 0x2000, 0xFFFF, 0x10000, 0xFFFFFFFF)
        return tuple(
            one(f"shift-{shift}-{value:x}", (value,), (32,), 16, shift=shift)
            for shift in shifts
            for value in values
        )

    constraints = _constraints_by_index(audit)
    if spelling == "__riscv_vnclip_wx_i16m4":
        shifts = constraints.get(1)
        modes = constraints.get(2)
        if shifts is None or len(shifts) != 1 or modes is None or len(modes) != 1:
            raise IntegerDifferentialAuditError("vnclip i16 exact operands changed")
        shift, mode = shifts[0], modes[0]
        if shift == 0:
            values = (-2147483648, -32769, -32768, -32767, 0, 32767, 32768, 2147483647)
        else:
            half = 1 << (shift - 1)
            values = tuple(dict.fromkeys((
                -2147483648,
                (-32768 << shift) - half,
                -32768 << shift,
                -half,
                -1,
                0,
                half,
                (32767 << shift),
                (32767 << shift) + half,
                2147483647,
            )))
        return tuple(
            one(f"{value}", (value,), (32,), 16, shift=shift, mode=mode)
            for value in values
        )
    if spelling == "__riscv_vnclip_wx_i8m2":
        shift = constraints[1][0]
        mode = constraints[2][0]
        values = (-32768, -129, -128, -127, -1, 0, 127, 128, 32767)
        return tuple(
            one(str(value), (value,), (16,), 8, shift=shift, mode=mode)
            for value in values
        )
    if spelling == "__riscv_vnclipu_wx_u8m2":
        shift = constraints[1][0]
        mode = constraints[2][0]
        values = (0, 1, 127, 255, 256, 32767, 65535)
        return tuple(
            one(str(value), (value,), (16,), 8, shift=shift, mode=mode)
            for value in values
        )
    if spelling == "__riscv_vnsrl_wx_u16m4":
        values = (
            (0xFFFFFFFF, 0),
            (0x12345678, 15),
            (0x12345678, 16),
            (0xFFFFFFFF, 31),
            (0x12345678, 32),
            (0x12345678, 33),
            (0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF),
        )
        return tuple(
            one(f"{value:x}-shift-{shift}", (value,), (32,), 16, shift=shift)
            for value, shift in values
        )
    if spelling == "__riscv_vsadd_vx_i16m4":
        pairs = (
            (0, 0),
            (1, -1),
            (-1, 1),
            (32767, 1),
            (-32768, -1),
            (32767, 32767),
            (-32768, -32768),
        )
        return tuple(
            one(f"{left}-{right}", (left, right), (16, 16), 16)
            for left, right in pairs
        )
    if spelling == "__riscv_vsll_vx_i16m4":
        shift = constraints[1][0]
        values = (-32768, -1, 0, 1, 255, 32767)
        return tuple(
            one(str(value), (value,), (16,), 16, shift=shift) for value in values
        )
    if spelling == "__riscv_vsll_vx_i32m8":
        values = (
            (1, 0),
            (1, 31),
            (1, 32),
            (3, 33),
            (-1, 33),
            (0x40000000, 0xFFFFFFFFFFFFFFFF),
        )
        return tuple(
            one(f"{value}-shift-{shift}", (value,), (32,), 32, shift=shift)
            for value, shift in values
        )
    if spelling == "__riscv_vssra_vx_i32m8":
        mode = constraints[2][0]
        boundary_values = (0, 1, -1, -2147483648, 2147483647)
        boundary_shifts = (0, 1, 31, 32, 33, 63, 64, 0xFFFFFFFFFFFFFFFF)
        values = tuple(
            (value, shift)
            for value in boundary_values
            for shift in boundary_shifts
        ) + ((2, 1), (3, 1), (-3, 1))
        return tuple(
            one(
                f"{value}-shift-{shift}",
                (value,),
                (32,),
                32,
                shift=shift,
                mode=mode,
            )
            for value, shift in values
        )
    raise IntegerDifferentialAuditError(f"unsupported P1 spelling: {spelling}")


def _bv(value: int, width: int) -> str:
    digits = (width + 3) // 4
    return f"(0x{value:0{digits}X} : BitVec {width})"


def _lean_expression(subject: Mapping[str, Any], case: IntegerCase) -> str:
    capability = subject["capability"]
    symbol = capability["semantic_symbol"]
    spelling = capability["spelling"]
    values = [_bv(value, width) for value, width in zip(case.inputs, case.input_widths)]
    if spelling == "vqmovn_high_s32":
        invocation = f"{symbol} [0, 0, 0, 0] [{values[0]}]"
    elif spelling in {"vqrdmulhq_s16", "vqsubq_s32", "vrshlq_s32"}:
        invocation = f"{symbol} [{values[0]}] [{values[1]}]"
    elif spelling in {"vshlq_n_s16", "vshrn_n_u32"}:
        invocation = f"{symbol} [{values[0]}] {case.shift}"
    elif spelling in {
        "vqmovn_s16",
        "vqmovn_s32",
        "vqmovun_s16",
    }:
        invocation = f"{symbol} [{values[0]}]"
    elif spelling.startswith("__riscv_vnclip"):
        invocation = f"{symbol} [{values[0]}] {case.shift} {case.mode}"
    elif spelling == "__riscv_vsadd_vx_i16m4":
        invocation = f"{symbol} [{values[0]}] {values[1]}"
    elif spelling.startswith("__riscv_vsll") or spelling == "__riscv_vnsrl_wx_u16m4":
        invocation = f"{symbol} [{values[0]}] {case.shift}"
    elif spelling == "__riscv_vssra_vx_i32m8":
        if symbol.endswith(".vssra_vx_rnu"):
            invocation = f"{symbol} [{values[0]}] {case.shift}"
        else:
            invocation = f"{symbol} [{values[0]}] {case.shift} {case.mode}"
    else:
        raise IntegerDifferentialAuditError(f"no Lean invocation for {spelling}")
    zero = _bv(0, case.output_width)
    return f"(({invocation}).getD {case.observed_lane} {zero}).toNat"


def evaluate_lean(
    root: Path, subjects: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, int], dict[str, Any]]:
    lean_root = root / "src/verification_bw/lean"
    lake = shutil.which("lake")
    if lake is None:
        raise IntegerDifferentialAuditError("Lean evaluator requires lake")
    lines = ["import SALT.Intrinsics.Neon", "import SALT.Intrinsics.RVV", ""]
    for subject in subjects:
        for case in _make_cases(subject):
            lines.append(
                f'#eval IO.println s!"INTDIFF|{case.case_id}|{{{_lean_expression(subject, case)}}}"'
            )
    source = "\n".join(lines) + "\n"
    with tempfile.TemporaryDirectory(prefix="saltyrn-int-lean-") as directory:
        path = Path(directory) / "IntegerDifferentialAudit.lean"
        path.write_text(source, encoding="utf-8")
        completed = _run([lake, "env", "lean", str(path)], cwd=lean_root, timeout=240)
    if completed.returncode != 0:
        raise IntegerDifferentialAuditError(
            f"Lean evaluator failed:\n{completed.stdout}\n{completed.stderr}"
        )
    results: dict[str, int] = {}
    for line in completed.stdout.splitlines():
        if line.startswith("INTDIFF|"):
            _, case_id, value = line.split("|", 2)
            results[case_id] = int(value)
    expected = sum(len(_make_cases(subject)) for subject in subjects)
    if len(results) != expected:
        raise IntegerDifferentialAuditError(
            f"Lean evaluator returned {len(results)}/{expected} values"
        )
    return results, {
        "backend": "lean-kernel-evaluator",
        "command": ["lake", "env", "lean", "<temporary>/IntegerDifferentialAudit.lean"],
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "status": "passed",
    }


def _neon_wrapper(index: int, spelling: str, shift: int | None) -> str:
    name = f"run_{index}" if shift is None else f"run_{index}_shift_{shift}"
    if spelling == "vqmovn_high_s32":
        body = (
            "int16x8_t r = vqmovn_high_s32(vdup_n_s16(0), "
            "vdupq_n_s32((int32_t)(uint32_t)a));\n"
            "  return (uint16_t)vgetq_lane_s16(r, 4);"
        )
    elif spelling == "vqmovn_s16":
        body = (
            "int8x8_t r = vqmovn_s16(vdupq_n_s16((int16_t)(uint16_t)a));\n"
            "  return (uint8_t)vget_lane_s8(r, 0);"
        )
    elif spelling == "vqmovn_s32":
        body = (
            "int16x4_t r = vqmovn_s32(vdupq_n_s32((int32_t)(uint32_t)a));\n"
            "  return (uint16_t)vget_lane_s16(r, 0);"
        )
    elif spelling == "vqmovun_s16":
        body = (
            "uint8x8_t r = vqmovun_s16(vdupq_n_s16((int16_t)(uint16_t)a));\n"
            "  return vget_lane_u8(r, 0);"
        )
    elif spelling == "vqrdmulhq_s16":
        body = (
            "int16x8_t r = vqrdmulhq_s16(vdupq_n_s16((int16_t)(uint16_t)a), "
            "vdupq_n_s16((int16_t)(uint16_t)b));\n"
            "  return (uint16_t)vgetq_lane_s16(r, 0);"
        )
    elif spelling == "vqsubq_s32":
        body = (
            "int32x4_t r = vqsubq_s32(vdupq_n_s32((int32_t)(uint32_t)a), "
            "vdupq_n_s32((int32_t)(uint32_t)b));\n"
            "  return (uint32_t)vgetq_lane_s32(r, 0);"
        )
    elif spelling == "vrshlq_s32":
        body = (
            "int32x4_t r = vrshlq_s32(vdupq_n_s32((int32_t)(uint32_t)a), "
            "vdupq_n_s32((int32_t)(uint32_t)b));\n"
            "  return (uint32_t)vgetq_lane_s32(r, 0);"
        )
    elif spelling == "vshlq_n_s16":
        body = (
            f"int16x8_t r = vshlq_n_s16(vdupq_n_s16((int16_t)(uint16_t)a), {shift});\n"
            "  return (uint16_t)vgetq_lane_s16(r, 0);"
        )
    elif spelling == "vshrn_n_u32":
        body = (
            f"uint16x4_t r = vshrn_n_u32(vdupq_n_u32((uint32_t)a), {shift});\n"
            "  return vget_lane_u16(r, 0);"
        )
    else:
        raise IntegerDifferentialAuditError(f"unsupported Neon wrapper: {spelling}")
    return f"static NOINLINE uint64_t {name}(uint64_t a, uint64_t b) {{\n  (void)b;\n  {body}\n}}\n"


def _neon_probe_source(subjects: Sequence[Mapping[str, Any]]) -> str:
    neon = [item for item in subjects if item["capability"]["architecture"] == "neon"]
    wrappers: list[str] = []
    calls: list[str] = []
    seen_wrappers: set[tuple[int, int | None]] = set()
    for index, subject in enumerate(neon):
        spelling = subject["capability"]["spelling"]
        for case in _make_cases(subject):
            key = (index, case.shift if spelling in {"vshlq_n_s16", "vshrn_n_u32"} else None)
            if key not in seen_wrappers:
                wrappers.append(_neon_wrapper(index, spelling, key[1]))
                seen_wrappers.add(key)
            function = f"run_{index}" if key[1] is None else f"run_{index}_shift_{key[1]}"
            left = case.inputs[0]
            right = case.inputs[1] if len(case.inputs) > 1 else 0
            calls.append(
                f'  printf("INTDIFF|{case.case_id}|%016" PRIX64 "\\n", '
                f"{function}(UINT64_C(0x{left:016X}), UINT64_C(0x{right:016X})));"
            )
    return f'''#if !defined(__aarch64__)
#error "native Neon integer differential probe requires AArch64"
#endif
#include <arm_neon.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

#define NOINLINE __attribute__((noinline))

{chr(10).join(wrappers)}
int main(void) {{
  uint64_t saved_fpsr;
  const uint64_t cleared_fpsr = 0;
  __asm__ volatile("mrs %0, fpsr" : "=r"(saved_fpsr));
  __asm__ volatile("msr fpsr, %0" : : "r"(cleared_fpsr) : "memory");
{chr(10).join(calls)}
  __asm__ volatile("msr fpsr, %0" : : "r"(saved_fpsr) : "memory");
  return 0;
}}
'''


def run_native_neon(
    root: Path, subjects: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, int], dict[str, Any]]:
    neon = [item for item in subjects if item["capability"]["architecture"] == "neon"]
    machine = platform.machine().lower()
    clang = shutil.which("clang")
    source = _neon_probe_source(subjects)
    base = {
        "backend": "native-aarch64-neon-c-intrinsics",
        "host_machine": machine,
        "compiler": clang,
        "probe_source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "state_scope": "active-lane-value-only;FPSR.QC-excluded",
    }
    if machine not in {"arm64", "aarch64"}:
        return {}, {**base, "status": "blocked", "blocked_reason": "host-not-aarch64"}
    if clang is None:
        return {}, {**base, "status": "blocked", "blocked_reason": "clang-not-found"}
    with tempfile.TemporaryDirectory(prefix="saltyrn-int-neon-") as directory:
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
            "-Wl,-no_uuid",
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
        assembly_command = [arg for arg in command[:-2] if arg != "-Wl,-no_uuid"]
        assembly = _run(assembly_command + ["-S", "-o", str(assembly_path)], cwd=root)
        executed = _run([str(binary_path)], cwd=root)
        if executed.returncode != 0:
            raise IntegerDifferentialAuditError(
                f"native Neon probe failed:\n{executed.stdout}\n{executed.stderr}"
            )
        results: dict[str, int] = {}
        for line in executed.stdout.splitlines():
            if line.startswith("INTDIFF|"):
                _, case_id, value = line.split("|", 2)
                results[case_id] = int(value, 16)
        cases = [case for subject in neon for case in _make_cases(subject)]
        if len(results) != len(cases):
            raise IntegerDifferentialAuditError(
                f"native Neon returned {len(results)}/{len(cases)} values"
            )
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
                "-Wl,-no_uuid",
                "<temporary>/probe.c",
                "-o",
                "<temporary>/probe",
            ],
            "binary_sha256": _sha256(binary_path),
            "assembly_sha256": _sha256(assembly_path) if assembly.returncode == 0 else None,
            "stdout_sha256": hashlib.sha256(executed.stdout.encode("utf-8")).hexdigest(),
        }
    return results, evidence


def _mode_macro(mode: int) -> str:
    macros = {
        0: "__RISCV_VXRM_RNU",
        1: "__RISCV_VXRM_RNE",
        2: "__RISCV_VXRM_RDN",
        3: "__RISCV_VXRM_ROD",
    }
    try:
        return macros[mode]
    except KeyError as error:
        raise IntegerDifferentialAuditError(f"invalid vxrm mode: {mode}") from error


def _rvv_wrapper(index: int, subject: Mapping[str, Any]) -> str:
    spelling = subject["capability"]["spelling"]
    constraints = _constraints_by_index(subject["audit"])
    name = f"run_{index}"
    if spelling == "__riscv_vnclip_wx_i16m4":
        shift, mode = constraints[1][0], constraints[2][0]
        setup = (
            "size_t vl = __riscv_vsetvl_e16m4(1);\n"
            "  vint32m8_t value = __riscv_vmv_v_x_i32m8((int32_t)(uint32_t)a, vl);\n"
            f"  vint16m4_t result = {spelling}(value, {shift}, {_mode_macro(mode)}, vl);\n"
            "  int16_t output = 0;\n"
            "  __riscv_vse16_v_i16m4(&output, result, vl);\n"
            "  return (uint16_t)output;"
        )
    elif spelling == "__riscv_vnclip_wx_i8m2":
        shift, mode = constraints[1][0], constraints[2][0]
        setup = (
            "size_t vl = __riscv_vsetvl_e8m2(1);\n"
            "  vint16m4_t value = __riscv_vmv_v_x_i16m4((int16_t)(uint16_t)a, vl);\n"
            f"  vint8m2_t result = {spelling}(value, {shift}, {_mode_macro(mode)}, vl);\n"
            "  int8_t output = 0;\n"
            "  __riscv_vse8_v_i8m2(&output, result, vl);\n"
            "  return (uint8_t)output;"
        )
    elif spelling == "__riscv_vnclipu_wx_u8m2":
        shift, mode = constraints[1][0], constraints[2][0]
        setup = (
            "size_t vl = __riscv_vsetvl_e8m2(1);\n"
            "  vuint16m4_t value = __riscv_vmv_v_x_u16m4((uint16_t)a, vl);\n"
            f"  vuint8m2_t result = {spelling}(value, {shift}, {_mode_macro(mode)}, vl);\n"
            "  uint8_t output = 0;\n"
            "  __riscv_vse8_v_u8m2(&output, result, vl);\n"
            "  return output;"
        )
    elif spelling == "__riscv_vnsrl_wx_u16m4":
        setup = (
            "size_t vl = __riscv_vsetvl_e16m4(1);\n"
            "  vuint32m8_t value = __riscv_vmv_v_x_u32m8((uint32_t)a, vl);\n"
            f"  vuint16m4_t result = {spelling}(value, (size_t)b, vl);\n"
            "  uint16_t output = 0;\n"
            "  __riscv_vse16_v_u16m4(&output, result, vl);\n"
            "  return output;"
        )
    elif spelling == "__riscv_vsadd_vx_i16m4":
        setup = (
            "size_t vl = __riscv_vsetvl_e16m4(1);\n"
            "  vint16m4_t value = __riscv_vmv_v_x_i16m4((int16_t)(uint16_t)a, vl);\n"
            f"  vint16m4_t result = {spelling}(value, (int16_t)(uint16_t)b, vl);\n"
            "  int16_t output = 0;\n"
            "  __riscv_vse16_v_i16m4(&output, result, vl);\n"
            "  return (uint16_t)output;"
        )
    elif spelling == "__riscv_vsll_vx_i16m4":
        shift = constraints[1][0]
        setup = (
            "size_t vl = __riscv_vsetvl_e16m4(1);\n"
            "  vint16m4_t value = __riscv_vmv_v_x_i16m4((int16_t)(uint16_t)a, vl);\n"
            f"  vint16m4_t result = {spelling}(value, {shift}, vl);\n"
            "  int16_t output = 0;\n"
            "  __riscv_vse16_v_i16m4(&output, result, vl);\n"
            "  return (uint16_t)output;"
        )
    elif spelling == "__riscv_vsll_vx_i32m8":
        setup = (
            "size_t vl = __riscv_vsetvl_e32m8(1);\n"
            "  vint32m8_t value = __riscv_vmv_v_x_i32m8((int32_t)(uint32_t)a, vl);\n"
            f"  vint32m8_t result = {spelling}(value, (size_t)b, vl);\n"
            "  int32_t output = 0;\n"
            "  __riscv_vse32_v_i32m8(&output, result, vl);\n"
            "  return (uint32_t)output;"
        )
    elif spelling == "__riscv_vssra_vx_i32m8":
        mode = constraints[2][0]
        setup = (
            "size_t vl = __riscv_vsetvl_e32m8(1);\n"
            "  vint32m8_t value = __riscv_vmv_v_x_i32m8((int32_t)(uint32_t)a, vl);\n"
            f"  vint32m8_t result = {spelling}(value, (size_t)b, {_mode_macro(mode)}, vl);\n"
            "  int32_t output = 0;\n"
            "  __riscv_vse32_v_i32m8(&output, result, vl);\n"
            "  return (uint32_t)output;"
        )
    else:
        raise IntegerDifferentialAuditError(f"unsupported RVV wrapper: {spelling}")
    return f"NOINLINE uint64_t {name}(uint64_t a, uint64_t b) {{\n  {setup}\n}}\n"


def _rvv_probe_sources(
    subjects: Sequence[Mapping[str, Any]],
) -> tuple[str, str, tuple[IntegerCase, ...]]:
    rvv = [item for item in subjects if item["capability"]["architecture"] == "rvv"]
    wrappers = [_rvv_wrapper(index, subject) for index, subject in enumerate(rvv)]
    cases: list[IntegerCase] = []
    start = [
        ".option norvc",
        ".text",
        ".globl _start",
        "_start:",
        "  li sp, 0x80020000",
        "  li t0, 0x600",
        "  csrs mstatus, t0",
        "  csrwi vxsat, 0",
    ]
    for index, subject in enumerate(rvv):
        for case in _make_cases(subject):
            cases.append(case)
            left = case.inputs[0]
            if len(case.inputs) > 1:
                right = case.inputs[1]
            elif case.shift is not None:
                right = case.shift
            else:
                right = 0
            start.extend(
                [
                    f"  # INTDIFF {case.case_id}",
                    f"  li a0, 0x{left:016X}",
                    f"  li a1, 0x{right:016X}",
                    f"  call run_{index}",
                    "  mv s1, a0",
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
        Path(shutil.which("clang-20") or ""),
        Path(shutil.which("clang") or ""),
    ]
    cross_clang = next((str(path) for path in clang_candidates if path.is_file()), None)
    c_source, start_source, cases = _rvv_probe_sources(subjects)
    tools = {
        "cross_clang": cross_clang,
        "linker": linker,
        "objdump": objdump,
        "spike": spike,
    }
    base = {
        "backend": "spike-rvv-c-intrinsics",
        "tools": tools,
        "probe_c_source_sha256": hashlib.sha256(c_source.encode("utf-8")).hexdigest(),
        "probe_start_source_sha256": hashlib.sha256(start_source.encode("utf-8")).hexdigest(),
        "isa": "rv64gcv_zvl128b",
        "state_scope": "active-lane-value-only;vxsat-excluded;vl=1",
    }
    missing = [name for name, path in tools.items() if path is None]
    if missing:
        return {}, {
            **base,
            "status": "blocked",
            "blocked_reason": "missing-rvv-toolchain:" + ",".join(missing),
        }
    with tempfile.TemporaryDirectory(prefix="saltyrn-int-rvv-") as directory:
        directory_path = Path(directory)
        c_path = directory_path / "probe.c"
        start_path = directory_path / "start.S"
        c_object = directory_path / "probe.o"
        start_object = directory_path / "start.o"
        elf_path = directory_path / "probe.elf"
        disassembly_path = directory_path / "probe.disassembly.txt"
        c_path.write_text(c_source, encoding="utf-8")
        start_path.write_text(start_source, encoding="utf-8")
        common = [
            cross_clang,
            "--target=riscv64-unknown-elf",
            "-march=rv64gcv_zvl128b",
            "-mabi=lp64d",
        ]
        c_command = common + ["-O2", "-ffreestanding", "-c", str(c_path), "-o", str(c_object)]
        start_command = common + ["-c", str(start_path), "-o", str(start_object)]
        compiled_c = _run(c_command, cwd=root)
        compiled_start = _run(start_command, cwd=root)
        if compiled_c.returncode != 0 or compiled_start.returncode != 0:
            return {}, {
                **base,
                "status": "blocked",
                "blocked_reason": "rvv-c-intrinsic-cross-compile-failed",
                "compiler_stderr": compiled_c.stderr + compiled_start.stderr,
            }
        link_command = [
            linker,
            "-Ttext=0x80001000",
            "-e",
            "_start",
            "--no-relax",
            str(start_object),
            str(c_object),
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
        disassembled = _run([objdump, "-d", str(elf_path)], cwd=root)
        if disassembled.returncode != 0:
            return {}, {
                **base,
                "status": "blocked",
                "blocked_reason": "rvv-disassembly-failed",
                "objdump_stderr": disassembled.stderr,
            }
        normalized_disassembly = disassembled.stdout.replace(
            str(directory_path), "<temporary>"
        )
        disassembly_path.write_text(normalized_disassembly, encoding="utf-8")
        for subject in subjects:
            if subject["capability"]["architecture"] != "rvv":
                continue
            selector = subject["audit"]["primary_evidence"]["isa_selector"]
            accepted = {selector}
            if selector.endswith(".wx"):
                accepted.add(selector.removesuffix(".wx") + ".wi")
            if selector.endswith(".vx"):
                accepted.add(selector.removesuffix(".vx") + ".vi")
            if not any(candidate in disassembled.stdout for candidate in accepted):
                raise IntegerDifferentialAuditError(
                    f"compiled RVV probe lacks expected selector/lowering {sorted(accepted)}"
                )
        instruction_limit = max(5000, len(cases) * 120)
        spike_command = [
            spike,
            "--isa=rv64gcv_zvl128b",
            "--pc=0x80001000",
            f"--instructions={instruction_limit}",
            "-l",
            "--log-commits",
            str(elf_path),
        ]
        executed = _run(spike_command, cwd=root, timeout=240)
        log = executed.stdout + executed.stderr
        if executed.returncode != 0:
            return {}, {
                **base,
                "status": "blocked",
                "blocked_reason": "spike-execution-failed",
                "spike_log_tail": log[-4000:],
            }
        marker_pattern = re.compile(
            r"\([^)]*\)\s+(?:mv|addi)\s+s1,\s*a0(?:,\s*0)?\n"
            r"core\s+0:\s+3\s+[^\n]*\bx9\s+0x([0-9a-fA-F]{16})"
        )
        values = [int(value, 16) for value in marker_pattern.findall(log)]
        if len(values) != len(cases):
            raise IntegerDifferentialAuditError(
                f"Spike returned {len(values)}/{len(cases)} marked RVV values"
            )
        results = {
            case.case_id: value & ((1 << case.output_width) - 1)
            for case, value in zip(cases, values, strict=True)
        }
        evidence = {
            **base,
            "status": "passed",
            "compiler_version": _tool_version(cross_clang),
            "linker_version": _tool_version(linker),
            "objdump_version": _tool_version(objdump),
            "spike_version": _tool_version(spike),
            "compile_commands": [
                [
                    "clang",
                    "--target=riscv64-unknown-elf",
                    "-march=rv64gcv_zvl128b",
                    "-mabi=lp64d",
                    "-O2",
                    "-ffreestanding",
                    "-c",
                    "<temporary>/probe.c",
                ],
                [
                    "clang",
                    "--target=riscv64-unknown-elf",
                    "-march=rv64gcv_zvl128b",
                    "-mabi=lp64d",
                    "-c",
                    "<temporary>/start.S",
                ],
            ],
            "run_command": [
                "spike",
                "--isa=rv64gcv_zvl128b",
                "--pc=0x80001000",
                f"--instructions={instruction_limit}",
                "-l",
                "--log-commits",
                "<temporary>/probe.elf",
            ],
            "elf_sha256": _sha256(elf_path),
            "disassembly_sha256": _sha256(disassembly_path),
            "commit_log_sha256": hashlib.sha256(log.encode("utf-8")).hexdigest(),
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
        raise IntegerDifferentialAuditError(f"Lean definition is absent: {symbol}")
    return {
        "symbol": symbol,
        "definition_path": path.relative_to(root).as_posix(),
        "definition_line": line,
        "definition_file_sha256": _sha256(path),
    }


def _c_calls(
    root: Path, architecture: str, spelling: str, programs: Sequence[str]
) -> list[dict[str, Any]]:
    side = "source" if architecture == "neon" else "target"
    result: list[dict[str, Any]] = []
    for program in programs:
        path = root / f"kernels/{side}/{program}.c"
        if not path.is_file():
            raise IntegerDifferentialAuditError(f"audited kernel source is absent: {path}")
        digest = _sha256(path)
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(rf"\b{re.escape(spelling)}\s*\(", line):
                result.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "line": line_number,
                        "text": line.strip(),
                        "file_sha256": digest,
                    }
                )
    if not result:
        raise IntegerDifferentialAuditError(f"no real C call found for {spelling}")
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


def _state_effect_scope(spelling: str) -> str:
    if spelling.startswith(("vq", "vrshl")):
        return "active-lane-value-only;FPSR.QC-excluded"
    if any(token in spelling for token in ("vnclip", "vsadd")):
        return "active-lane-value-only;vxsat-excluded"
    return "active-lane-value-only;no-sticky-saturation-state-claimed"


def build_audit(root: Path) -> dict[str, Any]:
    corpus = root / "verification/elementwise-compiler"
    subjects = load_exact_subjects(root, corpus)
    lean_results, lean_backend = evaluate_lean(root, subjects)
    neon_results, neon_backend = run_native_neon(root, subjects)
    rvv_results, rvv_backend = run_spike_rvv(root, subjects)
    rows: list[dict[str, Any]] = []
    for subject in subjects:
        capability = subject["capability"]
        audit = subject["audit"]
        architecture = capability["architecture"]
        backend = neon_backend if architecture == "neon" else rvv_backend
        oracle_results = neon_results if architecture == "neon" else rvv_results
        cases: list[dict[str, Any]] = []
        for case in _make_cases(subject):
            expected = lean_results[case.case_id]
            actual = oracle_results.get(case.case_id)
            if backend["status"] == "blocked":
                verdict = "blocked"
            else:
                verdict = "passed" if actual == expected else "mismatch"
            cases.append(
                {
                    "case_id": case.case_id,
                    "inputs_bits": [
                        f"0x{value:0{(width + 3) // 4}X}"
                        for value, width in zip(case.inputs, case.input_widths)
                    ],
                    "input_widths": list(case.input_widths),
                    "shift": case.shift,
                    "vxrm": case.mode,
                    "observed_lane": case.observed_lane,
                    "output_width": case.output_width,
                    "expected_bits": f"0x{expected:0{(case.output_width + 3) // 4}X}",
                    "actual_bits": (
                        None
                        if actual is None
                        else f"0x{actual:0{(case.output_width + 3) // 4}X}"
                    ),
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
            "semantic_family": subject["semantic_family"],
            "subject_scope": subject["subject_scope"],
            "registry_used": bool(audit["used"]),
            "architecture": architecture,
            "spelling": capability["spelling"],
            "function_type": capability["function_type"],
            "immediate_constraints": audit["immediate_constraints"],
            "architecture_conditions": audit["architecture_conditions"],
            "c_calls": (
                _c_calls(root, architecture, capability["spelling"], audit["programs"])
                if audit["programs"]
                else []
            ),
            "real_c_call_scope": (
                "current-kernel-calls-and-generated-oracle-call"
                if audit["programs"]
                else "no-current-kernel-call;generated-oracle-calls-exact-intrinsic"
            ),
            "official_pinned_source": _authority_evidence(root, audit["primary_evidence"]),
            "lean": _definition_evidence(root, capability["semantic_symbol"]),
            "oracle_backend": backend,
            "evidence_level": EVIDENCE_LEVEL,
            "coverage_scope": COVERAGE_SCOPE,
            "state_effect_scope": _state_effect_scope(capability["spelling"]),
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
        "state_exclusions": list(STATE_EXCLUSIONS),
        "verdict_definition": (
            "passed means every listed boundary vector matched its architecture oracle; "
            "it is sampled L3 evidence, not a proof of the full intrinsic"
        ),
        "semantic_family_source_path": "verification/elementwise-compiler/IntrinsicReviewPlan.json",
        "semantic_family_source_sha256": _sha256(
            corpus / "IntrinsicReviewPlan.json"
        ),
        "selected_semantic_families": sorted(P1_FAMILIES),
        "explicit_regression_capability_ids": sorted(REPAIRED_REGRESSION_CAPABILITY_IDS),
        "registry_path": "verification/elementwise-compiler/IntrinsicRegistry.json",
        "registry_file_sha256": _sha256(corpus / "IntrinsicRegistry.json"),
        "registry_sha256": _load_json(corpus / "IntrinsicRegistry.json")["registry_sha256"],
        "intrinsic_audit_path": "verification/elementwise-compiler/IntrinsicAudit.json",
        "intrinsic_audit_file_sha256": _sha256(corpus / "IntrinsicAudit.json"),
        "intrinsic_audit_sha256": _load_json(corpus / "IntrinsicAudit.json")["audit_sha256"],
        "lean_backend": lean_backend,
        "toolchain_inventory": {"native_neon": neon_backend, "rvv": rvv_backend},
        "ledger_projection_path": (
            "verification/elementwise-compiler/IntegerDifferentialAuditLedger.csv"
        ),
        "ledger_join_key": "capability_id",
        "counts": counts,
        "subjects": rows,
    }
    validate_audit(record)
    record["audit_sha256"] = canonical_sha256(record)
    return record


def render_ledger_projection(record: Mapping[str, Any]) -> str:
    fields = (
        "capability_id",
        "semantic_family",
        "subject_scope",
        "registry_used",
        "evidence_level",
        "coverage_scope",
        "state_effect_scope",
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
                "semantic_family": subject["semantic_family"],
                "subject_scope": subject["subject_scope"],
                "registry_used": "yes" if subject["registry_used"] else "no",
                "evidence_level": EVIDENCE_LEVEL,
                "coverage_scope": COVERAGE_SCOPE,
                "state_effect_scope": subject["state_effect_scope"],
                "differential_test_status": f"{subject['status']}-sampled",
                "oracle_backend": subject["oracle_backend"]["backend"],
                "executed_vectors": executed,
                "total_vectors": len(subject["cases"]),
                "mismatch_found": "yes" if subject["status"] == "mismatch" else "no",
                "evidence_path": (
                    "verification/elementwise-compiler/IntegerDifferentialAudit.json"
                ),
                "evidence_sha256": subject["evidence_sha256"],
                "full_intrinsic_proof": "no",
            }
        )
    return stream.getvalue()


def validate_audit(record: Mapping[str, Any]) -> None:
    if record.get("artifact_kind") != ARTIFACT_KIND or record.get("schema_version") != 1:
        raise IntegerDifferentialAuditError("invalid integer differential kind/schema")
    if record.get("evidence_level") != EVIDENCE_LEVEL:
        raise IntegerDifferentialAuditError("integer audit must be labeled L3-sampled")
    if record.get("coverage_scope") != COVERAGE_SCOPE:
        raise IntegerDifferentialAuditError("integer audit coverage scope changed")
    if record.get("state_exclusions") != list(STATE_EXCLUSIONS):
        raise IntegerDifferentialAuditError("integer audit state exclusions changed")
    subjects = record.get("subjects")
    if not isinstance(subjects, list) or not subjects:
        raise IntegerDifferentialAuditError("integer audit must contain P1 subjects")
    capability_ids: set[str] = set()
    for row in subjects:
        if not isinstance(row, dict):
            raise IntegerDifferentialAuditError("integer differential subject must be an object")
        capability_id = row.get("capability_id")
        if not isinstance(capability_id, str) or capability_id in capability_ids:
            raise IntegerDifferentialAuditError("integer capability IDs must be unique")
        capability_ids.add(capability_id)
        if row.get("semantic_family") not in P1_FAMILIES | {REPAIRED_REGRESSION_FAMILY}:
            raise IntegerDifferentialAuditError(f"non-P1 family subject: {capability_id}")
        if row.get("subject_scope") not in {
            "current-P1-exact",
            "explicit-repaired-regression-unused",
        }:
            raise IntegerDifferentialAuditError(f"invalid subject scope: {capability_id}")
        digest = row.get("evidence_sha256")
        unsigned = dict(row)
        unsigned.pop("evidence_sha256", None)
        if digest != canonical_sha256(unsigned):
            raise IntegerDifferentialAuditError(
                f"subject evidence digest mismatch: {capability_id}"
            )
        if row.get("status") not in {"passed", "blocked", "mismatch"}:
            raise IntegerDifferentialAuditError(f"invalid subject status: {capability_id}")
        if row.get("evidence_level") != EVIDENCE_LEVEL:
            raise IntegerDifferentialAuditError(f"subject lacks L3 scope: {capability_id}")
        if row.get("coverage_scope") != COVERAGE_SCOPE:
            raise IntegerDifferentialAuditError(f"subject scope changed: {capability_id}")
        cases = row.get("cases")
        if not isinstance(cases, list) or not cases:
            raise IntegerDifferentialAuditError(f"subject lacks cases: {capability_id}")
        for case in cases:
            if case.get("verdict") not in {"passed", "blocked", "mismatch"}:
                raise IntegerDifferentialAuditError(f"invalid case verdict: {capability_id}")
            output_width = case.get("output_width")
            expected = case.get("expected_bits")
            actual = case.get("actual_bits")
            digits = (output_width + 3) // 4 if isinstance(output_width, int) else 0
            pattern = rf"0x[0-9A-F]{{{digits}}}"
            if not isinstance(expected, str) or re.fullmatch(pattern, expected) is None:
                raise IntegerDifferentialAuditError(f"invalid expected bits: {capability_id}")
            if actual is not None and (
                not isinstance(actual, str) or re.fullmatch(pattern, actual) is None
            ):
                raise IntegerDifferentialAuditError(f"invalid actual bits: {capability_id}")


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("verification/elementwise-compiler/IntegerDifferentialAudit.json"),
    )
    parser.add_argument(
        "--ledger-output",
        type=Path,
        default=Path(
            "verification/elementwise-compiler/IntegerDifferentialAuditLedger.csv"
        ),
    )
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    output = arguments.output if arguments.output.is_absolute() else root / arguments.output
    ledger = (
        arguments.ledger_output
        if arguments.ledger_output.is_absolute()
        else root / arguments.ledger_output
    )
    record = build_audit(root)
    rendered = canonical_json(record, pretty=True)
    ledger_rendered = render_ledger_projection(record)
    if arguments.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise IntegerDifferentialAuditError(f"stale integer differential audit: {output}")
        if not ledger.is_file() or ledger.read_text(encoding="utf-8") != ledger_rendered:
            raise IntegerDifferentialAuditError(
                f"stale integer differential ledger projection: {ledger}"
            )
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(ledger_rendered, encoding="utf-8")
    print(json.dumps(record["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
