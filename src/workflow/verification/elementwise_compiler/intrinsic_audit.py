"""Generate a fail-closed primary-source audit of exact intrinsic variants.

This command does not approve reviews.  It verifies that every exact variant in
the published elementwise graph is backed by a pinned Arm ACLE or RISC-V Vector C
Intrinsics source selector, that source arity agrees with the parsed C contract,
and that the descriptor still matches the canonical registry.  A read-only
reviewer consumes the resulting report before any ``IntrinsicReview`` records are
published.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from workflow.verification.intrinsic_dashboard.elementwise_graph import (
    build_elementwise_graph,
)
from workflow.verification.lean_backend.descriptor import (
    canonical_spec_digest,
    canonical_spec_record,
)
from workflow.verification.lean_backend.intrinsic_index import (
    CANONICAL_INTRINSIC_INDEX,
)
from workflow.verification.lean_backend.schema import (
    Architecture as BackendArchitecture,
    IntrinsicSpec,
    SemanticIntrinsic,
    render_clang_function_type,
)

from .schema import canonical_json, canonical_sha256


ACLE_REVISION = "c218a6b499897e70d88ceab7c6148d692541929f"
RVV_REVISION = "b611045daf6c1f2449a5dad6f1a1a6b244b52798"
RISCV_ISA_REVISION = "846efd1c46315ed8ae3da3d15209bc49114246f5"
ACLE_SOURCE_URL = (
    "https://github.com/ARM-software/acle/blob/"
    f"{ACLE_REVISION}/tools/intrinsic_db/advsimd.csv"
)
RVV_SOURCE_PREFIX = (
    "https://github.com/riscv-non-isa/rvv-intrinsic-doc/blob/"
    f"{RVV_REVISION}/"
)
RISCV_ISA_SOURCE_PREFIX = (
    "https://github.com/riscv/riscv-isa-manual/blob/"
    f"{RISCV_ISA_REVISION}/"
)


class IntrinsicAuditError(RuntimeError):
    """The corpus, canonical descriptor, or pinned primary evidence disagrees."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_git_revision(root: Path, revision: str) -> None:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        raise IntrinsicAuditError(f"pinned source revision is absent: {revision}")


def _require_pinned_file(root: Path, revision: str, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        raise IntrinsicAuditError(f"pinned primary source is absent: {relative}")
    completed = subprocess.run(
        ["git", "show", f"{revision}:{relative}"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0 or completed.stdout != path.read_bytes():
        raise IntrinsicAuditError(
            f"primary source does not match {revision}:{relative}"
        )
    return hashlib.sha256(completed.stdout).hexdigest()


def _split_arguments(text: str) -> tuple[str, ...]:
    """Split one flat C call/prototype argument list fail closed."""

    if not text.strip():
        return ()
    result: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(text):
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                raise IntrinsicAuditError("unbalanced official argument list")
        elif character == "," and depth == 0:
            result.append(text[start:index].strip())
            start = index + 1
    if depth != 0:
        raise IntrinsicAuditError("unbalanced official argument list")
    result.append(text[start:].strip())
    if any(not item for item in result):
        raise IntrinsicAuditError("empty official argument")
    return tuple(result)


def _balanced_call_arguments(source: str, opening: int) -> tuple[str, ...]:
    depth = 1
    cursor = opening + 1
    while cursor < len(source) and depth:
        if source[cursor] == "(":
            depth += 1
        elif source[cursor] == ")":
            depth -= 1
        cursor += 1
    if depth:
        raise IntrinsicAuditError("unterminated primary-source intrinsic call")
    return _split_arguments(source[opening + 1 : cursor - 1])


def _canonical_c_type(value: str) -> str:
    value = value.strip()
    value = re.sub(r"__builtin_constant_p\([^)]*\)", "int", value)
    value = re.sub(r"\bfloat32_t\b", "float", value)
    value = re.sub(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s+const\b", r"const \1", value
    )
    value = re.sub(r"\s*\*\s*", " *", value)
    return re.sub(r"\s+", " ", value).strip()


def _prototype_parameter_type(value: str) -> str:
    value = value.strip()
    if value.startswith("__builtin_constant_p("):
        return "int"
    value = re.sub(r"\s+[A-Za-z_][A-Za-z0-9_]*$", "", value)
    value = re.sub(r"\*([A-Za-z_][A-Za-z0-9_]*)$", "*", value)
    return _canonical_c_type(value)


def _canonical_function_type(value: str) -> str:
    matched = re.fullmatch(r"(.+?)\s*\((.*)\)", value.strip())
    if matched is None:
        raise IntrinsicAuditError(f"malformed function type: {value!r}")
    arguments = _split_arguments(matched.group(2))
    return (
        f"{_canonical_c_type(matched.group(1))} ("
        + ", ".join(_canonical_c_type(item) for item in arguments)
        + ")"
    )


def _acle_prototypes(path: Path) -> Mapping[str, tuple[dict[str, Any], ...]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        columns = line.split("\t")
        if not columns or columns[0].startswith("<"):
            continue
        matched = re.fullmatch(
            r"(.+?)\s+([A-Za-z_][A-Za-z0-9_]*)\((.*)\)", columns[0]
        )
        if matched is None:
            continue
        parameters = _split_arguments(matched.group(3))
        official_type = (
            f"{_canonical_c_type(matched.group(1))} ("
            + ", ".join(_prototype_parameter_type(item) for item in parameters)
            + ")"
        )
        result[matched.group(2)].append(
            {
                "line": line_number,
                "prototype": columns[0],
                "function_type": official_type,
                "argument_count": len(parameters),
                "instruction": columns[2] if len(columns) > 2 else "",
            }
        )
    return {key: tuple(value) for key, value in result.items()}


def _rvv_prototypes(path: Path) -> Mapping[str, tuple[dict[str, Any], ...]]:
    """Parse the generated official RVV C API prototypes, including wrapped rows."""

    source = path.read_text(encoding="utf-8")
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    pattern = re.compile(
        r"(?m)^[ \t]*(?P<return>[A-Za-z_][A-Za-z0-9_ ]*?)\s+"
        r"(?P<name>__riscv_[A-Za-z0-9_]+)\((?P<parameters>.*?)\);[ \t]*$",
        re.DOTALL,
    )
    for matched in pattern.finditer(source):
        parameters = _split_arguments(matched.group("parameters"))
        prototype = re.sub(r"\s+", " ", matched.group(0)).strip()
        official_type = (
            f"{_canonical_c_type(matched.group('return'))} ("
            + ", ".join(_prototype_parameter_type(item) for item in parameters)
            + ")"
        )
        result[matched.group("name")].append(
            {
                "line": source.count("\n", 0, matched.start()) + 1,
                "prototype": prototype,
                "function_type": official_type,
                "argument_count": len(parameters),
            }
        )
    return {key: tuple(value) for key, value in result.items()}


def _rvv_calls(root: Path) -> Mapping[str, tuple[dict[str, Any], ...]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    pattern = re.compile(r"\b(__riscv_[A-Za-z0-9_]+)\s*\(")
    for path in sorted(root.glob("*.c")):
        source = path.read_text(encoding="utf-8")
        for matched in pattern.finditer(source):
            arguments = _balanced_call_arguments(source, matched.end() - 1)
            result[matched.group(1)].append(
                {
                    "path": path.name,
                    "line": source.count("\n", 0, matched.start()) + 1,
                    "argument_count": len(arguments),
                    "arguments": list(arguments),
                }
            )
    return {key: tuple(value) for key, value in result.items()}


def _rvv_isa_selector(spelling: str) -> str:
    body = spelling.removeprefix("__riscv_")
    if body.startswith("vreinterpret_"):
        return "reinterpret-pseudo-intrinsic"
    if body.startswith("vsetvl_"):
        return "vsetvl"
    suffix = re.compile(r"_(?:[iuf]\d+m(?:f)?\d+|b\d+)$")
    while suffix.search(body):
        body = suffix.sub("", body)
    return body.replace("_", ".")


def _architecture_conditions(spec: IntrinsicSpec) -> tuple[str, ...]:
    """Describe state assumptions of the current pure value abstraction.

    These annotations do not establish an ISA theorem.  They prevent a reviewer
    from confusing the pure RNE binary32 model with every legal architectural
    floating-point environment.
    """

    if not isinstance(spec, SemanticIntrinsic):
        return ()
    spelling = spec.spelling
    if spec.architecture is BackendArchitecture.RVV and spelling.startswith("__riscv_vf"):
        if any(token in spelling for token in ("add", "sub", "mul", "div", "sqrt", "cvt")):
            return ("rvv.frm=RNE", "rvv.frm-valid", "rvv.fflags-outside-value-claim")
        if any(token in spelling for token in ("max", "min")):
            return ("rvv.fflags-outside-value-claim",)
        return ()
    if spec.architecture is BackendArchitecture.RVV and spelling.startswith("__riscv_vmf"):
        return ("rvv.fflags-outside-value-claim",)
    if spec.architecture is BackendArchitecture.NEON and "f32" in spelling:
        if any(token in spelling for token in ("add", "sub", "mul", "div", "sqrt", "cvt")):
            return (
                "arm.fpcr.RMode=RN",
                "arm.fpcr.FZ=0",
                "arm.fpcr.DN=0",
                "arm.fpsr-outside-value-claim",
            )
        if spelling == "vcaltq_f32":
            return ("arm.fpcr.FZ=0", "arm.fpsr-outside-value-claim")
        if any(token in spelling for token in ("max", "min")):
            return (
                "arm.fpcr.FZ=0",
                "arm.fpcr.DN=0",
                "arm.fpsr-outside-value-claim",
            )
        return ()
    return ()


def _descriptor_by_digest() -> Mapping[str, IntrinsicSpec]:
    result: dict[str, IntrinsicSpec] = {}
    for variant in CANONICAL_INTRINSIC_INDEX.variants:
        digest = canonical_spec_digest(variant.spec)
        previous = result.setdefault(digest, variant.spec)
        if canonical_spec_record(previous) != canonical_spec_record(variant.spec):
            raise IntrinsicAuditError("canonical descriptor digest collision")
    return result


def build_intrinsic_audit(
    repository_root: str | Path,
    *,
    acle_root: str | Path,
    rvv_root: str | Path,
    riscv_isa_root: str | Path,
) -> dict[str, Any]:
    repository = Path(repository_root).resolve()
    acle = Path(acle_root).resolve()
    rvv = Path(rvv_root).resolve()
    riscv_isa = Path(riscv_isa_root).resolve()
    _require_git_revision(acle, ACLE_REVISION)
    _require_git_revision(rvv, RVV_REVISION)
    _require_git_revision(riscv_isa, RISCV_ISA_REVISION)
    acle_csv = acle / "tools/intrinsic_db/advsimd.csv"
    rvv_api = rvv / "auto-generated/api-testing"
    rvv_prototype_path = rvv / "auto-generated/intrinsic_funcs.adoc"
    rvv_doc = rvv / "doc/rvv-intrinsic-spec.adoc"
    if (
        not acle_csv.is_file()
        or not rvv_doc.is_file()
        or not rvv_prototype_path.is_file()
        or not rvv_api.is_dir()
    ):
        raise IntrinsicAuditError("pinned primary-source inventory is incomplete")
    acle_sha256 = _require_pinned_file(
        acle, ACLE_REVISION, "tools/intrinsic_db/advsimd.csv"
    )
    rvv_doc_sha256 = _require_pinned_file(
        rvv, RVV_REVISION, "doc/rvv-intrinsic-spec.adoc"
    )
    rvv_prototype_sha256 = _require_pinned_file(
        rvv, RVV_REVISION, "auto-generated/intrinsic_funcs.adoc"
    )
    vector_isa_relative = "src/unpriv/vector-common.adoc"
    scalar_fp_relative = "src/unpriv/f-st-ext.adoc"
    vector_isa_sha256 = _require_pinned_file(
        riscv_isa, RISCV_ISA_REVISION, vector_isa_relative
    )
    scalar_fp_sha256 = _require_pinned_file(
        riscv_isa, RISCV_ISA_REVISION, scalar_fp_relative
    )
    vector_isa_source = (riscv_isa / vector_isa_relative).read_text(encoding="utf-8")

    graph = build_elementwise_graph(
        repository / "verification/elementwise-compiler",
        include_intrinsic_audit=False,
    )
    if graph.get("schema_version") != 3 or graph.get("available") is not True:
        raise IntrinsicAuditError("schema-v3 elementwise graph is unavailable")
    descriptors = _descriptor_by_digest()
    acle_records = _acle_prototypes(acle_csv)
    rvv_prototypes = _rvv_prototypes(rvv_prototype_path)
    rvv_calls = _rvv_calls(rvv_api)
    rvv_hashes: dict[str, str] = {}
    variants: list[dict[str, Any]] = []

    for capability in graph["capabilities"]:
        descriptor_digest = str(capability["descriptor_sha256"])
        spec = descriptors.get(descriptor_digest)
        if spec is None:
            raise IntrinsicAuditError(
                f"{capability['id']}: descriptor is absent from canonical index"
            )
        expected_type = render_clang_function_type(spec.signature)
        if expected_type != capability["function_type"]:
            raise IntrinsicAuditError(
                f"{capability['id']}: canonical descriptor type mismatch"
            )
        if canonical_spec_digest(spec) != descriptor_digest:
            raise IntrinsicAuditError(f"{capability['id']}: descriptor digest mismatch")
        if isinstance(spec, SemanticIntrinsic):
            if capability["semantic_symbol"] != spec.lean_name:
                raise IntrinsicAuditError(f"{capability['id']}: Lean symbol mismatch")
        elif capability["semantic_symbol"] is not None:
            raise IntrinsicAuditError(f"{capability['id']}: unexpected Lean symbol")

        if capability["architecture"] == "neon":
            candidates = acle_records.get(str(capability["spelling"]), ())
            canonical_expected = _canonical_function_type(expected_type)
            matches = [
                row
                for row in candidates
                if row["argument_count"] == capability["argument_count"]
                and row["function_type"] == canonical_expected
            ]
            if not matches:
                raise IntrinsicAuditError(
                    f"{capability['id']}: no exact Arm ACLE prototype"
                )
            selected = matches[0]
            evidence = {
                "authority": "Arm ACLE",
                "revision": ACLE_REVISION,
                "source_url": ACLE_SOURCE_URL,
                "path": "tools/intrinsic_db/advsimd.csv",
                "file_sha256": acle_sha256,
                "selector": capability["spelling"],
                "line": selected["line"],
                "prototype": selected["prototype"],
                "instruction": selected["instruction"],
            }
        elif capability["architecture"] == "rvv":
            candidates = rvv_prototypes.get(str(capability["spelling"]), ())
            canonical_expected = _canonical_function_type(expected_type)
            matches = [
                row
                for row in candidates
                if row["argument_count"] == capability["argument_count"]
                and row["function_type"] == canonical_expected
            ]
            if not matches:
                raise IntrinsicAuditError(
                    f"{capability['id']}: no exact RVV official prototype"
                )
            selected = matches[0]
            call_candidates = rvv_calls.get(str(capability["spelling"]), ())
            call_matches = [
                row
                for row in call_candidates
                if row["argument_count"] == capability["argument_count"]
            ]
            if not call_matches:
                raise IntrinsicAuditError(
                    f"{capability['id']}: no exact-arity RVV official API test call"
                )
            selected_call = call_matches[0]
            relative = f"auto-generated/api-testing/{selected_call['path']}"
            rvv_hashes.setdefault(
                relative, _require_pinned_file(rvv, RVV_REVISION, relative)
            )
            isa_selector = _rvv_isa_selector(str(capability["spelling"]))
            if isa_selector == "reinterpret-pseudo-intrinsic":
                isa_path = "doc/rvv-intrinsic-spec.adoc"
                isa_sha256 = rvv_doc_sha256
                isa_source_url = RVV_SOURCE_PREFIX + isa_path
                isa_line = 592
            else:
                position = vector_isa_source.find(isa_selector)
                if position < 0:
                    raise IntrinsicAuditError(
                        f"{capability['id']}: ISA selector is absent: {isa_selector}"
                    )
                isa_path = vector_isa_relative
                isa_sha256 = vector_isa_sha256
                isa_source_url = RISCV_ISA_SOURCE_PREFIX + isa_path
                isa_line = vector_isa_source.count("\n", 0, position) + 1
            evidence = {
                "authority": "RISC-V Vector C Intrinsics",
                "revision": RVV_REVISION,
                "source_url": RVV_SOURCE_PREFIX + "auto-generated/intrinsic_funcs.adoc",
                "path": "auto-generated/intrinsic_funcs.adoc",
                "file_sha256": rvv_prototype_sha256,
                "selector": capability["spelling"],
                "line": selected["line"],
                "prototype": selected["prototype"],
                "function_type": selected["function_type"],
                "api_test_path": relative,
                "api_test_sha256": rvv_hashes[relative],
                "api_test_line": selected_call["line"],
                "api_test_arguments": selected_call["arguments"],
                "spec_path": "doc/rvv-intrinsic-spec.adoc",
                "spec_sha256": rvv_doc_sha256,
                "isa_authority": "RISC-V Instruction Set Manual",
                "isa_revision": RISCV_ISA_REVISION,
                "isa_source_url": isa_source_url,
                "isa_path": isa_path,
                "isa_file_sha256": isa_sha256,
                "isa_selector": isa_selector,
                "isa_line": isa_line,
            }
        else:
            raise IntrinsicAuditError(f"{capability['id']}: unknown architecture")

        conditions = tuple(sorted(_architecture_conditions(spec)))
        variant: dict[str, Any] = {
                "capability_id": capability["id"],
                "used": bool(capability["used"]),
                "programs": list(capability["programs"]),
                "architecture": capability["architecture"],
                "spelling": capability["spelling"],
                "function_type": capability["function_type"],
                "argument_count": capability["argument_count"],
                "role": capability["role"],
                "descriptor_sha256": descriptor_digest,
                "implementation_sha256": capability["implementation_sha256"],
                "semantic_symbol": capability["semantic_symbol"],
                "immediate_constraints": canonical_spec_record(spec)[
                    "immediate_constraints"
                ],
                "architecture_conditions": list(conditions),
                "claim_scope": (
                    "pure-value-model-with-explicit-architecture-conditions"
                    if conditions
                    else "pure-value-model"
                ),
                "primary_evidence": evidence,
                "static_checks": {
                    "canonical_descriptor": "passed",
                    "exact_source_signature": "passed",
                    "implementation_bound": "passed",
                },
            }
        audited_subject = {
            key: value for key, value in variant.items() if key not in {"used", "programs"}
        }
        variant["audit_variant_sha256"] = canonical_sha256(audited_subject)
        variants.append(variant)

    variants.sort(key=lambda row: (row["architecture"], row["spelling"], row["capability_id"]))
    report: dict[str, Any] = {
        "artifact_kind": "elementwise-intrinsic-audit-candidates",
        "schema_version": 2,
        "scope": "all-configured-exact-variants",
        "counts": {
            "registry_variants": len(variants),
            "used_variants": sum(row["used"] for row in variants),
            "conditioned_variants": sum(bool(row["architecture_conditions"]) for row in variants),
            "neon_variants": sum(row["architecture"] == "neon" for row in variants),
            "rvv_variants": sum(row["architecture"] == "rvv" for row in variants),
        },
        "sources": {
            "arm_acle": {
                "revision": ACLE_REVISION,
                "path": "tools/intrinsic_db/advsimd.csv",
                "sha256": acle_sha256,
            },
            "rvv_intrinsics": {
                "revision": RVV_REVISION,
                "prototype_path": "auto-generated/intrinsic_funcs.adoc",
                "prototype_sha256": rvv_prototype_sha256,
                "spec_path": "doc/rvv-intrinsic-spec.adoc",
                "spec_sha256": rvv_doc_sha256,
            },
            "riscv_isa": {
                "revision": RISCV_ISA_REVISION,
                "vector_path": vector_isa_relative,
                "vector_sha256": vector_isa_sha256,
                "scalar_fp_path": scalar_fp_relative,
                "scalar_fp_sha256": scalar_fp_sha256,
            },
        },
        "variants": variants,
    }
    report["audit_sha256"] = canonical_sha256(report)
    return report


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--acle-root", type=Path, required=True)
    parser.add_argument("--rvv-root", type=Path, required=True)
    parser.add_argument("--riscv-isa-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    report = build_intrinsic_audit(
        arguments.repository_root,
        acle_root=arguments.acle_root,
        rvv_root=arguments.rvv_root,
        riscv_isa_root=arguments.riscv_isa_root,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(canonical_json(report, pretty=True), encoding="utf-8")
    print(json.dumps(report["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
