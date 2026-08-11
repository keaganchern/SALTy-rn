from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from workflow.verification.lean_backend.generate_cases import (
    _main,
    generate_case_modules,
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
