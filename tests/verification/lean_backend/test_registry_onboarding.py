from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

import workflow.verification.lean_backend.registry_onboarding as onboarding
from workflow.verification.lean_backend.registry_onboarding import (
    RegistryOnboardingError,
    _group_record,
    _side_report,
    _main,
    build_onboarding_report,
    render_onboarding_report,
)
from workflow.verification.lean_backend.frontend import parse_kernel
from workflow.verification.lean_backend.intrinsic_index import (
    CANONICAL_INTRINSIC_INDEX,
    SourceIntrinsicDescriptor,
)
from workflow.verification.lean_backend.profiles import FRONTEND_PROFILES
from workflow.verification.lean_backend.scaleup_catalog import QS8_VCVT_CATALOG
from workflow.verification.lean_backend.schema import Architecture


ROOT = Path(__file__).resolve().parents[3]
CASES = {
    "qs8-vadd-minmax": (93, 16),
    "s8-vclamp": (36, 5),
    "qs8-vcvt": (23, 11),
    "qs8-vlrelu": (30, 13),
    "qu8-vadd-minmax": (70, 21),
}
clang_required = pytest.mark.skipif(
    shutil.which("clang") is None, reason="system clang required"
)


@pytest.mark.parametrize(("case_id", "expected_calls"), CASES.items())
@clang_required
def test_real_configured_cases_are_grouped_and_classified(
    case_id: str, expected_calls: tuple[int, int]
) -> None:
    report = build_onboarding_report(case_id, repository_root=ROOT)

    assert report["authoritative"] is False
    assert report["semantic_review_inherited"] is False
    assert report["kernel_catalog_remains_authoritative"] is True
    assert report["excluded_case_catalog"] is True
    assert "kernel-scoped" in report["binding_authority"]
    assert tuple(side["architecture"] for side in report["sides"]) == ("neon", "rvv")
    assert tuple(side["call_occurrence_count"] for side in report["sides"]) == expected_calls
    assert report["summary"]["call_occurrence_count"] == sum(expected_calls)
    assert all(side["call_groups"] for side in report["sides"])

    for side in report["sides"]:
        assert sum(group["occurrence_count"] for group in side["call_groups"]) == side[
            "call_occurrence_count"
        ]
        for group in side["call_groups"]:
            assert group["status"] != "exact-configured"
            assert len(group["call_ids"]) == group["occurrence_count"]
            assert sum(
                profile["occurrence_count"]
                for profile in group["constant_profiles"]
            ) == group["occurrence_count"]
            for candidate in group["candidates"]:
                assert len(candidate["descriptor_sha256"]) == 64
                assert candidate["provenance"]
                assert "immediate_constraints" in candidate
                assert all(
                    origin["case_id"] != case_id
                    for origin in candidate["provenance"]
                )
                assert sum(
                    key in candidate
                    for key in (
                        "lean_target",
                        "structural_operation",
                        "schedule_operation",
                    )
                ) == 1


@clang_required
def test_case_catalog_does_not_self_confirm_an_immediate_variant() -> None:
    report = build_onboarding_report("qs8-vcvt", repository_root=ROOT)
    rvv = next(side for side in report["sides"] if side["architecture"] == "rvv")
    group = next(
        group
        for group in rvv["call_groups"]
        if group["spelling"] == "__riscv_vnclip_wx_i16m4"
    )

    assert group["constant_profiles"] == [
        {
            "known_constant_arguments": [
                {"argument_index": 1, "value": 16},
                {"argument_index": 2, "value": 0},
            ],
            "occurrence_count": 1,
            "call_ids": ["call_0007"],
        }
    ]
    assert group["status"] == "same-name-mismatch"
    assert all(
        origin["case_id"] != "qs8-vcvt"
        for candidate in group["candidates"]
        for origin in candidate["provenance"]
    )
    assert report["semantic_review_inherited"] is False


def test_one_spelling_must_have_one_candidate_for_every_immediate_profile() -> None:
    spec = QS8_VCVT_CATALOG.registry["__riscv_vnclip_wx_i16m4"]
    descriptor = SourceIntrinsicDescriptor.from_spec(spec)
    shift_16 = replace(descriptor, known_constants=((1, 16), (2, 0)))
    shift_15 = replace(descriptor, known_constants=((1, 15), (2, 0)))

    group = _group_record(
        Architecture.RVV,
        (("call_0000", shift_16), ("call_0001", shift_15)),
        CANONICAL_INTRINSIC_INDEX,
    )

    assert group["status"] == "same-name-mismatch"
    assert group["occurrence_count"] == 2
    assert [profile["known_constant_arguments"] for profile in group["constant_profiles"]] == [
        [
            {"argument_index": 1, "value": 15},
            {"argument_index": 2, "value": 0},
        ],
        [
            {"argument_index": 1, "value": 16},
            {"argument_index": 2, "value": 0},
        ],
    ]


@clang_required
def test_side_report_rejects_an_architecture_dialect_mismatch() -> None:
    profile = FRONTEND_PROFILES["s8-vclamp"].neon
    extraction = parse_kernel(
        ROOT / "kernels/source/s8-vclamp.c",
        profile=profile,
    )

    with pytest.raises(RegistryOnboardingError, match="does not match"):
        _side_report(
            extraction,
            Architecture.RVV,
            ROOT,
            CANONICAL_INTRINSIC_INDEX,
        )


@clang_required
def test_rendered_report_is_deterministic_json() -> None:
    first_report = build_onboarding_report("s8-vclamp", repository_root=ROOT)
    second_report = build_onboarding_report("s8-vclamp", repository_root=ROOT)

    first = render_onboarding_report(first_report)
    second = render_onboarding_report(second_report)

    assert first == second
    assert first.endswith("\n")
    assert json.loads(first) == first_report


def test_unconfigured_case_is_rejected_before_frontend_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def unexpected_parse(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("unconfigured case reached Clang extraction")

    monkeypatch.setattr(onboarding, "parse_kernel", unexpected_parse)

    with pytest.raises(RegistryOnboardingError, match="no configured frontend profile"):
        build_onboarding_report("new-unconfigured-kernel", repository_root=ROOT)
    assert called is False


@clang_required
def test_cli_supports_explicit_json_format(capsys: pytest.CaptureFixture[str]) -> None:
    assert _main(
        [
            "--case",
            "s8-vclamp",
            "--repository-root",
            str(ROOT),
            "--clang",
            "clang",
            "--format",
            "json",
        ]
    ) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["case_id"] == "s8-vclamp"
    assert output["authoritative"] is False
