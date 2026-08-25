from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import workflow.verification.lean_backend.generate_cases as generate_cases
from workflow.verification.lean_backend.generate_cases import (
    _main,
    generate_case_obligations,
    generate_case_modules,
    generated_obligation_path,
)


ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(shutil.which("clang") is None, reason="system clang required")


def test_generation_is_deterministic_and_covers_all_four_scaleup_cases():
    first = generate_case_modules(repository_root=ROOT)
    second = generate_case_modules(repository_root=ROOT)

    assert first == second
    assert tuple(first) == (
        "s8-vclamp",
        "qs8-vcvt",
        "qs8-vlrelu",
        "qu8-vadd-minmax",
    )
    assert all('def registrySha256 : String :=' in module for module in first.values())


def test_cli_check_accepts_the_checked_in_modules():
    assert _main(
        [
            "--repository-root",
            str(ROOT),
            "--check",
        ]
    ) == 0


def test_qs8_vlrelu_obligation_is_deterministic_and_checked_in() -> None:
    first = generate_case_obligations(cases=("qs8-vlrelu",))
    second = generate_case_obligations(cases=("qs8-vlrelu",))
    path = generated_obligation_path(ROOT, "qs8-vlrelu")

    assert first == second
    assert tuple(first) == ("qs8-vlrelu",)
    assert path.read_text(encoding="ascii") == first["qs8-vlrelu"]
    assert "allLengthsValueEqualWithOverreadClaim" in first["qs8-vlrelu"]


def test_cli_check_rejects_stale_generated_obligation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    models = tmp_path / "src/verification_bw/lean/SALT/Generated/QS8VLReLU/Models.lean"
    obligation = models.with_name("Obligation.lean")
    models.parent.mkdir(parents=True)
    models.write_text("generated model\n", encoding="ascii")
    obligation.write_text("stale obligation\n", encoding="ascii")
    expected_obligation = generate_case_obligations(cases=("qs8-vlrelu",))[
        "qs8-vlrelu"
    ]
    monkeypatch.setattr(
        generate_cases,
        "generate_case_modules",
        lambda **_kwargs: {"qs8-vlrelu": "generated model\n"},
    )
    monkeypatch.setattr(
        generate_cases,
        "generate_case_obligations",
        lambda **_kwargs: {"qs8-vlrelu": expected_obligation},
    )

    assert _main(
        [
            "--repository-root",
            str(tmp_path),
            "--case",
            "qs8-vlrelu",
            "--check",
        ]
    ) == 1
