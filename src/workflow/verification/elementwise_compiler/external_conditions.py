"""Trace parameter facts that are not asserted inside an isolated kernel pair.

The extractor is intentionally conservative.  It binds the local pair to one
explicit XNNPACK registration file, verifies the pinned submodule commit, follows
the registration to its parameter initializer, and records every consulted file
by hash.  Finding a plausible condition is not enough to mark it resolved: the
extractor must also establish the caller path that guarantees it.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .schema import (
    BOOL,
    ContractExpr,
    ContractOp,
    ContractType,
    ContractTypeKind,
    EntryContract,
    EvidenceSource,
    ExternalConditionEvidence,
    ExternalConditionScope,
    ExternalConditionStatus,
    SourceArtifact,
    canonical_json,
    canonical_sha256,
)


class ExternalConditionError(RuntimeError):
    """External-condition evidence is absent, ambiguous, or stale."""


@dataclass(frozen=True, slots=True)
class ExternalConditionRequest:
    upstream_root: Path
    registration: Path


_MACRO = "XNN_UKERNEL("
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PARAM_DEREFERENCE = re.compile(r"\bparams\s*->")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_pair_sha256(sources: Sequence[SourceArtifact]) -> str:
    """Bind evidence to the exact parsed local source/facade pair."""

    return canonical_sha256([source.to_record() for source in sources])


def raw_source_pair_sha256(repository_root: Path, paths: Sequence[Path]) -> str:
    """A preflight identity used before a typed manifest can be built."""

    root = repository_root.resolve()
    return canonical_sha256(
        [
            {
                "path": path.resolve().relative_to(root).as_posix(),
                "sha256": _sha256(path.resolve()),
            }
            for path in paths
        ]
    )


def _relative(path: Path, root: Path, field: str) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise ExternalConditionError(f"{field} must be inside repository root: {path}") from error


def _git(*arguments: str, cwd: Path) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise ExternalConditionError(
            f"Git query failed in {cwd}: {completed.stderr.strip() or arguments!r}"
        )
    return completed.stdout.strip()


def _pinned_commit(repository_root: Path, upstream_root: Path) -> str:
    relative = _relative(upstream_root, repository_root, "upstream root")
    gitlink = _git("rev-parse", f"HEAD:{relative}", cwd=repository_root)
    checkout = _git("rev-parse", "HEAD", cwd=upstream_root)
    if gitlink != checkout:
        raise ExternalConditionError(
            f"upstream checkout {checkout} differs from pinned gitlink {gitlink}"
        )
    if re.fullmatch(r"[0-9a-f]{40}", checkout) is None:
        raise ExternalConditionError("upstream commit is not a full Git SHA-1")
    return checkout


def discover_request(
    repository_root: str | Path,
    local_source: str | Path,
    *,
    upstream_directory: str | Path = "benchmark/XNNPACK",
) -> ExternalConditionRequest | None:
    """Find a unique same-stem registration candidate without a case allowlist."""

    root = Path(repository_root).resolve()
    upstream = (root / upstream_directory).resolve()
    if not upstream.is_dir():
        return None
    stem = Path(local_source).stem
    candidates = tuple(sorted((upstream / "src").rglob(f"{stem}.inc")))
    if len(candidates) != 1:
        return None
    return ExternalConditionRequest(upstream, candidates[0])


def _split_macro_arguments(line: str) -> tuple[str, ...]:
    start = line.find(_MACRO)
    if start < 0:
        raise ExternalConditionError("registration line has no XNN_UKERNEL macro")
    text = line[start + len(_MACRO) :]
    depth = 0
    parts: list[str] = []
    current: list[str] = []
    for character in text:
        if character == "(" :
            depth += 1
            current.append(character)
        elif character == ")":
            if depth == 0:
                parts.append("".join(current).strip())
                break
            depth -= 1
            current.append(character)
        elif character == "," and depth == 0:
            parts.append("".join(current).strip())
            current.clear()
        else:
            current.append(character)
    if len(parts) < 6 or any(not part for part in parts):
        raise ExternalConditionError(f"malformed XNN_UKERNEL registration: {line.strip()}")
    return tuple(parts)


def _registration_binding(path: Path) -> tuple[str, str, tuple[str, ...]]:
    records = [
        _split_macro_arguments(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if _MACRO in line
    ]
    neon = [
        record
        for record in records
        if "neon" in record[0].lower() or "neon" in record[1].lower()
    ]
    rvv = [record for record in records if "__rvv" in record[1]]
    if not neon or not rvv:
        raise ExternalConditionError("registration must contain both Neon and RVV kernels")
    neon_bindings = {(record[-2], record[-1]) for record in neon}
    rvv_bindings = {(record[-2], record[-1]) for record in rvv}
    shared = sorted(neon_bindings & rvv_bindings)
    if len(shared) != 1:
        raise ExternalConditionError(
            "Neon/RVV registrations do not have one common parameter initializer"
        )
    parameter_type, initializer = shared[0]
    symbols = tuple(sorted({record[1] for record in (*neon, *rvv)}))
    return parameter_type, initializer, symbols


def _balanced_function(text: str, symbol: str) -> str:
    match = re.search(rf"\b{re.escape(symbol)}\s*\([^;]*?\)\s*\{{", text, re.DOTALL)
    if match is None:
        raise ExternalConditionError(f"could not locate definition of {symbol}")
    opening = text.find("{", match.start())
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : index + 1]
    raise ExternalConditionError(f"unterminated definition of {symbol}")


def _definition_file(upstream: Path, symbol: str) -> tuple[Path, str]:
    matches: list[tuple[Path, str]] = []
    pattern = re.compile(rf"\b{re.escape(symbol)}\s*\(")
    for path in sorted((upstream / "src").rglob("*")):
        if path.suffix not in {".c", ".h"} or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="strict")
        if pattern.search(text) is None:
            continue
        try:
            body = _balanced_function(text, symbol)
        except ExternalConditionError:
            continue
        matches.append((path, body))
    if len(matches) != 1:
        raise ExternalConditionError(
            f"expected one definition of {symbol}, found {len(matches)}"
        )
    return matches[0]


def _source(
    path: Path,
    repository_root: Path,
    role: str,
    symbols: Iterable[str],
) -> EvidenceSource:
    return EvidenceSource(
        role,
        _relative(path, repository_root, "evidence file"),
        _sha256(path),
        tuple(sorted(set(symbols))),
    )


def _direct_unconstrained_copy(body: str) -> bool:
    """Recognize a scalar field copied directly from unary operator parameters."""

    statements = body[body.find("{") + 1 :]
    if (
        "assert(" in statements
        or "input_quantization" in statements
        or "output_quantization" in statements
    ):
        return False
    assignments = re.findall(
        r"params->[^=;]+\s*=\s*op_params->[A-Za-z0-9_.]+\s*;", statements
    )
    remaining = re.sub(r"\s+", " ", statements)
    return bool(assignments) and "params->" in remaining


def _clamp_candidate(
    body: str,
    upstream: Path,
    repository_root: Path,
) -> tuple[EntryContract, tuple[EvidenceSource, ...], str] | None:
    assignments = {}
    pattern = re.compile(
        r"params->(?P<target>[A-Za-z0-9_.]+)\s*=\s*"
        r"(?P<helper>[A-Za-z_][A-Za-z0-9_]*)\("
        r"op_params->clamp\.(?P<field>min|max)\s*,"
    )
    for match in pattern.finditer(body):
        assignments[match.group("field")] = (
            match.group("target"), match.group("helper")
        )
    if set(assignments) != {"min", "max"}:
        return None
    if assignments["min"][1] != assignments["max"][1]:
        return None
    helper = assignments["min"][1]
    helper_path, _ = _definition_file(upstream, helper)
    helper_text = helper_path.read_text(encoding="utf-8")
    signature = re.search(
        rf"\b(?P<type>u?int(?:8|16|32)_t)\s+{re.escape(helper)}\s*\(", helper_text
    )
    if signature is None:
        return None
    spelling = signature.group("type")
    width_match = re.search(r"(8|16|32)", spelling)
    assert width_match is not None
    value_type = ContractType(
        ContractTypeKind.INTEGER,
        spelling,
        int(width_match.group(1)),
        not spelling.startswith("u"),
    )
    minimum = ContractExpr.variable("params.min", value_type)
    maximum = ContractExpr.variable("params.max", value_type)
    condition = ContractExpr.make(ContractOp.LE, minimum, maximum, result_type=BOOL)
    source = _source(helper_path, repository_root, "quantization-helper", (helper,))
    return (
        EntryContract.normalized((condition,)),
        (source,),
        "initializer applies the same quantizer to clamp.min and clamp.max; "
        "caller guarantees for input order and positive scale remain unresolved",
    )


def _extractor_sha256() -> str:
    return _sha256(Path(__file__).resolve())


def audit_local_unconditional_claim(
    repository_root: str | Path,
    local_sources: Sequence[str | Path],
    source_binding_sha256: str,
    functions: Sequence[str],
) -> ExternalConditionEvidence:
    """Record that a standalone compilation assumes no hidden caller condition.

    This scope does not claim that the generated theorem is true.  It fixes the
    theorem domain to all modeled parameter values; proof or counterexample
    checking must still establish the generated claim.
    """

    if len(local_sources) != 2 or len(functions) != 2:
        raise ExternalConditionError(
            "local unconditional audit needs exactly two sources and functions"
        )
    root = Path(repository_root).resolve()
    roles = ("local-neon-kernel", "local-rvv-kernel")
    sources = tuple(
        sorted(
            (
                EvidenceSource(
                    role=role,
                    path=_relative(Path(path), root, "local kernel"),
                    sha256=_sha256(Path(path).resolve()),
                    symbols=(function,),
                )
                for role, path, function in zip(
                    roles, local_sources, functions, strict=True
                )
            ),
            key=lambda source: canonical_json(source.to_record()),
        )
    )
    return ExternalConditionEvidence(
        local_sources_sha256=source_binding_sha256,
        scope=ExternalConditionScope.LOCAL_UNCONDITIONAL,
        upstream_root=None,
        upstream_commit=None,
        parameter_type="generated-parameter-domain",
        initializer="none",
        status=ExternalConditionStatus.NOT_REQUIRED,
        candidate_contract=EntryContract.normalized(()),
        sources=sources,
        extractor_sha256=_extractor_sha256(),
        derivation="unconditional-generated-claim-v1",
        detail=(
            "standalone generated claim assumes no caller restriction and quantifies "
            "over every modeled parameter value"
        ),
    )


def audit_external_condition(
    repository_root: str | Path,
    local_sources: Sequence[str | Path],
    source_binding_sha256: str,
    request: ExternalConditionRequest,
) -> ExternalConditionEvidence:
    """Produce conservative, content-addressed evidence for one local pair."""

    root = Path(repository_root).resolve()
    upstream = request.upstream_root.resolve()
    registration = request.registration.resolve()
    if not registration.is_file():
        raise ExternalConditionError(f"registration file is absent: {registration}")
    _relative(registration, upstream, "registration")
    commit = _pinned_commit(root, upstream)
    parameter_type, initializer, kernel_symbols = _registration_binding(registration)
    sources = [
        _source(registration, root, "kernel-registration", kernel_symbols)
    ]
    local_text = "\n".join(
        Path(path).read_text(encoding="utf-8") for path in local_sources
    )
    semantic_params = _PARAM_DEREFERENCE.search(local_text) is not None
    candidate = EntryContract.normalized(())
    derivation = "local-kernel-parameter-use-v1"
    if not semantic_params or initializer in {"nullptr", "NULL"}:
        status = ExternalConditionStatus.NOT_REQUIRED
        detail = "local kernels do not read semantic parameter fields"
    else:
        if _IDENTIFIER.fullmatch(initializer) is None:
            raise ExternalConditionError(f"invalid initializer symbol {initializer!r}")
        initializer_path, body = _definition_file(upstream, initializer)
        sources.append(
            _source(initializer_path, root, "parameter-initializer", (initializer,))
        )
        if _direct_unconstrained_copy(body):
            status = ExternalConditionStatus.NOT_REQUIRED
            detail = "initializer directly copies an unconstrained unary scalar parameter"
            derivation = "direct-unary-parameter-copy-v1"
        else:
            status = ExternalConditionStatus.REQUIRED_MISSING
            detail = (
                "initializer transforms or validates semantic parameters, but no complete "
                "caller-to-kernel guarantee has been established"
            )
            clamp = _clamp_candidate(body, upstream, root)
            if clamp is not None:
                candidate, helper_sources, clamp_detail = clamp
                sources.extend(helper_sources)
                derivation = "ordered-clamp-candidate-with-unresolved-caller-v1"
                detail = clamp_detail
    ordered_sources = tuple(
        sorted(sources, key=lambda source: canonical_json(source.to_record()))
    )
    return ExternalConditionEvidence(
        local_sources_sha256=source_binding_sha256,
        scope=ExternalConditionScope.XNNPACK_REGISTERED,
        upstream_root=_relative(upstream, root, "upstream root"),
        upstream_commit=commit,
        parameter_type=parameter_type,
        initializer=initializer,
        status=status,
        candidate_contract=candidate,
        sources=ordered_sources,
        extractor_sha256=_extractor_sha256(),
        derivation=derivation,
        detail=detail,
    )


def verify_external_condition(
    repository_root: str | Path,
    local_sources: Sequence[str | Path],
    source_binding_sha256: str,
    evidence: ExternalConditionEvidence,
) -> None:
    """Re-extract evidence and require byte-for-byte semantic identity."""

    root = Path(repository_root).resolve()
    if evidence.local_sources_sha256 != source_binding_sha256:
        raise ExternalConditionError(
            "external-condition evidence local-source binding is stale"
        )
    if evidence.scope is ExternalConditionScope.LOCAL_UNCONDITIONAL:
        local_records = {
            source.role: source
            for source in evidence.sources
            if source.role in {"local-neon-kernel", "local-rvv-kernel"}
        }
        if set(local_records) != {"local-neon-kernel", "local-rvv-kernel"}:
            raise ExternalConditionError(
                "local unconditional evidence must bind both kernel sources"
            )
        regenerated = audit_local_unconditional_claim(
            root,
            local_sources,
            source_binding_sha256,
            (
                local_records["local-neon-kernel"].symbols[0],
                local_records["local-rvv-kernel"].symbols[0],
            ),
        )
        if regenerated.to_record() != evidence.to_record():
            raise ExternalConditionError(
                "external-condition evidence is stale or was not reproduced"
            )
        return
    registrations = [source for source in evidence.sources if source.role == "kernel-registration"]
    if len(registrations) != 1:
        raise ExternalConditionError("evidence must bind exactly one registration file")
    request = ExternalConditionRequest(
        (root / evidence.upstream_root).resolve(),
        (root / registrations[0].path).resolve(),
    )
    regenerated = audit_external_condition(
        root, local_sources, source_binding_sha256, request
    )
    if regenerated.to_record() != evidence.to_record():
        raise ExternalConditionError("external-condition evidence is stale or was not reproduced")
