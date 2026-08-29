"""Golden inventory checks for the five configured integer kernel catalogs.

The three inventory levels are intentionally distinct:

* an occurrence is one descriptor slot in one kernel catalog;
* an ``(architecture, spelling)`` key identifies a source token namespace;
* an exact variant is one complete lowering contract, including its typed
  signature, immediates, operation, and ordered Lean arguments.

The onboarding oracle compares each catalog only with catalogs that precede it.
It is an audit of deterministic reuse opportunities, not a semantic review or an
approval mechanism.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

from workflow.verification.lean_backend.intrinsic_index import (
    CANONICAL_INTRINSIC_INDEX,
)
from workflow.verification.lean_backend.intrinsic_library import (
    render_elementwise_shared_facade,
)
from workflow.verification.lean_backend.registry import QS8_VADD_MINMAX_SPECS
from workflow.verification.lean_backend.scaleup_catalog import SCALEUP_CATALOGS
from workflow.verification.lean_backend.schema import Architecture, IntrinsicSpec


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

EXPECTED_CONFLICT_VARIANTS = {
    (Architecture.NEON, "vmax_s8"): 2,
    (Architecture.NEON, "vmaxq_s8"): 2,
    (Architecture.NEON, "vmin_s8"): 2,
    (Architecture.NEON, "vminq_s8"): 2,
    (Architecture.NEON, "vrshlq_s32"): 2,
    (Architecture.RVV, "__riscv_vnclip_wx_i16m4"): 4,
    (Architecture.RVV, "__riscv_vnclip_wx_i8m2"): 2,
    (Architecture.RVV, "__riscv_vsll_vx_i32m8"): 2,
    (Architecture.RVV, "__riscv_vssra_vx_i32m8"): 2,
}

EXPECTED_SEQUENTIAL_ONBOARDING = {
    "qs8-vadd-minmax": (0, 0, 43),
    "s8-vclamp": (11, 4, 6),
    "qs8-vcvt": (15, 2, 8),
    "qs8-vlrelu": (22, 1, 7),
    "qu8-vadd-minmax": (17, 4, 21),
}


def _variants_by_architecture_and_spelling():
    grouped = defaultdict(list)
    for variant in CANONICAL_INTRINSIC_INDEX.variants:
        grouped[(variant.spec.architecture, variant.spec.spelling)].append(variant)
    return grouped


def _onboarding_status(
    spec: IntrinsicSpec,
    prior_specs: set[IntrinsicSpec],
    prior_keys: set[tuple[Architecture, str]],
) -> str:
    if spec in prior_specs:
        return "exact"
    if (spec.architecture, spec.spelling) in prior_keys:
        return "same-name-conflict"
    return "unknown"


def test_configured_inventory_counts_and_architecture_split_are_stable() -> None:
    variants = CANONICAL_INTRINSIC_INDEX.variants
    grouped = _variants_by_architecture_and_spelling()

    assert sum(len(variant.provenance) for variant in variants) == 170
    assert len(grouped) == 94
    assert len(variants) == 105

    assert Counter(
        origin.architecture
        for variant in variants
        for origin in variant.provenance
    ) == Counter({Architecture.NEON: 108, Architecture.RVV: 62})
    assert Counter(architecture for architecture, _ in grouped) == Counter(
        {Architecture.NEON: 55, Architecture.RVV: 39}
    )
    assert Counter(variant.spec.architecture for variant in variants) == Counter(
        {Architecture.NEON: 60, Architecture.RVV: 45}
    )


def test_exactly_nine_architecture_scoped_keys_have_multiple_variants() -> None:
    grouped = _variants_by_architecture_and_spelling()
    conflicts = {
        key: len(variants) for key, variants in grouped.items() if len(variants) > 1
    }

    assert conflicts == EXPECTED_CONFLICT_VARIANTS


def test_exact_variant_case_support_distribution_is_stable() -> None:
    support_counts = Counter(
        len({origin.case_id for origin in variant.provenance})
        for variant in CANONICAL_INTRINSIC_INDEX.variants
    )

    assert support_counts == Counter({1: 69, 2: 21, 3: 3, 4: 10, 5: 2})


def test_shared_parse_facade_is_generated_from_the_typed_library() -> None:
    facade = (
        Path(__file__).resolve().parents[3]
        / "src/workflow/verification/lean_backend/facade/elementwise_shared.h"
    )
    assert facade.read_text(encoding="utf-8") == render_elementwise_shared_facade()


def test_sequential_onboarding_uses_only_prior_complete_descriptors() -> None:
    catalogs = (
        ("qs8-vadd-minmax", QS8_VADD_MINMAX_SPECS),
        *((case_id, catalog.specs) for case_id, catalog in SCALEUP_CATALOGS.items()),
    )
    assert tuple(case_id for case_id, _ in catalogs) == tuple(
        EXPECTED_SEQUENTIAL_ONBOARDING
    )

    prior_specs: set[IntrinsicSpec] = set()
    prior_keys: set[tuple[Architecture, str]] = set()
    actual = {}
    for case_id, specs in catalogs:
        statuses = Counter(
            _onboarding_status(spec, prior_specs, prior_keys) for spec in specs
        )
        actual[case_id] = (
            statuses["exact"],
            statuses["same-name-conflict"],
            statuses["unknown"],
        )
        prior_specs.update(specs)
        prior_keys.update((spec.architecture, spec.spelling) for spec in specs)

    assert actual == EXPECTED_SEQUENTIAL_ONBOARDING


def test_onboarding_does_not_reuse_a_same_spelling_from_the_wrong_architecture() -> None:
    neon = next(
        spec
        for spec in QS8_VADD_MINMAX_SPECS
        if spec.architecture is Architecture.NEON and spec.spelling == "vdupq_n_s8"
    )
    wrong_architecture = replace(neon, architecture=Architecture.RVV)

    assert _onboarding_status(
        wrong_architecture,
        {neon},
        {(neon.architecture, neon.spelling)},
    ) == "unknown"


def test_exact_configured_descriptor_is_not_a_semantic_review() -> None:
    configured = QS8_VADD_MINMAX_SPECS[0]
    variant = next(
        variant
        for variant in CANONICAL_INTRINSIC_INDEX.variants
        if variant.spec == configured
    )

    assert variant.spec == configured
    assert variant.provenance
    assert not hasattr(variant, "reviewed")
    assert not hasattr(variant, "approved")

    review_ledger = json.loads(
        (REPOSITORY_ROOT / "verification/intrinsic-dashboard/reviews.json").read_text(
            encoding="utf-8"
        )
    )
    assert review_ledger == {
        "intrinsics": [],
        "kernel_files": [],
        "schema_version": 2,
    }
