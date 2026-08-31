"""Canonical, provenance-preserving index of configured intrinsic descriptors.

A raw typed C call can identify compatible configured candidates, but it cannot
establish a semantic lowering.  Only equality with a complete
:class:`IntrinsicSpec` record is called ``exact-configured``.  Even that status
records configuration, not independent semantic review or approval.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from enum import Enum
from types import MappingProxyType

from .descriptor import (
    canonical_spec_digest,
    canonical_spec_json,
    canonical_spec_record,
)
from .intrinsic_library import ELEMENTWISE_SHARED_SPECS
from .registry import QS8_VADD_MINMAX_SPECS
from .scaleup_catalog import SCALEUP_CATALOGS
from .schema import (
    Architecture,
    ImmediateValue,
    IntrinsicSpec,
    ScheduleIntrinsic,
    SemanticIntrinsic,
    StructuralIntrinsic,
    render_clang_function_type,
)


_SPEC_TYPES = (StructuralIntrinsic, SemanticIntrinsic, ScheduleIntrinsic)


class IntrinsicIndexError(ValueError):
    """The configured descriptor inventory is inconsistent or cannot be resolved."""


class IntrinsicMatchStatus(str, Enum):
    """Configured-index result without implying semantic approval."""

    EXACT_CONFIGURED = "exact-configured"
    UNIQUE_CANDIDATE = "unique-candidate"
    SAME_NAME_MISMATCH = "same-name-mismatch"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"


def _normalized_spec(spec: IntrinsicSpec) -> IntrinsicSpec:
    constraints = tuple(
        sorted(
            spec.immediate_constraints,
            key=lambda constraint: constraint.argument_index,
        )
    )
    if constraints == spec.immediate_constraints:
        return spec
    return replace(spec, immediate_constraints=constraints)


@dataclass(frozen=True, slots=True, order=True)
class DescriptorProvenance:
    """One catalog occurrence of a configured descriptor."""

    case_id: str
    source_catalog: str
    architecture: Architecture
    spelling: str

    def __post_init__(self) -> None:
        if not self.case_id or self.case_id.strip() != self.case_id:
            raise IntrinsicIndexError("descriptor provenance needs an exact case id")
        if (
            not self.source_catalog
            or self.source_catalog.strip() != self.source_catalog
        ):
            raise IntrinsicIndexError("descriptor provenance needs a source catalog")
        if not isinstance(self.architecture, Architecture):
            raise IntrinsicIndexError("descriptor provenance needs an architecture")
        if not self.spelling or self.spelling.strip() != self.spelling:
            raise IntrinsicIndexError("descriptor provenance needs an exact spelling")


@dataclass(frozen=True, slots=True)
class IntrinsicOccurrence:
    """A complete descriptor together with its catalog location."""

    spec: IntrinsicSpec
    provenance: DescriptorProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.spec, _SPEC_TYPES):
            raise IntrinsicIndexError(
                f"unsupported intrinsic descriptor: {type(self.spec)!r}"
            )
        if self.provenance.architecture is not self.spec.architecture:
            raise IntrinsicIndexError("descriptor provenance architecture mismatch")
        if self.provenance.spelling != self.spec.spelling:
            raise IntrinsicIndexError("descriptor provenance spelling mismatch")


@dataclass(frozen=True, slots=True)
class SourceIntrinsicDescriptor:
    """Facts observable at one extracted C call, before semantic configuration."""

    architecture: Architecture
    spelling: str
    function_type: str
    argument_count: int
    known_constants: tuple[tuple[int, ImmediateValue], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.architecture, Architecture):
            raise IntrinsicIndexError("source descriptor needs an architecture")
        if not self.spelling or self.spelling.strip() != self.spelling:
            raise IntrinsicIndexError("source descriptor needs an exact spelling")
        if not self.function_type or self.function_type.strip() != self.function_type:
            raise IntrinsicIndexError("source descriptor needs an exact function type")
        if not isinstance(self.argument_count, int) or self.argument_count < 0:
            raise IntrinsicIndexError("source descriptor needs a non-negative arity")
        indices: list[int] = []
        for constant in self.known_constants:
            if not isinstance(constant, tuple) or len(constant) != 2:
                raise IntrinsicIndexError(
                    "each source constant must be an (argument index, value) pair"
                )
            index, value = constant
            if not isinstance(index, int) or not 0 <= index < self.argument_count:
                raise IntrinsicIndexError(
                    "source constant argument index is outside the call arity"
                )
            if not isinstance(value, (int, str)):
                raise IntrinsicIndexError(
                    "source constant values must be integers or exact symbols"
                )
            indices.append(index)
        if indices != sorted(set(indices)):
            raise IntrinsicIndexError(
                "source constant argument indices must be sorted and unique"
            )

    @classmethod
    def from_extracted_call(
        cls, architecture: Architecture, call: object
    ) -> SourceIntrinsicDescriptor:
        """Build source facts from an ``IntrinsicCall`` without consulting a catalog."""

        try:
            spelling = call.spelling
            function_type = call.callee_type
            arguments = call.arguments
        except AttributeError as error:
            raise IntrinsicIndexError("source call lacks extracted typed facts") from error
        constants = tuple(
            (index, argument.constant_value)
            for index, argument in enumerate(arguments)
            if argument.constant_value is not None
        )
        return cls(
            architecture=architecture,
            spelling=spelling,
            function_type=function_type,
            argument_count=len(arguments),
            known_constants=constants,
        )

    @classmethod
    def from_spec(cls, spec: IntrinsicSpec) -> SourceIntrinsicDescriptor:
        if not isinstance(spec, _SPEC_TYPES):
            raise IntrinsicIndexError(
                f"unsupported intrinsic descriptor: {type(spec)!r}"
            )
        return cls(
            architecture=spec.architecture,
            spelling=spec.spelling,
            function_type=render_clang_function_type(spec.signature),
            argument_count=len(spec.signature.parameters),
        )

    @property
    def source_key(self) -> tuple[Architecture, str, str, int]:
        return (
            self.architecture,
            self.spelling,
            self.function_type,
            self.argument_count,
        )


@dataclass(frozen=True, slots=True)
class CanonicalIntrinsicVariant:
    """One distinct complete lowering contract and every catalog that uses it."""

    spec: IntrinsicSpec
    provenance: tuple[DescriptorProvenance, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.spec, _SPEC_TYPES):
            raise IntrinsicIndexError(
                f"unsupported intrinsic descriptor: {type(self.spec)!r}"
            )
        if not self.provenance:
            raise IntrinsicIndexError("canonical variant needs provenance")
        if tuple(sorted(set(self.provenance))) != self.provenance:
            raise IntrinsicIndexError("canonical provenance must be sorted and unique")
        for origin in self.provenance:
            if origin.architecture is not self.spec.architecture:
                raise IntrinsicIndexError("canonical provenance architecture mismatch")
            if origin.spelling != self.spec.spelling:
                raise IntrinsicIndexError("canonical provenance spelling mismatch")


@dataclass(frozen=True, slots=True)
class SourceCallClassification:
    """Candidates compatible with every source call in one spelling group."""

    status: IntrinsicMatchStatus
    calls: tuple[SourceIntrinsicDescriptor, ...]
    variants: tuple[CanonicalIntrinsicVariant, ...]

    def __post_init__(self) -> None:
        if not self.calls:
            raise IntrinsicIndexError("source-call classification needs a call")
        first_key = self.calls[0].source_key
        if any(call.source_key != first_key for call in self.calls[1:]):
            raise IntrinsicIndexError(
                "one source-call group must share architecture, spelling, type, and arity"
            )
        allowed = {
            IntrinsicMatchStatus.UNIQUE_CANDIDATE,
            IntrinsicMatchStatus.SAME_NAME_MISMATCH,
            IntrinsicMatchStatus.UNKNOWN,
            IntrinsicMatchStatus.AMBIGUOUS,
        }
        if self.status not in allowed:
            raise IntrinsicIndexError(
                "source calls cannot establish exact-configured status"
            )
        expected_count = {
            IntrinsicMatchStatus.UNIQUE_CANDIDATE: lambda count: count == 1,
            IntrinsicMatchStatus.SAME_NAME_MISMATCH: lambda count: count >= 1,
            IntrinsicMatchStatus.UNKNOWN: lambda count: count == 0,
            IntrinsicMatchStatus.AMBIGUOUS: lambda count: count >= 2,
        }[self.status]
        if not expected_count(len(self.variants)):
            raise IntrinsicIndexError(
                f"invalid {self.status.value} source candidate count: "
                f"{len(self.variants)}"
            )


@dataclass(frozen=True, slots=True)
class ConfiguredSpecClassification:
    """Comparison of one complete descriptor with configured canonical records."""

    status: IntrinsicMatchStatus
    candidate: IntrinsicSpec
    variants: tuple[CanonicalIntrinsicVariant, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, _SPEC_TYPES):
            raise IntrinsicIndexError(
                f"unsupported intrinsic descriptor: {type(self.candidate)!r}"
            )
        if self.status is IntrinsicMatchStatus.UNIQUE_CANDIDATE:
            raise IntrinsicIndexError(
                "complete descriptors cannot have unique-candidate status"
            )
        if self.status is IntrinsicMatchStatus.AMBIGUOUS:
            raise IntrinsicIndexError(
                "complete descriptor equality cannot be ambiguous"
            )
        expected_count = {
            IntrinsicMatchStatus.EXACT_CONFIGURED: lambda count: count == 1,
            IntrinsicMatchStatus.SAME_NAME_MISMATCH: lambda count: count >= 1,
            IntrinsicMatchStatus.UNKNOWN: lambda count: count == 0,
        }[self.status]
        if not expected_count(len(self.variants)):
            raise IntrinsicIndexError(
                f"invalid {self.status.value} configured match count: "
                f"{len(self.variants)}"
            )
        if (
            self.status is IntrinsicMatchStatus.EXACT_CONFIGURED
            and canonical_spec_json(self.variants[0].spec)
            != canonical_spec_json(self.candidate)
        ):
            raise IntrinsicIndexError(
                "exact-configured status requires complete descriptor equality"
            )

    @property
    def configured_spec(self) -> IntrinsicSpec | None:
        if self.status is IntrinsicMatchStatus.EXACT_CONFIGURED:
            return self.variants[0].spec
        return None


@dataclass(frozen=True, slots=True)
class CanonicalIntrinsicIndex:
    """Immutable indexes over complete variants and extracted source-call facts."""

    variants: tuple[CanonicalIntrinsicVariant, ...]
    _by_spelling: Mapping[
        tuple[Architecture, str], tuple[CanonicalIntrinsicVariant, ...]
    ]
    _by_source: Mapping[
        tuple[Architecture, str, str, int], tuple[CanonicalIntrinsicVariant, ...]
    ]
    _by_canonical: Mapping[str, CanonicalIntrinsicVariant]

    @classmethod
    def from_occurrences(
        cls, occurrences: Iterable[IntrinsicOccurrence]
    ) -> CanonicalIntrinsicIndex:
        occurrence_list = tuple(occurrences)
        if not occurrence_list:
            raise IntrinsicIndexError("canonical intrinsic index cannot be empty")

        seen_locations: set[DescriptorProvenance] = set()
        grouped: dict[str, tuple[IntrinsicSpec, list[DescriptorProvenance]]] = {}
        for occurrence in occurrence_list:
            if not isinstance(occurrence, IntrinsicOccurrence):
                raise IntrinsicIndexError(
                    f"unsupported intrinsic occurrence: {type(occurrence)!r}"
                )
            if occurrence.provenance in seen_locations:
                raise IntrinsicIndexError(
                    f"duplicate descriptor provenance: {occurrence.provenance!r}"
                )
            seen_locations.add(occurrence.provenance)
            normalized = _normalized_spec(occurrence.spec)
            canonical = canonical_spec_json(normalized)
            existing = grouped.get(canonical)
            if existing is None:
                grouped[canonical] = (normalized, [occurrence.provenance])
            else:
                existing[1].append(occurrence.provenance)

        variants = tuple(
            sorted(
                (
                    CanonicalIntrinsicVariant(spec, tuple(sorted(origins)))
                    for spec, origins in grouped.values()
                ),
                key=lambda variant: (
                    canonical_spec_digest(variant.spec),
                    canonical_spec_json(variant.spec),
                ),
            )
        )
        by_spelling: dict[tuple[Architecture, str], list[CanonicalIntrinsicVariant]] = (
            defaultdict(list)
        )
        by_source: dict[
            tuple[Architecture, str, str, int], list[CanonicalIntrinsicVariant]
        ] = defaultdict(list)
        for variant in variants:
            by_spelling[(variant.spec.architecture, variant.spec.spelling)].append(
                variant
            )
            by_source[SourceIntrinsicDescriptor.from_spec(variant.spec).source_key].append(
                variant
            )

        return cls(
            variants=variants,
            _by_spelling=MappingProxyType(
                {key: tuple(group) for key, group in by_spelling.items()}
            ),
            _by_source=MappingProxyType(
                {descriptor: tuple(group) for descriptor, group in by_source.items()}
            ),
            _by_canonical=MappingProxyType(
                {canonical_spec_json(variant.spec): variant for variant in variants}
            ),
        )

    def classify_source_call(
        self, candidate: SourceIntrinsicDescriptor
    ) -> SourceCallClassification:
        return self.classify_source_call_group((candidate,))

    def classify_source_call_group(
        self, candidates: Iterable[SourceIntrinsicDescriptor]
    ) -> SourceCallClassification:
        """Find variants compatible with every occurrence in one source-call group."""

        calls = tuple(candidates)
        if not calls:
            raise IntrinsicIndexError("source-call classification needs a call")
        if any(not isinstance(call, SourceIntrinsicDescriptor) for call in calls):
            raise IntrinsicIndexError("source-call group contains unsupported facts")
        first_key = calls[0].source_key
        if any(call.source_key != first_key for call in calls[1:]):
            raise IntrinsicIndexError(
                "one source-call group must share architecture, spelling, type, and arity"
            )

        typed_variants = self._by_source.get(first_key, ())
        compatible = tuple(
            variant
            for variant in typed_variants
            if all(self._source_call_matches(variant.spec, call) for call in calls)
        )
        if len(compatible) == 1:
            status = IntrinsicMatchStatus.UNIQUE_CANDIDATE
            variants = compatible
        elif len(compatible) > 1:
            status = IntrinsicMatchStatus.AMBIGUOUS
            variants = compatible
        else:
            variants = self._by_spelling.get(
                (calls[0].architecture, calls[0].spelling), ()
            )
            status = (
                IntrinsicMatchStatus.SAME_NAME_MISMATCH
                if variants
                else IntrinsicMatchStatus.UNKNOWN
            )
        return SourceCallClassification(status, calls, variants)

    @staticmethod
    def _source_call_matches(
        spec: IntrinsicSpec, candidate: SourceIntrinsicDescriptor
    ) -> bool:
        constants = dict(candidate.known_constants)
        return all(
            constraint.argument_index in constants
            and constants[constraint.argument_index] in constraint.allowed_values
            for constraint in spec.immediate_constraints
        )

    def classify_configured_spec(
        self, candidate: IntrinsicSpec
    ) -> ConfiguredSpecClassification:
        """Compare every field of a complete descriptor with configured records."""

        if not isinstance(candidate, _SPEC_TYPES):
            raise IntrinsicIndexError(
                f"unsupported intrinsic descriptor: {type(candidate)!r}"
            )
        exact = self._by_canonical.get(canonical_spec_json(candidate))
        if exact is not None:
            return ConfiguredSpecClassification(
                IntrinsicMatchStatus.EXACT_CONFIGURED, candidate, (exact,)
            )

        same_name = self._by_spelling.get(
            (candidate.architecture, candidate.spelling), ()
        )
        return ConfiguredSpecClassification(
            (
                IntrinsicMatchStatus.SAME_NAME_MISMATCH
                if same_name
                else IntrinsicMatchStatus.UNKNOWN
            ),
            candidate,
            same_name,
        )

    def resolve_exact_configured(self, candidate: IntrinsicSpec) -> IntrinsicSpec:
        """Resolve only complete descriptor equality, never a raw typed call."""

        classification = self.classify_configured_spec(candidate)
        if classification.status is not IntrinsicMatchStatus.EXACT_CONFIGURED:
            raise IntrinsicIndexError(
                f"cannot resolve {candidate.architecture.value}:{candidate.spelling}: "
                f"{classification.status.value}"
            )
        spec = classification.configured_spec
        if spec is None:  # pragma: no cover - classification invariant
            raise AssertionError("exact-configured classification lost its descriptor")
        return spec


def configured_intrinsic_occurrences() -> tuple[IntrinsicOccurrence, ...]:
    """Return every case-scoped configured descriptor with its provenance."""

    occurrences: list[IntrinsicOccurrence] = []

    for spec in ELEMENTWISE_SHARED_SPECS:
        occurrences.append(
            IntrinsicOccurrence(
                spec,
                DescriptorProvenance(
                    case_id="elementwise-shared",
                    source_catalog="intrinsic_library.ELEMENTWISE_SHARED_SPECS",
                    architecture=spec.architecture,
                    spelling=spec.spelling,
                ),
            )
        )

    for spec in QS8_VADD_MINMAX_SPECS:
        occurrences.append(
            IntrinsicOccurrence(
                spec,
                DescriptorProvenance(
                    case_id="qs8-vadd-minmax",
                    source_catalog="registry.QS8_VADD_MINMAX_SPECS",
                    architecture=spec.architecture,
                    spelling=spec.spelling,
                ),
            )
        )

    for case_id, catalog in SCALEUP_CATALOGS.items():
        if case_id != catalog.kernel_name:
            raise IntrinsicIndexError(
                f"scale-up catalog key {case_id!r} does not match "
                f"{catalog.kernel_name!r}"
            )
        for spec in catalog.specs:
            occurrences.append(
                IntrinsicOccurrence(
                    spec,
                    DescriptorProvenance(
                        case_id=case_id,
                        source_catalog=f"scaleup_catalog.SCALEUP_CATALOGS[{case_id!r}]",
                        architecture=spec.architecture,
                        spelling=spec.spelling,
                    ),
                )
            )
    return tuple(occurrences)


def build_configured_intrinsic_index() -> CanonicalIntrinsicIndex:
    """Build the index from the base registry and every configured scale-up case."""

    return CanonicalIntrinsicIndex.from_occurrences(configured_intrinsic_occurrences())


CANONICAL_INTRINSIC_INDEX = build_configured_intrinsic_index()
