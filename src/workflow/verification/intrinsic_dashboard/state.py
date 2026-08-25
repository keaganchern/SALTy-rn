"""Build the read-only state served by the intrinsic verification dashboard.

The dashboard combines three deliberately separate sources of evidence:

* exact call-shaped candidates in the 40 local ``kernels/source`` programs;
* matching candidates from the available local ``kernels/target`` programs;
* case-scoped mappings already configured in the restricted Lean backend.

None of those sources constitutes semantic approval.  Approval is carried only
from an independent, hash-bound :class:`AuditLedger` and becomes stale when the
descriptor or Lean implementation digest changes.
"""

from __future__ import annotations

import csv
import re
import subprocess
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from .activity import load_activity
from .authority import (
    DEFAULT_REVIEWER_REGISTRY_RELATIVE_PATH,
    ReviewerAuthorityError,
    TrustedReviewer,
    load_reviewer_registry,
    verify_bound_evidence,
)
from .audit import (
    build_kernel_file_status,
    file_sha256,
    load_ledger,
    reconcile_reviews,
)
from .freshness import (
    GENERATED_CASES,
    check_generated_models,
    generation_watch_digest,
)
from .model import (
    AuditLedger,
    ClaimScope,
    IntrinsicArchitecture,
    IntrinsicAudit,
    ProofCheckAttestation,
    canonical_sha256,
)
from .registry_status import collect_registry_implementations
from .scanner import (
    LEXICAL_METHOD,
    LexicalInventory,
    lexical_call_counts,
)
from .targets import PROOF_CASES


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
FAMILY_CATALOG_RELATIVE_PATH = Path("kernels/xnnpack-kernel-families.csv")
DEFAULT_REVIEW_LEDGER_RELATIVE_PATH = Path(
    "verification/intrinsic-dashboard/reviews.json"
)
DEFAULT_ACTIVITY_RELATIVE_PATH = Path(".intrinsic-dashboard/activity")

PROFILE = "local-lexical-candidate-v1"
REGISTRY_AUTHOR = "saltyrn-lean-backend"
MISSING_AUTHOR = "unassigned"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_OID_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_FAMILY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ALLOWED_FAMILY_TYPES = frozenset(
    {
        "convolution",
        "elementwise-binary",
        "elementwise-conversion",
        "elementwise-special",
        "elementwise-unary",
        "gemm",
        "interpolation",
        "pack",
        "pooling",
    }
)
_EXPECTED_FAMILY_TYPE_COUNTS: Mapping[str, int] = {
    "convolution": 8,
    "elementwise-binary": 13,
    "elementwise-conversion": 10,
    "elementwise-special": 2,
    "elementwise-unary": 34,
    "gemm": 24,
    "interpolation": 6,
    "pack": 4,
    "pooling": 6,
}

# These are explicit corpus relationships, not fuzzy name normalization.  The
# key is one of Keagan's 107 XNNPACK families and values are local program ids.
_FAMILY_PROGRAM_ALIASES: Mapping[str, tuple[str, ...]] = {
    "f32-dwconv": ("f32-dwconv-minmax",),
    "f32-gemm": ("f32-gemm-minmax",),
    "f32-igemm": ("f32-igemm-minmax",),
    "f32-spmm": ("f32-spmm-minmax",),
    "f32-vbinary": (
        "f32-vadd",
        "f32-vdiv",
        "f32-vmax",
        "f32-vmin",
        "f32-vmul",
        "f32-vmulc",
        "f32-vsub",
    ),
    "f32-vrnd": ("f32-vrndne",),
    "qd8-f32-qc4w-gemm": ("qd8-f32-qc4w-gemm-minmax",),
    "qd8-f32-qc8w-gemm": ("qd8-f32-qc8w-gemm-minmax",),
    "qd8-f32-qc8w-igemm": ("qd8-f32-qc8w-igemm-minmax",),
    "qs8-qc8w-gemm": ("qs8-qc8w-gemm-minmax-fp32",),
    "qs8-vadd": ("qs8-vadd-minmax",),
    "qs8-vmul": ("qs8-vmul-minmax-fp32",),
    "qu8-vadd": ("qu8-vadd-minmax",),
    "x32-packw": ("x32-packw-gemm-goi",),
}


class DashboardStateError(RuntimeError):
    """Dashboard inputs are malformed, inconsistent, or incomplete."""


def _validate_review_authority(
    repository_root: Path,
    ledger: AuditLedger,
    trusted_reviewers: Mapping[str, TrustedReviewer] | frozenset[str],
) -> None:
    reviews = [
        (item.review, item.author, item.review.checklist.evidence)
        for item in ledger.intrinsics
        if item.review is not None
    ] + [
        (item.final_review, item.author, item.final_review.evidence)
        for item in ledger.kernel_files
        if item.final_review is not None
    ]
    for review, author, evidence in reviews:
        if isinstance(trusted_reviewers, frozenset):
            trusted = review.reviewer in trusted_reviewers
        else:
            policy = trusted_reviewers.get(review.reviewer)
            trusted = policy is not None and policy.can_review(author)
        if not trusted:
            raise DashboardStateError(
                "audit ledger contains a reviewer absent from the tracked authority "
                f"or unauthorized for the author: {review.reviewer!r} for {author!r}"
            )
        try:
            verify_bound_evidence(repository_root, evidence)
        except ReviewerAuthorityError as error:
            raise DashboardStateError(str(error)) from error


def _trusted_reviewers(repository_root: Path) -> Mapping[str, TrustedReviewer]:
    try:
        reviewers = load_reviewer_registry(
            repository_root / DEFAULT_REVIEWER_REGISTRY_RELATIVE_PATH
        )
    except ReviewerAuthorityError as error:
        raise DashboardStateError(str(error)) from error
    return reviewers


@dataclass(frozen=True, slots=True)
class KernelFamily:
    name: str
    category: str


@dataclass(frozen=True, slots=True)
class _LocalProgram:
    program_id: str
    family: str
    source_path: str
    target_path: str | None
    neon_calls: tuple[tuple[str, int], ...]
    rvv_calls: tuple[tuple[str, int], ...]


def _is_relative_repository_path(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def load_kernel_families(path: Path) -> tuple[KernelFamily, ...]:
    """Read and strictly validate Keagan's 107-family catalog."""

    try:
        stream = path.open("r", encoding="ascii", newline="")
    except (OSError, UnicodeError) as error:
        raise DashboardStateError(
            f"cannot read kernel-family catalog {path}"
        ) from error
    try:
        with stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames != ["kernel", "type"]:
                raise DashboardStateError(
                    "kernel-family catalog header must be exactly 'kernel,type'"
                )
            rows: list[KernelFamily] = []
            for row in reader:
                if set(row) != {"kernel", "type"} or None in row:
                    raise DashboardStateError(
                        f"malformed kernel-family row at line {reader.line_num}"
                    )
                name = row["kernel"]
                category = row["type"]
                if (
                    name is None
                    or name != name.strip()
                    or _FAMILY_RE.fullmatch(name) is None
                ):
                    raise DashboardStateError(
                        f"invalid kernel family at line {reader.line_num}: {name!r}"
                    )
                if category is None or category != category.strip():
                    raise DashboardStateError(
                        f"invalid kernel type at line {reader.line_num}: {category!r}"
                    )
                if category not in _ALLOWED_FAMILY_TYPES:
                    raise DashboardStateError(
                        f"unknown kernel type at line {reader.line_num}: {category!r}"
                    )
                rows.append(KernelFamily(name=name, category=category))
    except (csv.Error, UnicodeError) as error:
        raise DashboardStateError(f"malformed kernel-family catalog {path}") from error

    if len(rows) != 107:
        raise DashboardStateError(
            f"kernel-family catalog must contain exactly 107 rows, found {len(rows)}"
        )
    names = [row.name for row in rows]
    if len(names) != len(set(names)):
        duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
        raise DashboardStateError(
            f"kernel-family catalog contains duplicate families: {duplicates}"
        )
    actual_types = {row.category for row in rows}
    if actual_types != _ALLOWED_FAMILY_TYPES:
        raise DashboardStateError(
            "kernel-family catalog type set changed: "
            f"missing={sorted(_ALLOWED_FAMILY_TYPES - actual_types)}, "
            f"extra={sorted(actual_types - _ALLOWED_FAMILY_TYPES)}"
        )
    actual_counts = Counter(row.category for row in rows)
    if dict(sorted(actual_counts.items())) != dict(
        sorted(_EXPECTED_FAMILY_TYPE_COUNTS.items())
    ):
        raise DashboardStateError(
            "kernel-family catalog type counts changed: "
            f"expected={dict(_EXPECTED_FAMILY_TYPE_COUNTS)}, "
            f"actual={dict(sorted(actual_counts.items()))}"
        )
    return tuple(rows)


def _local_family(program_id: str, family_names: frozenset[str]) -> str:
    if program_id in family_names:
        return program_id
    inverse: dict[str, str] = {}
    for family, program_ids in _FAMILY_PROGRAM_ALIASES.items():
        if family not in family_names:
            raise DashboardStateError(
                f"alias table references a family absent from the catalog: {family}"
            )
        for alias in program_ids:
            previous = inverse.setdefault(alias, family)
            if previous != family:
                raise DashboardStateError(
                    f"local program alias {alias} maps to multiple families"
                )
    return inverse.get(program_id, program_id)


def _read_local_calls(path: Path, architecture: str) -> tuple[tuple[str, int], ...]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise DashboardStateError(f"cannot read local C program {path}") from error
    try:
        counts = lexical_call_counts(architecture, source, path.as_posix())
    except Exception as error:
        raise DashboardStateError(f"cannot scan local C program {path}") from error
    return tuple(sorted(counts.items()))


def _scan_local_programs(
    repository_root: Path, family_names: frozenset[str]
) -> tuple[_LocalProgram, ...]:
    source_root = repository_root / "kernels" / "source"
    target_root = repository_root / "kernels" / "target"
    if not source_root.is_dir() or not target_root.is_dir():
        raise DashboardStateError("local kernels/source and kernels/target must exist")

    source_paths = tuple(sorted(source_root.glob("*.c")))
    target_paths = tuple(sorted(target_root.glob("*.c")))
    if not source_paths:
        raise DashboardStateError("local kernels/source contains no C programs")
    source_ids = {path.stem for path in source_paths}
    if len(source_ids) != len(source_paths):
        raise DashboardStateError("local source program ids are not unique")
    orphan_targets = sorted(
        path.name for path in target_paths if path.stem not in source_ids
    )
    if orphan_targets:
        raise DashboardStateError(
            f"local RVV targets have no matching Neon source: {orphan_targets}"
        )

    programs = []
    for source_path in source_paths:
        program_id = source_path.stem
        target_path = target_root / source_path.name
        source_relative = source_path.relative_to(repository_root).as_posix()
        target_relative = (
            target_path.relative_to(repository_root).as_posix()
            if target_path.is_file()
            else None
        )
        programs.append(
            _LocalProgram(
                program_id=program_id,
                family=_local_family(program_id, family_names),
                source_path=source_relative,
                target_path=target_relative,
                neon_calls=_read_local_calls(source_path, "neon"),
                rvv_calls=(
                    _read_local_calls(target_path, "rvv")
                    if target_relative is not None
                    else ()
                ),
            )
        )
    return tuple(programs)


def _git_provenance(repository_root: Path) -> tuple[str, bool, str]:
    try:
        head_result = subprocess.run(
            ("git", "-C", str(repository_root), "rev-parse", "HEAD"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        status_result = subprocess.run(
            (
                "git",
                "-C",
                str(repository_root),
                "status",
                "--porcelain=v1",
                "--untracked-files=normal",
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as error:
        raise DashboardStateError("cannot execute git for parent revision") from error
    try:
        head = head_result.stdout.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise DashboardStateError("parent git HEAD is not ASCII") from error
    if head_result.returncode != 0 or _GIT_OID_RE.fullmatch(head) is None:
        raise DashboardStateError("cannot determine a valid parent git HEAD")
    if status_result.returncode != 0:
        raise DashboardStateError("cannot determine parent git worktree status")
    status_sha256 = canonical_sha256({"porcelain_v1_hex": status_result.stdout.hex()})
    return head, bool(status_result.stdout), status_sha256


def _validate_inventory(
    inventory: LexicalInventory, family_names: frozenset[str]
) -> None:
    if inventory.method != LEXICAL_METHOD:
        raise DashboardStateError(
            f"unsupported XNNPACK scan method: {inventory.method!r}"
        )
    if _GIT_OID_RE.fullmatch(inventory.pinned_commit) is None:
        raise DashboardStateError("XNNPACK inventory has an invalid pinned commit")
    unknown = sorted(
        (
            {program.family for program in inventory.programs}
            | {u.family for u in inventory.usages}
        )
        - family_names
    )
    if unknown:
        raise DashboardStateError(
            f"XNNPACK inventory escaped the 107-family filter: {unknown}"
        )


def _validate_registry_record(key: str, record: Mapping[str, Any]) -> None:
    architecture = record.get("architecture")
    spelling = record.get("name")
    profile = record.get("profile")
    if (
        architecture not in {"neon", "rvv"}
        or not isinstance(spelling, str)
        or not spelling
        or not isinstance(profile, str)
        or _SHA256_RE.fullmatch(profile) is None
    ):
        raise DashboardStateError(f"invalid registry identity for {key!r}")
    if record.get("subject_id") != key or key != f"{architecture}:{spelling}@{profile}":
        raise DashboardStateError(f"registry key does not match its record: {key!r}")
    if record.get("variant_sha256") != profile or not isinstance(
        record.get("variant"), Mapping
    ):
        raise DashboardStateError(f"registry record {key!r} has invalid variant data")
    source_digest = record.get("source_sha256")
    semantics_digest = record.get("semantics_sha256")
    if (
        not isinstance(source_digest, str)
        or _SHA256_RE.fullmatch(source_digest) is None
        or not isinstance(semantics_digest, str)
        or _SHA256_RE.fullmatch(semantics_digest) is None
        or source_digest == semantics_digest
    ):
        raise DashboardStateError(
            f"registry record {key!r} needs independent descriptor and semantics hashes"
        )
    code = record.get("code")
    if (
        not isinstance(code, Sequence)
        or isinstance(code, (str, bytes))
        or not code
        or any(not _is_relative_repository_path(path) for path in code)
    ):
        raise DashboardStateError(f"registry record {key!r} has invalid code paths")
    signature = record.get("signature")
    if not isinstance(signature, str) or not signature:
        raise DashboardStateError(f"registry record {key!r} has invalid signature")
    supported_cases = record.get("supported_cases")
    if (
        not isinstance(supported_cases, Sequence)
        or isinstance(supported_cases, (str, bytes))
        or not supported_cases
        or any(not isinstance(case, str) or not case for case in supported_cases)
        or len(set(supported_cases)) != len(supported_cases)
    ):
        raise DashboardStateError(
            f"registry record {key!r} has invalid supported_cases"
        )
    descriptor_paths = record.get("descriptor_paths")
    if (
        not isinstance(descriptor_paths, Sequence)
        or isinstance(descriptor_paths, (str, bytes))
        or not descriptor_paths
        or any(not _is_relative_repository_path(path) for path in descriptor_paths)
    ):
        raise DashboardStateError(
            f"registry record {key!r} has invalid descriptor_paths"
        )
    tcb_files = record.get("tcb_files")
    if (
        not isinstance(tcb_files, Mapping)
        or not tcb_files
        or any(
            not _is_relative_repository_path(path)
            or not isinstance(digest, str)
            or _SHA256_RE.fullmatch(digest) is None
            for path, digest in tcb_files.items()
        )
    ):
        raise DashboardStateError(f"registry record {key!r} has invalid TCB files")


def _program_detail(
    *,
    name: str,
    path: str,
    origin: str,
    family: str,
    occurrences: int,
    production: bool | None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "name": name,
        "path": path,
        "origin": origin,
        "kernel_family": family,
        "occurrences": occurrences,
    }
    if production is not None:
        value["production"] = production
    return value


def _collect_local_usage(
    local_programs: Sequence[_LocalProgram],
) -> tuple[
    dict[tuple[str, str], list[dict[str, object]]],
    dict[tuple[str, str], set[str]],
]:
    """Collect only calls in the 40 local SALTyRN source/target programs."""

    programs: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    families: dict[tuple[str, str], set[str]] = defaultdict(set)

    for program in local_programs:
        for architecture, path, calls in (
            ("neon", program.source_path, program.neon_calls),
            ("rvv", program.target_path, program.rvv_calls),
        ):
            if path is None:
                continue
            for spelling, occurrences in calls:
                key = architecture, spelling
                programs[key].append(
                    _program_detail(
                        name=program.program_id,
                        path=path,
                        origin="saltyrn-local",
                        family=program.family,
                        occurrences=occurrences,
                        production=None,
                    )
                )
                families[key].add(program.family)

    for details in programs.values():
        details.sort(
            key=lambda item: (
                str(item["origin"]),
                str(item["path"]),
                str(item["name"]),
            )
        )
    return programs, families


def _make_intrinsics(
    *,
    registry_records: Mapping[str, Mapping[str, Any]],
    usage_programs: Mapping[tuple[str, str], Sequence[Mapping[str, object]]],
    usage_families: Mapping[tuple[str, str], set[str]],
) -> tuple[
    tuple[IntrinsicAudit, ...],
    dict[str, dict[str, object]],
]:
    for key, record in registry_records.items():
        _validate_registry_record(key, record)

    registry_by_identity: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(
        list
    )
    for record in registry_records.values():
        registry_by_identity[(str(record["architecture"]), str(record["name"]))].append(
            record
        )
    case_descriptors: dict[tuple[str, str, str], str] = {}
    for subject_id, record in registry_records.items():
        architecture_name = str(record["architecture"])
        spelling = str(record["name"])
        local_cases = {
            str(detail["name"])
            for detail in usage_programs.get((architecture_name, spelling), ())
        }
        supported_cases = tuple(str(case) for case in record["supported_cases"])
        missing_cases = sorted(set(supported_cases) - local_cases)
        if missing_cases:
            raise DashboardStateError(
                f"registry record {subject_id!r} is not used by its local cases: "
                f"{missing_cases}"
            )
        for case in supported_cases:
            case_key = architecture_name, spelling, case
            previous = case_descriptors.setdefault(case_key, subject_id)
            if previous != subject_id:
                raise DashboardStateError(
                    "multiple registry descriptors claim one local call: "
                    f"{case_key}: {previous!r}, {subject_id!r}"
                )

    # Registry entries unused by current local programs fail above and cannot
    # create standalone rows in this local translation view.
    identities = set(usage_programs)
    audits: list[IntrinsicAudit] = []
    projection_extras: dict[str, dict[str, object]] = {}
    for architecture_name, spelling in sorted(identities):
        architecture = IntrinsicArchitecture(architecture_name)
        records = sorted(
            registry_by_identity.get((architecture_name, spelling), ()),
            key=lambda item: str(item["subject_id"]),
        )
        details = tuple(usage_programs.get((architecture_name, spelling), ()))
        related_paths = tuple(sorted({str(detail["path"]) for detail in details}))
        related_families = tuple(
            sorted(usage_families.get((architecture_name, spelling), set()))
        )

        if not records:
            if not related_paths:
                raise DashboardStateError(
                    f"lexical intrinsic has no source path: {architecture_name}:{spelling}"
                )
            source_path = related_paths[0]
            source_sha256 = canonical_sha256(
                {
                    "architecture": architecture_name,
                    "spelling": spelling,
                    "profile": PROFILE,
                    "related_kernel_families": related_families,
                    "related_programs": related_paths,
                    "scan_method": LEXICAL_METHOD,
                    "scan_scope": "local-saltyrn-kernels-only",
                }
            )
            semantics_path = None
            semantics_sha256 = None
            author = MISSING_AUTHOR
            generated = False
            automated = False
            signatures: list[str] = []
            category = "lexical candidate"
            implementation_paths: list[str] = []
            supported_cases: list[str] = []
            audit = IntrinsicAudit(
                architecture=architecture,
                spelling=spelling,
                profile=PROFILE,
                source_path=source_path,
                source_sha256=source_sha256,
                semantics_path=semantics_path,
                semantics_sha256=semantics_sha256,
                author=author,
                generated=generated,
                automated=automated,
                related_kernel_families=related_families,
                related_programs=related_paths,
            )
            audits.append(audit)
            projection_extras[audit.subject_id] = {
                "signature": "Not available from lexical scan",
                "category": category,
                "implementation_paths": implementation_paths,
                "descriptor_paths": [source_path],
                "supported_cases": supported_cases,
                "variant": None,
                "lean_target": None,
                "lowering_operation": None,
                "adequacy_status": "not-established",
                "tcb_file_count": 0,
            }
            continue

        for record in records:
            code = sorted(str(path) for path in record["code"])
            descriptor_paths = sorted(str(path) for path in record["descriptor_paths"])
            audit = IntrinsicAudit(
                architecture=architecture,
                spelling=spelling,
                profile=str(record["profile"]),
                source_path=descriptor_paths[0],
                source_sha256=str(record["source_sha256"]),
                semantics_path=code[0],
                semantics_sha256=str(record["semantics_sha256"]),
                author=REGISTRY_AUTHOR,
                generated=True,
                automated=True,
                related_kernel_families=related_families,
                related_programs=related_paths,
            )
            audits.append(audit)
            projection_extras[audit.subject_id] = {
                "signature": str(record["signature"]),
                "category": str(record["kind"]),
                "implementation_paths": code,
                "descriptor_paths": descriptor_paths,
                "supported_cases": sorted(
                    str(value) for value in record["supported_cases"]
                ),
                "variant": record["variant"],
                "lean_target": record.get("lean_target"),
                "lowering_operation": record.get("lowering_operation"),
                "adequacy_status": str(record["adequacy_status"]),
                "tcb_file_count": len(record["tcb_files"]),
            }
    return tuple(audits), projection_extras


def _generated_artifact_status(repository_root: Path, program_id: str) -> tuple[
    dict[str, str] | None,
    dict[str, str] | None,
    dict[str, str] | None,
    dict[str, str] | None,
]:
    target = PROOF_CASES.get(program_id)
    if target is None:
        return None, None, None, None
    contract = repository_root / target.contract_path
    models = repository_root / target.models_path
    proof = repository_root / target.proof_path
    obligation = (
        None
        if target.obligation_path is None
        else repository_root / target.obligation_path
    )
    contract_record = (
        {
            "path": contract.relative_to(repository_root).as_posix(),
            "sha256": file_sha256(contract),
        }
        if contract.is_file()
        else None
    )
    models_record = (
        {
            "path": models.relative_to(repository_root).as_posix(),
            "sha256": file_sha256(models),
        }
        if models.is_file()
        else None
    )
    proof_record = (
        {
            "path": proof.relative_to(repository_root).as_posix(),
            "sha256": file_sha256(proof),
        }
        if proof.is_file()
        else None
    )
    obligation_record = (
        {
            "path": obligation.relative_to(repository_root).as_posix(),
            "sha256": file_sha256(obligation),
        }
        if obligation is not None and obligation.is_file()
        else None
    )
    return contract_record, models_record, proof_record, obligation_record


def _missing_local_dependency(
    *,
    repository_root: Path,
    program: _LocalProgram,
    architecture: IntrinsicArchitecture,
    spelling: str,
) -> IntrinsicAudit:
    relative_path = (
        program.source_path
        if architecture is IntrinsicArchitecture.NEON
        else program.target_path
    )
    if relative_path is None:
        raise DashboardStateError(
            f"cannot create an RVV dependency without a target: {program.program_id}"
        )
    source_digest = file_sha256(repository_root / relative_path)
    return IntrinsicAudit(
        architecture=architecture,
        spelling=spelling,
        profile=f"local-lexical-{program.program_id}-v1",
        source_path=relative_path,
        source_sha256=canonical_sha256(
            {
                "architecture": architecture.value,
                "spelling": spelling,
                "program_id": program.program_id,
                "program_sha256": source_digest,
                "scan_method": LEXICAL_METHOD,
            }
        ),
        semantics_path=None,
        semantics_sha256=None,
        author=MISSING_AUTHOR,
        generated=False,
        automated=False,
        related_kernel_families=(program.family,),
        related_programs=(relative_path,),
    )


def _kernel_dependencies(
    *,
    repository_root: Path,
    program: _LocalProgram,
    architecture: IntrinsicArchitecture,
    spelling: str,
    intrinsic_by_key: Mapping[tuple[str, str], Sequence[IntrinsicAudit]],
    registry_records: Mapping[str, Mapping[str, Any]],
) -> tuple[IntrinsicAudit, ...]:
    configured = tuple(
        intrinsic
        for intrinsic in intrinsic_by_key.get((architecture.value, spelling), ())
        if intrinsic.subject_id in registry_records
        and program.program_id
        in registry_records[intrinsic.subject_id]["supported_cases"]
    )
    if configured:
        return configured
    return (
        _missing_local_dependency(
            repository_root=repository_root,
            program=program,
            architecture=architecture,
            spelling=spelling,
        ),
    )


def _dependency_record(intrinsic: IntrinsicAudit) -> dict[str, object]:
    return {
        "subject_id": intrinsic.subject_id,
        "source_sha256": intrinsic.source_sha256,
        "semantics_sha256": intrinsic.semantics_sha256,
        "review_sha256": (
            None
            if intrinsic.review is None
            else canonical_sha256(intrinsic.review.to_dict())
        ),
    }


def _kernel_files(
    *,
    repository_root: Path,
    local_programs: Sequence[_LocalProgram],
    intrinsic_by_key: Mapping[tuple[str, str], Sequence[IntrinsicAudit]],
    registry_records: Mapping[str, Mapping[str, Any]],
    lean_checks: Mapping[str, ProofCheckAttestation],
    model_freshness: Mapping[str, bool],
    model_freshness_sha256: str | None,
) -> tuple[tuple[Any, ...], tuple[dict[str, object], ...]]:
    program_ids = {program.program_id for program in local_programs}
    unknown_checks = sorted(set(lean_checks) - program_ids)
    if unknown_checks:
        raise DashboardStateError(
            f"Lean-check evidence names unknown local programs: {unknown_checks}"
        )
    if any(
        not isinstance(value, ProofCheckAttestation) for value in lean_checks.values()
    ):
        raise DashboardStateError(
            "Lean-check evidence values must be proof-check attestations"
        )
    unknown_freshness = sorted(set(model_freshness) - set(GENERATED_CASES))
    if unknown_freshness:
        raise DashboardStateError(
            f"generated-model freshness names unknown cases: {unknown_freshness}"
        )
    if any(type(value) is not bool for value in model_freshness.values()):
        raise DashboardStateError("generated-model freshness values must be booleans")
    if any(model_freshness.values()) and (
        not isinstance(model_freshness_sha256, str)
        or _SHA256_RE.fullmatch(model_freshness_sha256) is None
    ):
        raise DashboardStateError(
            "fresh generated models require a producer/input/output binding digest"
        )

    statuses = []
    extras = []
    for program in local_programs:
        neon = tuple(
            intrinsic
            for spelling, _occurrences in program.neon_calls
            for intrinsic in _kernel_dependencies(
                repository_root=repository_root,
                program=program,
                architecture=IntrinsicArchitecture.NEON,
                spelling=spelling,
                intrinsic_by_key=intrinsic_by_key,
                registry_records=registry_records,
            )
        )
        rvv = tuple(
            intrinsic
            for spelling, _occurrences in program.rvv_calls
            for intrinsic in _kernel_dependencies(
                repository_root=repository_root,
                program=program,
                architecture=IntrinsicArchitecture.RVV,
                spelling=spelling,
                intrinsic_by_key=intrinsic_by_key,
                registry_records=registry_records,
            )
        )
        (
            contract_record,
            models_record,
            proof_record,
            obligation_record,
        ) = _generated_artifact_status(repository_root, program.program_id)
        target = PROOF_CASES.get(program.program_id)
        spec_generated = contract_record is not None and (
            target is None
            or target.obligation_path is None
            or obligation_record is not None
        )
        proof_generated = proof_record is not None
        generated_model_fresh = models_record is not None and model_freshness.get(
            program.program_id, False
        )
        proof_check = lean_checks.get(program.program_id)
        if proof_check is not None and not proof_generated:
            raise DashboardStateError(
                f"Lean-check evidence exists without a proof artifact: {program.program_id}"
            )
        if proof_check is not None and (
            target is None or proof_check.target != target.module
        ):
            raise DashboardStateError(
                f"Lean-check target does not match the configured proof module: "
                f"{program.program_id}"
            )
        claim_scope = (
            ClaimScope.LEXICAL_INVENTORY if target is None else target.claim_scope
        )
        source_record = {
            "path": program.source_path,
            "sha256": file_sha256(repository_root / program.source_path),
        }
        target_record = (
            {
                "path": program.target_path,
                "sha256": file_sha256(repository_root / program.target_path),
            }
            if program.target_path is not None
            else None
        )
        artifact_sha256 = canonical_sha256(
            {
                "schema": "kernel-file-artifact-binding-v3",
                "kernel_family": program.family,
                "program_id": program.program_id,
                "source": source_record,
                "target": target_record,
                "neon_dependencies": [
                    _dependency_record(intrinsic) for intrinsic in neon
                ],
                "rvv_dependencies": [
                    _dependency_record(intrinsic) for intrinsic in rvv
                ],
                "contract": contract_record,
                "obligation": obligation_record,
                "models": models_record,
                "generated_model_fresh": generated_model_fresh,
                "generated_model_freshness_sha256": (
                    model_freshness_sha256 if generated_model_fresh else None
                ),
                "proof": proof_record,
                "claim_scope": claim_scope.value,
                "proof_check_sha256": (
                    None if proof_check is None else proof_check.binding_sha256
                ),
            }
        )
        status = build_kernel_file_status(
            kernel_family=program.family,
            program_id=program.program_id,
            source_path=program.source_path,
            artifact_sha256=artifact_sha256,
            author=REGISTRY_AUTHOR,
            claim_scope=claim_scope,
            neon_intrinsics=neon,
            rvv_intrinsics=rvv,
            generated_model_fresh=generated_model_fresh,
            spec_generated=spec_generated,
            proof_generated=proof_generated,
            proof_check=proof_check,
        )
        statuses.append(status)
        extras.append(
            {
                "program_id": program.program_id,
                "target_path": program.target_path,
                "target_present": program.target_path is not None,
                "neon_mapping": {
                    "mapped": sum(item.generated and item.automated for item in neon),
                    "total": len(neon),
                },
                "rvv_mapping": {
                    "mapped": sum(item.generated and item.automated for item in rvv),
                    "total": len(rvv),
                },
                "artifact_binding": {
                    "source": source_record,
                    "target": target_record,
                    "contract": contract_record,
                    "obligation": obligation_record,
                    "models": models_record,
                    "generated_model_fresh": generated_model_fresh,
                    "generated_model_freshness_sha256": (
                        model_freshness_sha256 if generated_model_fresh else None
                    ),
                    "proof": proof_record,
                    "proof_check": (
                        None if proof_check is None else proof_check.to_dict()
                    ),
                    "neon_dependencies": [
                        _dependency_record(intrinsic) for intrinsic in neon
                    ],
                    "rvv_dependencies": [
                        _dependency_record(intrinsic) for intrinsic in rvv
                    ],
                },
            }
        )
    return tuple(statuses), tuple(extras)


def _project_intrinsics(
    ledger: AuditLedger,
    projection_extras: Mapping[str, Mapping[str, object]],
) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {"neon": [], "rvv": []}
    groups: dict[tuple[str, str], list[IntrinsicAudit]] = defaultdict(list)
    for intrinsic in ledger.intrinsics:
        groups[(intrinsic.architecture.value, intrinsic.spelling)].append(intrinsic)

    for (architecture, spelling), unsorted_variants in sorted(groups.items()):
        variants = sorted(unsorted_variants, key=lambda item: item.subject_id)
        summaries = []
        for intrinsic in variants:
            extra = projection_extras[intrinsic.subject_id]
            review = intrinsic.review
            summaries.append(
                {
                    "subject_id": intrinsic.subject_id,
                    "profile": intrinsic.profile,
                    "signature": extra["signature"],
                    "category": extra["category"],
                    "lean_target": extra["lean_target"] or "",
                    "lowering_operation": extra["lowering_operation"] or "",
                    "descriptor_paths": extra["descriptor_paths"],
                    "implementation_paths": extra["implementation_paths"],
                    "supported_cases": extra["supported_cases"],
                    "source_sha256": intrinsic.source_sha256,
                    "semantics_sha256": intrinsic.semantics_sha256,
                    "review_state": intrinsic.review_state.value,
                    "reviewer": None if review is None else review.reviewer,
                    "reviewed_at": None if review is None else review.reviewed_at,
                    "evidence": (
                        [] if review is None else list(review.checklist.evidence)
                    ),
                }
            )

        variant_count = len(variants)
        reviewed_variants = sum(item.status.reviewed for item in variants)
        stale_variants = sum(item.status.stale for item in variants)
        signatures = sorted(
            {str(projection_extras[item.subject_id]["signature"]) for item in variants}
        )
        categories = sorted(
            {str(projection_extras[item.subject_id]["category"]) for item in variants}
        )
        implementation_paths = sorted(
            {
                str(path)
                for item in variants
                for path in projection_extras[item.subject_id]["implementation_paths"]
            }
        )
        supported_cases = sorted(
            {
                str(case)
                for item in variants
                for case in projection_extras[item.subject_id]["supported_cases"]
            }
        )
        related_families = sorted(
            {family for item in variants for family in item.related_kernel_families}
        )
        related_programs = sorted(
            {program for item in variants for program in item.related_programs}
        )
        result[architecture].append(
            {
                "id": f"{architecture}:{spelling}",
                "architecture": architecture,
                "spelling": spelling,
                "variant_count": variant_count,
                "reviewed_variants": reviewed_variants,
                "stale_variants": stale_variants,
                "subject_ids": [item.subject_id for item in variants],
                "signatures": signatures,
                "signature": " | ".join(signatures),
                "category": " | ".join(categories),
                "implementation_paths": implementation_paths,
                "supported_cases": supported_cases,
                "coverage_scope": (
                    "lexical-candidate"
                    if all(not item.generated for item in variants)
                    else "case-scoped"
                ),
                "status": {
                    "generated": all(item.generated for item in variants),
                    "automated": all(item.automated for item in variants),
                    "reviewed": reviewed_variants == variant_count > 0,
                    "stale": stale_variants > 0,
                },
                "related_kernel_families": related_families,
                "variant_summaries": summaries,
                "related_programs": related_programs,
            }
        )
    return result


def _project_kernel_files(
    ledger: AuditLedger, extras: Sequence[Mapping[str, object]]
) -> list[dict[str, object]]:
    extras_by_program = {str(item["program_id"]): item for item in extras}
    rows = []
    for status in sorted(ledger.kernel_files, key=lambda item: item.program_id):
        row = status.to_dict()
        row["review_subject_sha256"] = status.review_subject_sha256
        row.update(extras_by_program[status.program_id])
        rows.append(row)
    return rows


def _metadata(
    *,
    families: Sequence[KernelFamily],
    local_programs: Sequence[_LocalProgram],
    registry_records: Mapping[str, Mapping[str, Any]],
    ledger: AuditLedger,
) -> dict[str, object]:
    local_occurrences = {
        "neon": sum(
            count for program in local_programs for _, count in program.neon_calls
        ),
        "rvv": sum(
            count for program in local_programs for _, count in program.rvv_calls
        ),
    }
    local_spellings = {
        "neon": len(
            {
                spelling
                for program in local_programs
                for spelling, _ in program.neon_calls
            }
        ),
        "rvv": len(
            {
                spelling
                for program in local_programs
                for spelling, _ in program.rvv_calls
            }
        ),
    }
    registry_architectures = Counter(
        str(record["architecture"]) for record in registry_records.values()
    )
    reviews = Counter(
        (
            "reviewed"
            if item.status.reviewed
            else "stale" if item.status.stale else "not-reviewed"
        )
        for item in ledger.intrinsics
    )
    missing_targets = [
        program.program_id for program in local_programs if program.target_path is None
    ]
    return {
        "scan_method": LEXICAL_METHOD,
        "scan_scope": (
            "Direct call-shaped tokens in the 40 local SALTyRN source kernels and "
            "their available RVV targets."
        ),
        "limitations": [
            "This is lexical candidate extraction, not a typed C or header-resolution pass.",
            "A call-shaped token is not evidence that the modeled Lean semantics matches ACLE or the RISC-V V specification.",
            "Registry presence is case-scoped translation support and is never reviewer approval.",
            "Proof-file presence is not a Lean-check result; checks must be injected explicitly.",
            "Selected-local-block and arbitrary-length-value claims are not complete-C-function or ISA correspondence claims.",
        ],
        "family_catalog": {
            "path": FAMILY_CATALOG_RELATIVE_PATH.as_posix(),
            "families": len(families),
            "types": len({family.category for family in families}),
        },
        "local": {
            "source_programs": len(local_programs),
            "paired_targets": sum(
                program.target_path is not None for program in local_programs
            ),
            "missing_targets": missing_targets,
            "candidate_occurrences": local_occurrences,
            "candidate_spellings": local_spellings,
        },
        "registry": {
            "variant_records": len(registry_records),
            "variants_by_architecture": dict(sorted(registry_architectures.items())),
            "spellings_by_architecture": {
                architecture: len(
                    {
                        str(record["name"])
                        for record in registry_records.values()
                        if record["architecture"] == architecture
                    }
                )
                for architecture in ("neon", "rvv")
            },
            "adequacy_status": "not-established",
        },
        "reviews": dict(sorted(reviews.items())),
    }


def build_current_ledger(
    repository_root: Path | str = REPOSITORY_ROOT,
    *,
    inventory: LexicalInventory | None = None,
    registry_records: Mapping[str, Mapping[str, Any]] | None = None,
    previous_ledger: AuditLedger | None = None,
    lean_checks: Mapping[str, ProofCheckAttestation] | None = None,
    model_freshness: Mapping[str, bool] | None = None,
    model_freshness_sha256: str | None = None,
    trusted_reviewer_ids: frozenset[str] | None = None,
    _families: Sequence[KernelFamily] | None = None,
) -> tuple[AuditLedger, dict[str, object]]:
    """Build current hash-bound records plus JSON projection metadata.

    The returned ``extras`` object contains ``revision``, ``metadata``,
    architecture-separated ``intrinsics`` projection rows, and projected
    ``kernel_files``.  The first return value remains the authoritative ledger
    suitable for review operations and atomic persistence.
    """

    root = Path(repository_root).resolve()
    current_model_freshness = dict(model_freshness or {})
    current_trusted_reviewers = (
        trusted_reviewer_ids
        if trusted_reviewer_ids is not None
        else _trusted_reviewers(root)
    )
    if previous_ledger is not None:
        _validate_review_authority(root, previous_ledger, current_trusted_reviewers)
    families = (
        tuple(_families)
        if _families is not None
        else load_kernel_families(root / FAMILY_CATALOG_RELATIVE_PATH)
    )
    family_names = frozenset(family.name for family in families)
    # The optional inventory is accepted only as a compatibility/reference
    # input. It is validated but never contributes live rows or dependencies.
    if inventory is not None:
        _validate_inventory(inventory, family_names)
    current_registry = (
        dict(registry_records)
        if registry_records is not None
        else collect_registry_implementations(root)
    )
    local_programs = _scan_local_programs(root, family_names)
    usage_programs, usage_families = _collect_local_usage(local_programs)
    intrinsics, intrinsic_extras = _make_intrinsics(
        registry_records=current_registry,
        usage_programs=usage_programs,
        usage_families=usage_families,
    )

    intrinsic_ledger = AuditLedger(intrinsics=intrinsics)
    if previous_ledger is not None:
        intrinsic_ledger = reconcile_reviews(intrinsic_ledger, previous_ledger)
    grouped_intrinsics: dict[tuple[str, str], list[IntrinsicAudit]] = defaultdict(list)
    for item in intrinsic_ledger.intrinsics:
        grouped_intrinsics[(item.architecture.value, item.spelling)].append(item)
    intrinsic_by_key = {
        key: tuple(sorted(items, key=lambda item: item.subject_id))
        for key, items in grouped_intrinsics.items()
    }
    kernel_files, kernel_extras = _kernel_files(
        repository_root=root,
        local_programs=local_programs,
        intrinsic_by_key=intrinsic_by_key,
        registry_records=current_registry,
        lean_checks=lean_checks or {},
        model_freshness=current_model_freshness,
        model_freshness_sha256=model_freshness_sha256,
    )
    ledger = AuditLedger(
        intrinsics=intrinsic_ledger.intrinsics,
        kernel_files=kernel_files,
    )
    if previous_ledger is not None:
        ledger = reconcile_reviews(ledger, previous_ledger)

    parent_head, worktree_dirty, worktree_status_sha256 = _git_provenance(root)
    metadata = _metadata(
        families=families,
        local_programs=local_programs,
        registry_records=current_registry,
        ledger=ledger,
    )
    metadata["repository"] = {
        "head": parent_head,
        "worktree_dirty": worktree_dirty,
        "worktree_status_sha256": worktree_status_sha256,
    }
    metadata["review_authority"] = {
        "path": DEFAULT_REVIEWER_REGISTRY_RELATIVE_PATH.as_posix(),
        "configured_reviewers": len(current_trusted_reviewers),
        "assurance": "tracked-policy-control-not-cryptographic-authentication",
    }
    metadata["generated_models"] = {
        "fresh": sum(
            current_model_freshness.get(case_id, False) for case_id in GENERATED_CASES
        ),
        "total": len(GENERATED_CASES),
        "method": "deterministic-in-memory-regeneration-and-byte-comparison",
        "binding_sha256": model_freshness_sha256,
    }
    extras: dict[str, object] = {
        "revision": (
            f"{parent_head[:8]}"
            f"{'+dirty.' + worktree_status_sha256[:8] if worktree_dirty else ''}"
        ),
        "parent_git_head": parent_head,
        "worktree_dirty": worktree_dirty,
        "worktree_status_sha256": worktree_status_sha256,
        "metadata": metadata,
        "intrinsics": _project_intrinsics(ledger, intrinsic_extras),
        "kernel_files": _project_kernel_files(ledger, kernel_extras),
    }
    return ledger, extras


def _utc_timestamp() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def build_dashboard_state(
    repository_root: Path | str = REPOSITORY_ROOT,
    *,
    inventory: LexicalInventory | None = None,
    registry_records: Mapping[str, Mapping[str, Any]] | None = None,
    previous_ledger: AuditLedger | None = None,
    review_ledger_path: Path | str | None = None,
    lean_checks: Mapping[str, ProofCheckAttestation] | None = None,
    model_freshness: Mapping[str, bool] | None = None,
    model_freshness_sha256: str | None = None,
    trusted_reviewer_ids: frozenset[str] | None = None,
    activity_directory: Path | str | None = None,
    _families: Sequence[KernelFamily] | None = None,
) -> dict[str, object]:
    """Return the complete JSON-serializable state consumed by the web UI."""

    root = Path(repository_root).resolve()
    if previous_ledger is not None and review_ledger_path is not None:
        raise DashboardStateError(
            "pass either previous_ledger or review_ledger_path, not both"
        )
    if previous_ledger is None:
        ledger_path = (
            Path(review_ledger_path)
            if review_ledger_path is not None
            else root / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH
        )
        if not ledger_path.is_absolute():
            ledger_path = root / ledger_path
        if ledger_path.exists():
            previous_ledger = load_ledger(ledger_path)

    ledger, extras = build_current_ledger(
        root,
        inventory=inventory,
        registry_records=registry_records,
        previous_ledger=previous_ledger,
        lean_checks=lean_checks,
        model_freshness=model_freshness,
        model_freshness_sha256=model_freshness_sha256,
        trusted_reviewer_ids=trusted_reviewer_ids,
        _families=_families,
    )
    activity_path = (
        Path(activity_directory)
        if activity_directory is not None
        else root / DEFAULT_ACTIVITY_RELATIVE_PATH
    )
    if not activity_path.is_absolute():
        activity_path = root / activity_path
    projected_intrinsics = extras["intrinsics"]
    assert isinstance(projected_intrinsics, dict)
    return {
        "schema_version": ledger.schema_version,
        "revision": extras["revision"],
        "generated_at": _utc_timestamp(),
        "agents": [record.to_dict() for record in load_activity(activity_path)],
        "metadata": extras["metadata"],
        "intrinsics": projected_intrinsics,
        "kernel_files": extras["kernel_files"],
    }


class DashboardStateProvider:
    """Rebuild local translation state while caching only stable catalog data.

    Registry mappings, local C programs, generated artifacts, review records,
    and agent activity are reread on every call. XNNPACK generated sources are
    deliberately outside this local 40-kernel dashboard.
    """

    def __init__(
        self,
        repository_root: Path | str = REPOSITORY_ROOT,
        *,
        inventory: LexicalInventory | None = None,
        review_ledger_path: Path | str | None = None,
        lean_checks: Mapping[str, ProofCheckAttestation] | None = None,
        activity_directory: Path | str | None = None,
        clang: str = "clang",
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.review_ledger_path = review_ledger_path
        self.lean_checks = dict(lean_checks or {})
        self.activity_directory = activity_directory
        self.clang = clang
        self._lock = threading.Lock()
        self._catalog_path = self.repository_root / FAMILY_CATALOG_RELATIVE_PATH
        self._families = load_kernel_families(self._catalog_path)
        self._catalog_sha256 = file_sha256(self._catalog_path)
        family_names = frozenset(family.name for family in self._families)
        self._reference_inventory = inventory
        if self._reference_inventory is not None:
            _validate_inventory(self._reference_inventory, family_names)
        self._generation_watch_sha256: str | None = None
        self._model_freshness: Mapping[str, bool] = {}
        self._refresh_model_freshness_if_needed()

    def _refresh_model_freshness_if_needed(self) -> None:
        try:
            current_digest = generation_watch_digest(
                self.repository_root, clang=self.clang
            )
            if current_digest == self._generation_watch_sha256:
                return
            checks = check_generated_models(self.repository_root, clang=self.clang)
            if (
                generation_watch_digest(self.repository_root, clang=self.clang)
                != current_digest
            ):
                raise RuntimeError(
                    "generated-model inputs changed during the freshness check"
                )
        except (OSError, UnicodeError, RuntimeError, ValueError):
            self._generation_watch_sha256 = None
            self._model_freshness = {}
            return
        self._generation_watch_sha256 = current_digest
        self._model_freshness = dict(checks)

    def _refresh_catalog_if_needed(self) -> None:
        catalog_sha256 = file_sha256(self._catalog_path)
        if catalog_sha256 == self._catalog_sha256:
            return
        families = load_kernel_families(self._catalog_path)
        family_names = frozenset(family.name for family in families)
        if self._reference_inventory is not None:
            _validate_inventory(self._reference_inventory, family_names)
        self._families = families
        self._catalog_sha256 = catalog_sha256

    def _previous_ledger(self) -> AuditLedger | None:
        path = (
            Path(self.review_ledger_path)
            if self.review_ledger_path is not None
            else self.repository_root / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH
        )
        if not path.is_absolute():
            path = self.repository_root / path
        return load_ledger(path) if path.exists() else None

    def current_ledger(self) -> AuditLedger:
        """Return authoritative current records without duplicating them in the API."""

        with self._lock:
            self._refresh_catalog_if_needed()
            self._refresh_model_freshness_if_needed()
            ledger, _extras = build_current_ledger(
                self.repository_root,
                inventory=self._reference_inventory,
                previous_ledger=self._previous_ledger(),
                lean_checks=self.lean_checks,
                model_freshness=self._model_freshness,
                model_freshness_sha256=self._generation_watch_sha256,
                _families=self._families,
            )
            return ledger

    def __call__(self) -> dict[str, object]:
        with self._lock:
            self._refresh_catalog_if_needed()
            self._refresh_model_freshness_if_needed()
            return build_dashboard_state(
                self.repository_root,
                inventory=self._reference_inventory,
                review_ledger_path=self.review_ledger_path,
                lean_checks=self.lean_checks,
                model_freshness=self._model_freshness,
                model_freshness_sha256=self._generation_watch_sha256,
                activity_directory=self.activity_directory,
                _families=self._families,
            )


def create_state_provider(
    repository_root: Path | str = REPOSITORY_ROOT,
    **kwargs: Any,
) -> DashboardStateProvider:
    """Create the cache-aware callable intended for the dashboard server."""

    return DashboardStateProvider(repository_root, **kwargs)
