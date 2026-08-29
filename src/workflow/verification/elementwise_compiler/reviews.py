"""Strict content-addressed independent review records for intrinsic variants."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .schema import Architecture, ElementwiseSchemaError, canonical_sha256


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ElementwiseSchemaError(f"{field} must be a trimmed non-empty string")
    return value


def _digest(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ElementwiseSchemaError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ElementwiseSchemaError(f"{field} must be a string-keyed JSON object")
    return value


def _sequence(value: object, field: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ElementwiseSchemaError(f"{field} must be a JSON array")
    return value


def _exact(data: Mapping[str, Any], expected: set[str], subject: str) -> None:
    if set(data) != expected:
        raise ElementwiseSchemaError(
            f"invalid {subject} fields: missing={sorted(expected - set(data))!r}, "
            f"extra={sorted(set(data) - expected)!r}"
        )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ReviewEvidence:
    authority: str
    revision: str
    source_url: str
    path: str
    file_sha256: str
    selectors: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.authority, "evidence authority")
        _text(self.revision, "evidence revision")
        if not self.source_url.startswith("https://"):
            raise ElementwiseSchemaError("evidence source URL must use https")
        _text(self.path, "evidence path")
        _digest(self.file_sha256, "evidence file digest")
        if not self.selectors or tuple(sorted(set(self.selectors))) != self.selectors:
            raise ElementwiseSchemaError("evidence selectors must be sorted and unique")
        for selector in self.selectors:
            _text(selector, "evidence selector")

    def to_record(self) -> dict[str, object]:
        return {
            "authority": self.authority,
            "revision": self.revision,
            "source_url": self.source_url,
            "path": self.path,
            "file_sha256": self.file_sha256,
            "selectors": list(self.selectors),
        }

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "ReviewEvidence":
        expected = {
            "authority", "revision", "source_url", "path", "file_sha256", "selectors"
        }
        _exact(data, expected, "review evidence")
        selectors = tuple(
            _text(value, "evidence selector")
            for value in _sequence(data["selectors"], "evidence selectors")
        )
        return cls(
            _text(data["authority"], "evidence authority"),
            _text(data["revision"], "evidence revision"),
            _text(data["source_url"], "evidence source URL"),
            _text(data["path"], "evidence path"),
            _digest(data["file_sha256"], "evidence file digest"),
            selectors,
        )


@dataclass(frozen=True, slots=True)
class ReviewCheck:
    name: str
    command: str
    output_path: str
    output_sha256: str

    def __post_init__(self) -> None:
        _text(self.name, "review check name")
        _text(self.command, "review check command")
        _text(self.output_path, "review check output path")
        if Path(self.output_path).is_absolute() or ".." in Path(self.output_path).parts:
            raise ElementwiseSchemaError(
                "review check output path must stay repository-relative"
            )
        _digest(self.output_sha256, "review check output digest")

    def to_record(self) -> dict[str, str]:
        return {
            "name": self.name,
            "command": self.command,
            "status": "passed",
            "output_path": self.output_path,
            "output_sha256": self.output_sha256,
        }

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "ReviewCheck":
        _exact(
            data,
            {"name", "command", "status", "output_path", "output_sha256"},
            "review check",
        )
        if data["status"] != "passed":
            raise ElementwiseSchemaError("only passed checks may enter an approved review")
        return cls(
            _text(data["name"], "review check name"),
            _text(data["command"], "review check command"),
            _text(data["output_path"], "review check output path"),
            _digest(data["output_sha256"], "review check output digest"),
        )


@dataclass(frozen=True, slots=True)
class IntrinsicReview:
    architecture: Architecture
    spelling: str
    function_type: str
    argument_count: int
    descriptor_sha256: str
    implementation_sha256: str
    policy_path: str
    policy_sha256: str
    reviewer: str
    evidence: tuple[ReviewEvidence, ...]
    checks: tuple[ReviewCheck, ...]
    detail: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        _text(self.spelling, "review spelling")
        _text(self.function_type, "review function type")
        if type(self.argument_count) is not int or self.argument_count < 0:
            raise ElementwiseSchemaError("review argument count must be non-negative")
        _digest(self.descriptor_sha256, "review descriptor digest")
        _digest(self.implementation_sha256, "review implementation digest")
        _text(self.policy_path, "review policy path")
        if Path(self.policy_path).is_absolute() or ".." in Path(self.policy_path).parts:
            raise ElementwiseSchemaError("review policy path must stay repository-relative")
        _digest(self.policy_sha256, "review policy digest")
        _text(self.reviewer, "reviewer identity")
        _text(self.detail, "review detail")
        if not self.evidence:
            raise ElementwiseSchemaError("approved intrinsic review needs primary evidence")
        if tuple(sorted(self.evidence, key=lambda item: item.to_record().__repr__())) != self.evidence:
            raise ElementwiseSchemaError("review evidence must use canonical order")
        if not self.checks:
            raise ElementwiseSchemaError("approved intrinsic review needs executable checks")
        if tuple(sorted(self.checks, key=lambda item: item.name)) != self.checks:
            raise ElementwiseSchemaError("review checks must be sorted by name")
        if self.schema_version != 1:
            raise ElementwiseSchemaError("unsupported intrinsic review schema version")

    @property
    def review_id(self) -> str:
        source_key = canonical_sha256(
            {
                "architecture": self.architecture.value,
                "spelling": self.spelling,
                "function_type": self.function_type,
                "argument_count": self.argument_count,
            }
        )[:16]
        return f"intrinsic-review:{self.architecture.value}:{self.spelling}:{source_key}"

    @property
    def key(self) -> tuple[object, ...]:
        return (
            self.architecture,
            self.spelling,
            self.function_type,
            self.argument_count,
            self.descriptor_sha256,
            self.implementation_sha256,
        )

    def unsigned_record(self) -> dict[str, object]:
        return {
            "artifact_kind": "intrinsic-review",
            "schema_version": self.schema_version,
            "review_id": self.review_id,
            "verdict": "approved",
            "architecture": self.architecture.value,
            "spelling": self.spelling,
            "function_type": self.function_type,
            "argument_count": self.argument_count,
            "descriptor_sha256": self.descriptor_sha256,
            "implementation_sha256": self.implementation_sha256,
            "policy_path": self.policy_path,
            "policy_sha256": self.policy_sha256,
            "reviewer": self.reviewer,
            "evidence": [item.to_record() for item in self.evidence],
            "checks": [item.to_record() for item in self.checks],
            "detail": self.detail,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.unsigned_record())

    def to_record(self) -> dict[str, object]:
        return {**self.unsigned_record(), "review_sha256": self.sha256}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "IntrinsicReview":
        expected = {
            "artifact_kind", "schema_version", "review_id", "review_sha256",
            "verdict", "architecture", "spelling", "function_type",
            "argument_count", "descriptor_sha256", "implementation_sha256",
            "policy_path", "policy_sha256", "reviewer", "evidence", "checks",
            "detail",
        }
        _exact(data, expected, "intrinsic review")
        if data["artifact_kind"] != "intrinsic-review" or data["verdict"] != "approved":
            raise ElementwiseSchemaError("intrinsic review is not an approved review artifact")
        try:
            architecture = Architecture(data["architecture"])
        except (TypeError, ValueError) as error:
            raise ElementwiseSchemaError("invalid review architecture") from error
        argument_count = data["argument_count"]
        schema_version = data["schema_version"]
        if type(argument_count) is not int or type(schema_version) is not int:
            raise ElementwiseSchemaError("review integer fields are malformed")
        review = cls(
            architecture,
            _text(data["spelling"], "review spelling"),
            _text(data["function_type"], "review function type"),
            argument_count,
            _digest(data["descriptor_sha256"], "review descriptor digest"),
            _digest(data["implementation_sha256"], "review implementation digest"),
            _text(data["policy_path"], "review policy path"),
            _digest(data["policy_sha256"], "review policy digest"),
            _text(data["reviewer"], "reviewer identity"),
            tuple(
                ReviewEvidence.from_record(_mapping(item, "review evidence"))
                for item in _sequence(data["evidence"], "review evidence")
            ),
            tuple(
                ReviewCheck.from_record(_mapping(item, "review check"))
                for item in _sequence(data["checks"], "review checks")
            ),
            _text(data["detail"], "review detail"),
            schema_version,
        )
        if data["review_id"] != review.review_id:
            raise ElementwiseSchemaError("intrinsic review id disagrees with source key")
        if _digest(data["review_sha256"], "review digest") != review.sha256:
            raise ElementwiseSchemaError("intrinsic review digest disagrees with contents")
        return review


def load_intrinsic_reviews(repository_root: str | Path) -> Mapping[tuple[object, ...], IntrinsicReview]:
    """Load approved records and re-check their local policy binding."""

    root = Path(repository_root).resolve()
    review_root = root / "verification/elementwise-compiler/intrinsic-reviews"
    result: dict[tuple[object, ...], IntrinsicReview] = {}
    if not review_root.is_dir():
        return result
    for path in sorted(review_root.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ElementwiseSchemaError(f"cannot read intrinsic review {path.name}") from error
        review = IntrinsicReview.from_record(_mapping(raw, "intrinsic review"))
        policy = (root / review.policy_path).resolve()
        try:
            policy.relative_to(root)
        except ValueError as error:
            raise ElementwiseSchemaError("intrinsic review policy escapes repository") from error
        if not policy.is_file() or _file_sha256(policy) != review.policy_sha256:
            raise ElementwiseSchemaError(
                f"intrinsic review {path.name} has a stale policy binding"
            )
        for check in review.checks:
            output = (root / check.output_path).resolve()
            try:
                output.relative_to(root)
            except ValueError as error:
                raise ElementwiseSchemaError(
                    "intrinsic review check output escapes repository"
                ) from error
            if not output.is_file() or _file_sha256(output) != check.output_sha256:
                raise ElementwiseSchemaError(
                    f"intrinsic review {path.name} has a stale check output binding"
                )
        if review.key in result:
            raise ElementwiseSchemaError("duplicate approved intrinsic review key")
        result[review.key] = review
    return result
