"""Program-independent resolution of extracted calls to global capabilities."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from workflow.verification.lean_backend.descriptor import canonical_spec_digest
from workflow.verification.lean_backend.intrinsic_index import (
    CANONICAL_INTRINSIC_INDEX,
    CanonicalIntrinsicIndex,
    CanonicalIntrinsicVariant,
    IntrinsicMatchStatus,
    SourceIntrinsicDescriptor,
)
from workflow.verification.lean_backend.schema import (
    Architecture as BackendArchitecture,
    IntrinsicSpec,
    OperandTransform,
    ScheduleIntrinsic,
    SemanticIntrinsic,
    StructuralIntrinsic,
)

from .capabilities import IntrinsicCapability, IntrinsicRole
from .schema import Architecture, CapabilityRef, ElementwiseSchemaError


class IntrinsicResolutionError(ElementwiseSchemaError):
    """A source call has no single information-preserving global capability."""

    def __init__(self, status: str, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass(frozen=True, slots=True)
class ResolvedIntrinsicSet:
    capabilities: tuple[IntrinsicCapability, ...]
    neon_registry: Mapping[str, IntrinsicSpec]
    rvv_registry: Mapping[str, IntrinsicSpec]

    @property
    def refs(self) -> tuple[CapabilityRef, ...]:
        return tuple(
            sorted(
                (capability.ref for capability in self.capabilities),
                key=lambda item: (item.capability_id, item.version, item.sha256),
            )
        )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _architecture(value: BackendArchitecture) -> Architecture:
    return Architecture(value.value)


def _role(spec: IntrinsicSpec) -> IntrinsicRole:
    if isinstance(spec, SemanticIntrinsic):
        return IntrinsicRole.SEMANTIC
    if isinstance(spec, StructuralIntrinsic):
        return IntrinsicRole.STRUCTURAL
    if isinstance(spec, ScheduleIntrinsic):
        return IntrinsicRole.SCHEDULE
    raise IntrinsicResolutionError("intrinsic-missing", f"unsupported descriptor {type(spec)!r}")


def _information_score(variant: CanonicalIntrinsicVariant) -> tuple[int, ...]:
    """Rank only by how much exact source information the lowering preserves.

    A generic vector operation is preferred over a broadcast-specialized alias;
    an explicit rounding/shift operand is preferred over erasing that operand.
    This rule is independent of program names and descriptor provenance.  Equal
    scores remain ambiguous.
    """

    spec = variant.spec
    if isinstance(spec, SemanticIntrinsic):
        return (
            3,
            len(spec.lean_arguments),
            sum(
                argument.transform is OperandTransform.IDENTITY
                for argument in spec.lean_arguments
            ),
            -sum(
                constraint.erased_from_semantics
                for constraint in spec.immediate_constraints
            ),
            -len(spec.immediate_constraints),
        )
    if isinstance(spec, StructuralIntrinsic):
        return (2, 0, 0, 0, -len(spec.immediate_constraints))
    if isinstance(spec, ScheduleIntrinsic):
        return (1, 0, 0, 0, -len(spec.immediate_constraints))
    return (0, 0, 0, 0, 0)


def _select_variant(
    spelling: str,
    status: IntrinsicMatchStatus,
    variants: tuple[CanonicalIntrinsicVariant, ...],
) -> CanonicalIntrinsicVariant:
    if status in {IntrinsicMatchStatus.UNKNOWN, IntrinsicMatchStatus.SAME_NAME_MISMATCH}:
        failure = (
            "intrinsic-missing"
            if status is IntrinsicMatchStatus.UNKNOWN
            else "intrinsic-ambiguous"
        )
        raise IntrinsicResolutionError(
            failure,
            f"{spelling}: configured index returned {status.value}",
        )
    if not variants:
        raise IntrinsicResolutionError(
            "intrinsic-missing", f"{spelling}: no compatible configured descriptor"
        )
    if len(variants) == 1:
        return variants[0]
    best = max(_information_score(variant) for variant in variants)
    winners = tuple(
        variant for variant in variants if _information_score(variant) == best
    )
    if len(winners) != 1:
        raise IntrinsicResolutionError(
            "intrinsic-ambiguous",
            f"{spelling}: {len(winners)} equally information-preserving descriptors",
        )
    return winners[0]


def _implementation_digest(
    repository_root: Path,
    spec: IntrinsicSpec,
) -> str:
    if isinstance(spec, SemanticIntrinsic):
        relative = (
            "src/verification_bw/lean/SALT/Intrinsics/Neon.lean"
            if spec.architecture is BackendArchitecture.NEON
            else "src/verification_bw/lean/SALT/Intrinsics/RVV.lean"
        )
    elif isinstance(spec, ScheduleIntrinsic):
        relative = "src/verification_bw/lean/SALT/Kernel/Schedule.lean"
    else:
        relative = "src/workflow/verification/lean_backend/emit_lean.py"
    path = repository_root / relative
    if not path.is_file():
        raise IntrinsicResolutionError(
            "intrinsic-missing", f"capability implementation file is absent: {relative}"
        )
    return _file_sha256(path)


def _capability(
    repository_root: Path,
    source: SourceIntrinsicDescriptor,
    variant: CanonicalIntrinsicVariant,
) -> IntrinsicCapability:
    spec = variant.spec
    return IntrinsicCapability(
        architecture=_architecture(source.architecture),
        spelling=source.spelling,
        function_type=source.function_type,
        argument_count=source.argument_count,
        role=_role(spec),
        descriptor_sha256=canonical_spec_digest(spec),
        implementation_sha256=_implementation_digest(repository_root, spec),
        semantic_symbol=spec.lean_name if isinstance(spec, SemanticIntrinsic) else None,
    )


def resolve_intrinsics(
    neon: object,
    rvv: object,
    *,
    repository_root: str | Path,
    index: CanonicalIntrinsicIndex = CANONICAL_INTRINSIC_INDEX,
) -> ResolvedIntrinsicSet:
    """Resolve every extracted call group and return exact global registries."""

    root = Path(repository_root).resolve()
    capabilities: dict[str, IntrinsicCapability] = {}
    registries: dict[BackendArchitecture, dict[str, IntrinsicSpec]] = {
        BackendArchitecture.NEON: {},
        BackendArchitecture.RVV: {},
    }
    for extraction, architecture in (
        (neon, BackendArchitecture.NEON),
        (rvv, BackendArchitecture.RVV),
    ):
        try:
            calls: Iterable[object] = extraction.calls
        except AttributeError as error:
            raise IntrinsicResolutionError(
                "parse-unsupported", "intrinsic resolver needs frontend calls"
            ) from error
        groups: dict[tuple[object, ...], list[SourceIntrinsicDescriptor]] = defaultdict(list)
        for call in calls:
            descriptor = SourceIntrinsicDescriptor.from_extracted_call(architecture, call)
            groups[descriptor.source_key].append(descriptor)
        for source_key in sorted(groups, key=lambda item: tuple(str(part) for part in item)):
            group = tuple(groups[source_key])
            classification = index.classify_source_call_group(group)
            variant = _select_variant(
                group[0].spelling,
                classification.status,
                classification.variants,
            )
            capability = _capability(root, group[0], variant)
            previous = capabilities.setdefault(capability.capability_id, capability)
            if previous != capability:
                raise IntrinsicResolutionError(
                    "intrinsic-ambiguous",
                    f"{capability.capability_id}: source key resolved inconsistently",
                )
            registries[architecture][variant.spec.spelling] = variant.spec
    return ResolvedIntrinsicSet(
        tuple(sorted(capabilities.values(), key=lambda item: item.capability_id)),
        registries[BackendArchitecture.NEON],
        registries[BackendArchitecture.RVV],
    )
