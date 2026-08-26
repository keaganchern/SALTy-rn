from dataclasses import fields, replace
from random import Random

import pytest

from workflow.verification.lean_backend.intrinsic_index import (
    CANONICAL_INTRINSIC_INDEX,
    CanonicalIntrinsicIndex,
    DescriptorProvenance,
    IntrinsicIndexError,
    IntrinsicMatchStatus,
    IntrinsicOccurrence,
    SourceIntrinsicDescriptor,
    build_configured_intrinsic_index,
    canonical_spec_digest,
    canonical_spec_record,
)
from workflow.verification.lean_backend.registry import QS8_VADD_MINMAX_REGISTRY
from workflow.verification.lean_backend.scaleup_catalog import (
    QS8_VCVT_CATALOG,
)
from workflow.verification.lean_backend.schema import (
    Architecture,
    FunctionSignature,
    ImmediateConstraint,
    LeanArgument,
    Parameter,
    PointerType,
    ScalarType,
    ScheduleIntrinsic,
    SemanticIntrinsic,
    StructuralIntrinsic,
    VectorType,
    VoidType,
)


def _source(spec, *constants):
    return replace(
        SourceIntrinsicDescriptor.from_spec(spec),
        known_constants=tuple(constants),
    )


def test_configured_index_merges_equal_variants_and_preserves_provenance() -> None:
    index = build_configured_intrinsic_index()
    spec = QS8_VADD_MINMAX_REGISTRY["vqaddq_s16"]

    result = index.classify_configured_spec(spec)

    assert result.status is IntrinsicMatchStatus.EXACT_CONFIGURED
    assert result.configured_spec is spec
    assert {origin.case_id for origin in result.variants[0].provenance} == {
        "qs8-vadd-minmax",
        "qs8-vcvt",
        "qs8-vlrelu",
        "qu8-vadd-minmax",
    }
    assert {origin.source_catalog for origin in result.variants[0].provenance} == {
        "registry.QS8_VADD_MINMAX_SPECS",
        "scaleup_catalog.SCALEUP_CATALOGS['qs8-vcvt']",
        "scaleup_catalog.SCALEUP_CATALOGS['qs8-vlrelu']",
        "scaleup_catalog.SCALEUP_CATALOGS['qu8-vadd-minmax']",
    }


def test_configured_index_exposes_all_canonical_variants() -> None:
    assert len(CANONICAL_INTRINSIC_INDEX.variants) == 96
    assert (
        sum(len(variant.provenance) for variant in CANONICAL_INTRINSIC_INDEX.variants)
        == 161
    )


def test_same_source_call_with_multiple_lowerings_is_ambiguous() -> None:
    spec = QS8_VADD_MINMAX_REGISTRY["vmaxq_s8"]

    result = CANONICAL_INTRINSIC_INDEX.classify_source_call(_source(spec))

    assert result.status is IntrinsicMatchStatus.AMBIGUOUS
    assert len(result.variants) == 2


def test_known_constants_filter_candidates_without_claiming_exact_semantics() -> None:
    spec = QS8_VADD_MINMAX_REGISTRY["__riscv_vnclip_wx_i16m4"]

    result = CANONICAL_INTRINSIC_INDEX.classify_source_call(
        _source(spec, (1, 16), (2, 0))
    )

    assert result.status is IntrinsicMatchStatus.UNIQUE_CANDIDATE
    assert len(result.variants) == 1
    assert {origin.case_id for origin in result.variants[0].provenance} == {"qs8-vcvt"}
    assert not hasattr(result, "configured_spec")


def test_same_name_with_a_different_signature_is_not_a_candidate() -> None:
    spec = QS8_VADD_MINMAX_REGISTRY["vqaddq_s16"]
    mismatched = replace(
        _source(spec),
        function_type="int8_t (int8_t)",
        argument_count=1,
    )

    result = CANONICAL_INTRINSIC_INDEX.classify_source_call(mismatched)

    assert result.status is IntrinsicMatchStatus.SAME_NAME_MISMATCH
    assert result.variants


def test_same_spelling_for_the_wrong_architecture_is_unknown() -> None:
    spec = QS8_VADD_MINMAX_REGISTRY["vqaddq_s16"]
    wrong_architecture = replace(_source(spec), architecture=Architecture.RVV)

    result = CANONICAL_INTRINSIC_INDEX.classify_source_call(wrong_architecture)

    assert result.status is IntrinsicMatchStatus.UNKNOWN
    assert result.variants == ()


def test_unknown_spelling_has_no_fallback_candidates() -> None:
    spec = QS8_VADD_MINMAX_REGISTRY["vqaddq_s16"]
    unknown = replace(_source(spec), spelling="vqaddq_s16_unconfigured")

    result = CANONICAL_INTRINSIC_INDEX.classify_source_call(unknown)

    assert result.status is IntrinsicMatchStatus.UNKNOWN
    assert result.variants == ()


def test_unique_source_candidate_cannot_be_passed_to_configured_resolver() -> None:
    spec = QS8_VADD_MINMAX_REGISTRY["vqaddq_s16"]
    source = _source(spec)
    result = CANONICAL_INTRINSIC_INDEX.classify_source_call(source)

    assert result.status is IntrinsicMatchStatus.UNIQUE_CANDIDATE
    with pytest.raises(IntrinsicIndexError, match="unsupported intrinsic descriptor"):
        CANONICAL_INTRINSIC_INDEX.resolve_exact_configured(source)


def test_configured_resolver_requires_and_returns_a_complete_exact_record() -> None:
    spec = QS8_VADD_MINMAX_REGISTRY["vqaddq_s16"]

    assert CANONICAL_INTRINSIC_INDEX.resolve_exact_configured(spec) is spec

    changed = replace(spec, lean_name="SALT.Intrinsics.Neon.vsadd_vx")
    with pytest.raises(IntrinsicIndexError, match="same-name"):
        CANONICAL_INTRINSIC_INDEX.resolve_exact_configured(changed)


def test_incompatible_known_constants_do_not_select_a_lowering() -> None:
    spec = QS8_VADD_MINMAX_REGISTRY["__riscv_vnclip_wx_i16m4"]

    result = CANONICAL_INTRINSIC_INDEX.classify_source_call(
        _source(spec, (1, 16), (2, 2))
    )

    assert result.status is IntrinsicMatchStatus.SAME_NAME_MISMATCH


def test_known_constant_indices_must_be_sorted_and_unique() -> None:
    spec = QS8_VADD_MINMAX_REGISTRY["__riscv_vnclip_wx_i16m4"]

    with pytest.raises(IntrinsicIndexError, match="sorted and unique"):
        replace(
            SourceIntrinsicDescriptor.from_spec(spec),
            known_constants=((2, 0), (1, 16)),
        )


def test_complete_record_can_be_exact_even_when_source_call_is_ambiguous() -> None:
    spec = QS8_VADD_MINMAX_REGISTRY["vmaxq_s8"]

    raw = CANONICAL_INTRINSIC_INDEX.classify_source_call(_source(spec))
    configured = CANONICAL_INTRINSIC_INDEX.classify_configured_spec(spec)

    assert raw.status is IntrinsicMatchStatus.AMBIGUOUS
    assert configured.status is IntrinsicMatchStatus.EXACT_CONFIGURED
    assert configured.configured_spec is spec


def test_duplicate_catalog_location_is_rejected() -> None:
    spec = QS8_VCVT_CATALOG.registry["vsubw_s8"]
    provenance = DescriptorProvenance(
        "case", "test.catalog", spec.architecture, spec.spelling
    )
    occurrence = IntrinsicOccurrence(spec, provenance)

    with pytest.raises(IntrinsicIndexError, match="duplicate descriptor provenance"):
        CanonicalIntrinsicIndex.from_occurrences((occurrence, occurrence))


def test_provenance_must_match_its_descriptor() -> None:
    spec = QS8_VCVT_CATALOG.registry["vsubw_s8"]
    wrong = DescriptorProvenance(
        "case", "test.catalog", Architecture.RVV, spec.spelling
    )

    with pytest.raises(IntrinsicIndexError, match="architecture mismatch"):
        IntrinsicOccurrence(spec, wrong)


def test_complete_descriptor_differences_are_retained_as_distinct_variants() -> None:
    original = QS8_VCVT_CATALOG.registry["vsubw_s8"]
    changed = replace(original, lean_name="SALT.Intrinsics.Neon.vsubl_s8")
    first = DescriptorProvenance(
        "first", "test.catalog", original.architecture, original.spelling
    )
    second = DescriptorProvenance(
        "second", "test.catalog", changed.architecture, changed.spelling
    )
    index = CanonicalIntrinsicIndex.from_occurrences(
        (IntrinsicOccurrence(original, first), IntrinsicOccurrence(changed, second))
    )

    result = index.classify_source_call(_source(original))

    assert result.status is IntrinsicMatchStatus.AMBIGUOUS
    assert {variant.spec for variant in result.variants} == {original, changed}

    exact = index.classify_configured_spec(original)
    assert exact.status is IntrinsicMatchStatus.EXACT_CONFIGURED


def test_variant_order_is_independent_of_occurrence_order() -> None:
    occurrences = [
        IntrinsicOccurrence(variant.spec, origin)
        for variant in CANONICAL_INTRINSIC_INDEX.variants
        for origin in variant.provenance
    ]
    reversed_index = CanonicalIntrinsicIndex.from_occurrences(reversed(occurrences))
    Random(7).shuffle(occurrences)
    shuffled_index = CanonicalIntrinsicIndex.from_occurrences(occurrences)

    assert reversed_index.variants == CANONICAL_INTRINSIC_INDEX.variants
    assert shuffled_index.variants == CANONICAL_INTRINSIC_INDEX.variants


def test_canonical_record_and_digest_cover_complete_lowering_contract() -> None:
    original = QS8_VCVT_CATALOG.registry["vsubw_s8"]
    changed = replace(original, lean_name="SALT.Intrinsics.Neon.vsubl_s8")

    record = canonical_spec_record(original)

    assert record["architecture"] == "neon"
    assert record["signature"]["parameters"][0]["name"] == "wide"
    assert len(canonical_spec_digest(original)) == 64
    assert canonical_spec_digest(original) != canonical_spec_digest(changed)

    constrained = QS8_VADD_MINMAX_REGISTRY["__riscv_vnclip_wx_i16m4"]
    reordered = replace(
        constrained,
        immediate_constraints=tuple(reversed(constrained.immediate_constraints)),
    )
    assert canonical_spec_digest(constrained) == canonical_spec_digest(reordered)

    origins = (
        DescriptorProvenance(
            "first", "test.first", constrained.architecture, constrained.spelling
        ),
        DescriptorProvenance(
            "second", "test.second", reordered.architecture, reordered.spelling
        ),
    )
    forward = CanonicalIntrinsicIndex.from_occurrences(
        (
            IntrinsicOccurrence(constrained, origins[0]),
            IntrinsicOccurrence(reordered, origins[1]),
        )
    )
    backward = CanonicalIntrinsicIndex.from_occurrences(
        (
            IntrinsicOccurrence(reordered, origins[1]),
            IntrinsicOccurrence(constrained, origins[0]),
        )
    )
    assert len(forward.variants) == 1
    assert forward.variants == backward.variants


def test_extracted_source_call_uses_clang_type_and_constants_without_catalog() -> None:
    spec = QS8_VADD_MINMAX_REGISTRY["__riscv_vnclip_wx_i16m4"]
    source = SourceIntrinsicDescriptor(
        architecture=spec.architecture,
        spelling=spec.spelling,
        function_type="vint16m4_t (vint32m8_t, size_t, unsigned int, size_t)",
        argument_count=4,
        known_constants=((1, 16), (2, 0)),
    )

    result = CANONICAL_INTRINSIC_INDEX.classify_source_call(source)

    assert result.status is IntrinsicMatchStatus.UNIQUE_CANDIDATE
    assert {origin.case_id for origin in result.variants[0].provenance} == {"qs8-vcvt"}


def test_source_call_group_requires_one_variant_to_cover_every_occurrence() -> None:
    spec = QS8_VADD_MINMAX_REGISTRY["__riscv_vnclip_wx_i16m4"]
    base = SourceIntrinsicDescriptor.from_spec(spec)
    first = SourceIntrinsicDescriptor(
        base.architecture,
        base.spelling,
        base.function_type,
        base.argument_count,
        ((1, 16), (2, 0)),
    )
    second = SourceIntrinsicDescriptor(
        base.architecture,
        base.spelling,
        base.function_type,
        base.argument_count,
        ((1, 15), (2, 0)),
    )

    result = CANONICAL_INTRINSIC_INDEX.classify_source_call_group((first, second))

    assert result.status is IntrinsicMatchStatus.SAME_NAME_MISMATCH
    assert len(result.variants) == 4


def test_source_call_missing_a_required_immediate_is_not_a_unique_candidate() -> None:
    spec = QS8_VADD_MINMAX_REGISTRY["__riscv_vnclip_wx_i16m4"]
    source = SourceIntrinsicDescriptor.from_spec(spec)

    result = CANONICAL_INTRINSIC_INDEX.classify_source_call(source)

    assert result.status is IntrinsicMatchStatus.SAME_NAME_MISMATCH
    assert result.variants


def test_canonical_serializer_field_inventory_tracks_the_schema() -> None:
    def names(type_):
        return {field.name for field in fields(type_)}

    assert names(ScalarType) == {"c_spelling", "bit_width", "signedness"}
    assert names(VectorType) == {"c_spelling", "element", "fixed_lanes", "lmul"}
    assert names(PointerType) == {"pointee", "const"}
    assert names(VoidType) == {"c_spelling"}
    assert names(Parameter) == {"name", "type"}
    assert names(FunctionSignature) == {"parameters", "result"}
    assert names(ImmediateConstraint) == {
        "argument_index",
        "allowed_values",
        "erased_from_semantics",
    }
    assert names(LeanArgument) == {"source_index", "transform"}
    assert names(StructuralIntrinsic) == {
        "spelling",
        "architecture",
        "signature",
        "shape",
        "operation",
        "immediate_constraints",
    }
    assert names(SemanticIntrinsic) == {
        "spelling",
        "architecture",
        "signature",
        "shape",
        "lean_name",
        "lean_arguments",
        "immediate_constraints",
    }
    assert names(ScheduleIntrinsic) == {
        "spelling",
        "architecture",
        "signature",
        "shape",
        "operation",
        "immediate_constraints",
    }
