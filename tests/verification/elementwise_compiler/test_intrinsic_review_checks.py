from __future__ import annotations

from pathlib import Path

from workflow.verification.elementwise_compiler.intrinsic_review_checks import (
    build_intrinsic_review_checks,
)
from workflow.verification.elementwise_compiler.schema import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]


def test_review_checks_cover_every_used_exact_subject() -> None:
    checks = build_intrinsic_review_checks(ROOT)
    unsigned = dict(checks)
    assert unsigned.pop("checks_sha256") == canonical_sha256(unsigned)
    assert checks["counts"] == {"families": 12, "passed_subjects": 180}
    assert len({row["capability_id"] for row in checks["subjects"]}) == 180
    assert all(row["status"] == "passed" for row in checks["subjects"])
    assert all(row["status"] == "passed" for row in checks["family_checks"])
