"""Command-line entry point for the local intrinsic verification dashboard.

Review commands are intentionally explicit and fail closed.  In particular,
there is no bulk-approval command: every intrinsic approval requires all six
semantic-review acknowledgements and at least one evidence reference.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import threading
from pathlib import Path
from typing import Callable, Mapping, Sequence, TextIO

from .activity import ActivityError, ActivityRecord, save_activity
from .authority import (
    DEFAULT_REVIEWER_REGISTRY_RELATIVE_PATH,
    ReviewerAuthorityError,
    bind_evidence,
    require_trusted_reviewer,
)
from .audit import (
    AuditPersistenceError,
    approve_intrinsic,
    approve_kernel_file,
    load_ledger,
    save_ledger,
)
from .checks import lean_project_digest, run_lean_proof_checks
from .model import (
    AuditLedger,
    AuditModelError,
    ProofCheckAttestation,
    ReviewChecklist,
)
from .proof_policy import proof_policy_digest
from .server import DEFAULT_PORT, serve
from .state import (
    DEFAULT_ACTIVITY_RELATIVE_PATH,
    DEFAULT_REVIEW_LEDGER_RELATIVE_PATH,
    REPOSITORY_ROOT,
    DashboardStateError,
    DashboardStateProvider,
    create_state_provider,
)


ProofChecker = Callable[..., dict[str, ProofCheckAttestation]]
ProjectDigester = Callable[[Path], str]
PolicyDigester = Callable[[Path], str]
ProviderFactory = Callable[..., DashboardStateProvider]
ServeRunner = Callable[..., None]


class CLIError(RuntimeError):
    """A requested dashboard operation cannot be completed safely."""


class DigestBoundStateProvider:
    """Expose proof results only while their complete Lean tree is unchanged."""

    def __init__(
        self,
        provider: DashboardStateProvider,
        *,
        repository_root: Path,
        checks: Mapping[str, ProofCheckAttestation],
        checked_digest: str | None,
        project_digester: ProjectDigester = lean_project_digest,
        policy_digester: PolicyDigester = proof_policy_digest,
    ) -> None:
        self._provider = provider
        self._repository_root = repository_root
        self._checks = dict(checks)
        self._checked_digest = checked_digest
        self._project_digester = project_digester
        self._policy_digester = policy_digester
        policy_digests = {check.policy_sha256 for check in self._checks.values()}
        self._checked_policy_digest = (
            next(iter(policy_digests)) if len(policy_digests) == 1 else None
        )
        self._lock = threading.Lock()

    def _is_current(self) -> bool:
        if self._checked_digest is None or self._checked_policy_digest is None:
            return False
        try:
            return (
                self._project_digester(self._repository_root) == self._checked_digest
                and self._policy_digester(self._repository_root)
                == self._checked_policy_digest
            )
        except (OSError, UnicodeError, ValueError):
            return False

    def __call__(self) -> dict[str, object]:
        # The provider itself serializes scans.  This outer lock also makes the
        # temporary lean_checks selection atomic across concurrent HTTP polls.
        with self._lock:
            current = self._is_current()
            self._provider.lean_checks = dict(self._checks if current else {})
            state = self._provider()
            if current and not self._is_current():
                self._provider.lean_checks = {}
                state = self._provider()
            return state


def _stable_proof_checks(
    repository_root: Path,
    *,
    cases: Sequence[str] | None = None,
    proof_checker: ProofChecker = run_lean_proof_checks,
    project_digester: ProjectDigester = lean_project_digest,
    policy_digester: PolicyDigester = proof_policy_digest,
) -> tuple[dict[str, ProofCheckAttestation], str | None]:
    before = project_digester(repository_root)
    before_policy = policy_digester(repository_root)
    checks = proof_checker(repository_root, cases=cases)
    after = project_digester(repository_root)
    after_policy = policy_digester(repository_root)
    if before != after or before_policy != after_policy:
        return {}, None
    if any(check.project_sha256 != before for check in checks.values()):
        return {}, None
    if any(check.policy_sha256 != before_policy for check in checks.values()):
        return {}, None
    return dict(checks), after


def create_cli_state_provider(
    repository_root: Path,
    *,
    check_lean: bool,
    provider_factory: ProviderFactory = create_state_provider,
    proof_checker: ProofChecker = run_lean_proof_checks,
    project_digester: ProjectDigester = lean_project_digest,
    policy_digester: PolicyDigester = proof_policy_digest,
) -> DigestBoundStateProvider:
    checks: dict[str, ProofCheckAttestation] = {}
    checked_digest: str | None = None
    if check_lean:
        checks, checked_digest = _stable_proof_checks(
            repository_root,
            proof_checker=proof_checker,
            project_digester=project_digester,
            policy_digester=policy_digester,
        )
    provider = provider_factory(
        repository_root,
        review_ledger_path=(repository_root / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH),
        activity_directory=repository_root / DEFAULT_ACTIVITY_RELATIVE_PATH,
        lean_checks=checks,
    )
    return DigestBoundStateProvider(
        provider,
        repository_root=repository_root,
        checks=checks,
        checked_digest=checked_digest,
        project_digester=project_digester,
        policy_digester=policy_digester,
    )


def _current_ledger(provider: DashboardStateProvider) -> AuditLedger:
    ledger = provider.current_ledger()
    if not isinstance(ledger, AuditLedger):
        raise CLIError("state provider returned an invalid current ledger")
    return ledger


def _rebuild_with_previous(
    provider: DashboardStateProvider, previous: AuditLedger
) -> AuditLedger:
    """Rebuild once through the cache-aware provider without publishing midway."""

    with tempfile.TemporaryDirectory(prefix="saltyrn-review-") as directory:
        temporary_ledger = Path(directory) / "reviews.json"
        save_ledger(temporary_ledger, previous)
        original_path = provider.review_ledger_path
        provider.review_ledger_path = temporary_ledger
        try:
            return _current_ledger(provider)
        finally:
            provider.review_ledger_path = original_path


def _replace_intrinsic(
    ledger: AuditLedger, subject_id: str, replacement: object
) -> AuditLedger:
    matches = [item for item in ledger.intrinsics if item.subject_id == subject_id]
    if len(matches) != 1:
        raise CLIError(
            f"intrinsic subject must match exactly one current record: {subject_id}"
        )
    return AuditLedger(
        intrinsics=tuple(
            replacement if item.subject_id == subject_id else item
            for item in ledger.intrinsics
        ),
        kernel_files=ledger.kernel_files,
    )


def _replace_kernel_file(
    ledger: AuditLedger, program_id: str, replacement: object
) -> AuditLedger:
    matches = [item for item in ledger.kernel_files if item.program_id == program_id]
    if len(matches) != 1:
        raise CLIError(
            f"program id must match exactly one current record: {program_id}"
        )
    return AuditLedger(
        intrinsics=ledger.intrinsics,
        kernel_files=tuple(
            replacement if item.program_id == program_id else item
            for item in ledger.kernel_files
        ),
    )


def _existing_ledger(path: Path) -> AuditLedger:
    return load_ledger(path) if path.exists() else AuditLedger()


def _approval_provider(
    repository_root: Path,
    *,
    lean_checks: Mapping[str, ProofCheckAttestation],
    provider_factory: ProviderFactory,
) -> DashboardStateProvider:
    return provider_factory(
        repository_root,
        review_ledger_path=(repository_root / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH),
        activity_directory=repository_root / DEFAULT_ACTIVITY_RELATIVE_PATH,
        lean_checks=lean_checks,
    )


def _approve_intrinsic_command(
    arguments: argparse.Namespace,
    *,
    provider_factory: ProviderFactory,
) -> str:
    root = arguments.repository_root
    ledger_path = root / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH
    provider = _approval_provider(
        root, lean_checks={}, provider_factory=provider_factory
    )
    current = _current_ledger(provider)
    # Force parsing of an existing tracked ledger even if a test provider does
    # not consume it; malformed persisted evidence must never be overwritten.
    if ledger_path.exists():
        _existing_ledger(ledger_path)

    matches = [
        item for item in current.intrinsics if item.subject_id == arguments.subject
    ]
    if len(matches) != 1:
        raise CLIError(
            "intrinsic subject must match exactly one current record: "
            f"{arguments.subject}"
        )
    trusted_reviewer = require_trusted_reviewer(
        root / DEFAULT_REVIEWER_REGISTRY_RELATIVE_PATH,
        arguments.reviewer,
        author=matches[0].author,
    )
    evidence = bind_evidence(root, arguments.evidence)
    checklist = ReviewChecklist(
        identity_signature=arguments.ack_identity_signature,
        operand_order_types=arguments.ack_operand_order_types,
        value_semantics=arguments.ack_value_semantics,
        fused_rounding_saturation=arguments.ack_fused_rounding_saturation,
        architectural_state=arguments.ack_architectural_state,
        mutation_tests=arguments.ack_mutation_tests,
        evidence=evidence,
    )
    approved = approve_intrinsic(
        matches[0],
        reviewer=trusted_reviewer.reviewer_id,
        checklist=checklist,
        note=arguments.note,
    )
    provisional = _replace_intrinsic(current, arguments.subject, approved)
    rebuilt = _rebuild_with_previous(provider, provisional)
    rebuilt_match = next(
        (item for item in rebuilt.intrinsics if item.subject_id == arguments.subject),
        None,
    )
    if rebuilt_match is None or not rebuilt_match.status.reviewed:
        raise CLIError("intrinsic approval became stale during the required rebuild")
    save_ledger(ledger_path, rebuilt)
    return f"approved intrinsic {arguments.subject}"


def _approve_file_command(
    arguments: argparse.Namespace,
    *,
    provider_factory: ProviderFactory,
    proof_checker: ProofChecker,
    project_digester: ProjectDigester,
    policy_digester: PolicyDigester,
) -> str:
    root = arguments.repository_root
    checks, checked_digest = _stable_proof_checks(
        root,
        proof_checker=proof_checker,
        project_digester=project_digester,
        policy_digester=policy_digester,
    )
    if checked_digest is None:
        raise CLIError("Lean sources changed while proof checks were running")
    provider = _approval_provider(
        root, lean_checks=checks, provider_factory=provider_factory
    )
    current = _current_ledger(provider)
    ledger_path = root / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH
    if ledger_path.exists():
        _existing_ledger(ledger_path)
    matches = [
        item for item in current.kernel_files if item.program_id == arguments.program_id
    ]
    if len(matches) != 1:
        raise CLIError(
            "program id must match exactly one current record: "
            f"{arguments.program_id}"
        )
    trusted_reviewer = require_trusted_reviewer(
        root / DEFAULT_REVIEWER_REGISTRY_RELATIVE_PATH,
        arguments.reviewer,
        author=matches[0].author,
    )
    evidence = bind_evidence(root, arguments.evidence)
    approved = approve_kernel_file(
        matches[0],
        reviewer=trusted_reviewer.reviewer_id,
        evidence=evidence,
        note=arguments.note,
    )
    if project_digester(root) != checked_digest:
        raise CLIError(
            "Lean sources changed after proof checks; approval was not saved"
        )
    expected_policy = {check.policy_sha256 for check in checks.values()}
    if len(expected_policy) != 1 or policy_digester(root) not in expected_policy:
        raise CLIError(
            "proof policy changed after proof checks; approval was not saved"
        )
    save_ledger(
        ledger_path,
        _replace_kernel_file(current, arguments.program_id, approved),
    )
    return f"approved file {arguments.program_id}"


def _add_repository_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--repository-root",
        type=lambda value: Path(value).expanduser().resolve(),
        default=REPOSITORY_ROOT,
        help="SALTyRN checkout root",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="run the local dashboard")
    _add_repository_root(serve_parser)
    serve_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve_parser.add_argument("--check-lean", action="store_true")

    snapshot = subparsers.add_parser("snapshot", help="print current state as JSON")
    _add_repository_root(snapshot)
    snapshot.add_argument("--check-lean", action="store_true")

    activity = subparsers.add_parser("activity", help="write one agent activity")
    _add_repository_root(activity)
    activity.add_argument("--agent-id", required=True)
    activity.add_argument("--name", required=True)
    activity.add_argument(
        "--status",
        required=True,
        choices=("running", "idle", "completed", "failed", "blocked"),
    )
    activity.add_argument("--task", required=True)
    activity.add_argument("--current-item", default="")
    activity.add_argument("--completed", type=int, default=0)
    activity.add_argument("--total", type=int, default=0)

    intrinsic = subparsers.add_parser(
        "approve-intrinsic", help="record one hash-bound intrinsic review"
    )
    _add_repository_root(intrinsic)
    intrinsic.add_argument("--subject", required=True)
    intrinsic.add_argument("--reviewer", required=True)
    intrinsic.add_argument(
        "--ack-identity-signature", action="store_true", required=True
    )
    intrinsic.add_argument(
        "--ack-operand-order-types", action="store_true", required=True
    )
    intrinsic.add_argument("--ack-value-semantics", action="store_true", required=True)
    intrinsic.add_argument(
        "--ack-fused-rounding-saturation", action="store_true", required=True
    )
    intrinsic.add_argument(
        "--ack-architectural-state", action="store_true", required=True
    )
    intrinsic.add_argument("--ack-mutation-tests", action="store_true", required=True)
    intrinsic.add_argument("--evidence", action="append", required=True)
    intrinsic.add_argument("--note", default="")

    file_parser = subparsers.add_parser(
        "approve-file", help="record final review after every gate passes"
    )
    _add_repository_root(file_parser)
    file_parser.add_argument("--program-id", required=True)
    file_parser.add_argument("--reviewer", required=True)
    file_parser.add_argument("--evidence", action="append", required=True)
    file_parser.add_argument("--note", default="")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    provider_factory: ProviderFactory = create_state_provider,
    proof_checker: ProofChecker = run_lean_proof_checks,
    project_digester: ProjectDigester = lean_project_digest,
    policy_digester: PolicyDigester = proof_policy_digest,
    serve_runner: ServeRunner = serve,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.command in {"serve", "snapshot"}:
            provider = create_cli_state_provider(
                arguments.repository_root,
                check_lean=arguments.check_lean,
                provider_factory=provider_factory,
                proof_checker=proof_checker,
                project_digester=project_digester,
                policy_digester=policy_digester,
            )
            if arguments.command == "serve":
                serve_runner(port=arguments.port, state_provider=provider)
            else:
                json.dump(
                    provider(),
                    stdout,
                    ensure_ascii=True,
                    indent=2,
                    sort_keys=True,
                )
                stdout.write("\n")
            return 0

        if arguments.command == "activity":
            record = ActivityRecord(
                agent_id=arguments.agent_id,
                name=arguments.name,
                status=arguments.status,
                task=arguments.task,
                current_item=arguments.current_item,
                completed=arguments.completed,
                total=arguments.total,
            )
            save_activity(
                arguments.repository_root / DEFAULT_ACTIVITY_RELATIVE_PATH, record
            )
            stdout.write(
                f"activity {record.agent_id}: {record.status} "
                f"{record.completed}/{record.total}\n"
            )
            return 0

        if arguments.command == "approve-intrinsic":
            message = _approve_intrinsic_command(
                arguments, provider_factory=provider_factory
            )
        elif arguments.command == "approve-file":
            message = _approve_file_command(
                arguments,
                provider_factory=provider_factory,
                proof_checker=proof_checker,
                project_digester=project_digester,
                policy_digester=policy_digester,
            )
        else:  # pragma: no cover - argparse enforces this exhaustively.
            raise CLIError(f"unknown command: {arguments.command}")
        stdout.write(message + "\n")
        return 0
    except (
        ActivityError,
        AuditModelError,
        AuditPersistenceError,
        CLIError,
        DashboardStateError,
        FileNotFoundError,
        OSError,
        ReviewerAuthorityError,
        UnicodeError,
        ValueError,
    ) as error:
        stderr.write(f"error: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
