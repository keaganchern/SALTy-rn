"""Fail-closed policy checks layered on top of Lean target compilation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping, Sequence

from .freshness import check_semantic_mutation_sensitivity, clang_producer_digest
from .model import canonical_sha256


POLICY_RELATIVE_PATH = Path("verification/intrinsic-dashboard/proof-policy.json")
AUDITOR_RELATIVE_PATH = Path(
    "src/workflow/verification/intrinsic_dashboard/lean/ProofAudit.lean"
)
AUDIT_OUTPUT_PREFIX = "SALTYRN_PROOF_AUDIT_V1\t"
POLICY_CASES = (
    "qs8-vadd-minmax",
    "s8-vclamp",
    "qs8-vcvt",
    "qs8-vlrelu",
    "qu8-vadd-minmax",
)
FORBIDDEN_LEAN_IDENTIFIERS = frozenset(
    {
        "admit",
        "axiom",
        "constant",
        "extern",
        "implemented_by",
        "elab_rules",
        "macro_rules",
        "native_decide",
        "opaque",
        "ofReduceBool",
        "partial",
        "run_cmd",
        "sorry",
        "sorryAx",
        "unsafe",
    }
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")
_BLOCKED_TOOL_ENVIRONMENT = frozenset(
    {
        "AR",
        "CC",
        "CXX",
        "ELAN_HOME",
        "ELAN_TOOLCHAIN",
        "LAKE_CACHE_DIR",
        "LAKE_HOME",
        "LAKE_PACKAGES_DIR",
        "LEAN_AR",
        "LEAN_CC",
        "LEAN_OPTS",
        "LEAN_PATH",
        "LEAN_SRC_PATH",
        "LEAN_SYSROOT",
    }
)


class ProofPolicyError(ValueError):
    """The tracked proof policy or one of its protected inputs is malformed."""


@dataclass(frozen=True, slots=True)
class ProtectedFile:
    path: str
    sha256: str


@dataclass(frozen=True, slots=True)
class ProofPolicyCase:
    module: str
    theorem: str
    proof_path: str
    elaborated_type_sha256: str
    contract: ProtectedFile | None


@dataclass(frozen=True, slots=True)
class LeanToolchainPolicy:
    selector: str
    lean_sha256: str
    lake_sha256: str
    runtime_sha256: str
    lean_version: str
    lake_version: str


@dataclass(frozen=True, slots=True)
class ProofPolicy:
    allowed_axioms: frozenset[str]
    lean_project_sha256: str
    toolchain: LeanToolchainPolicy
    cases: Mapping[str, ProofPolicyCase]


@dataclass(frozen=True, slots=True)
class ElaboratedTheoremAudit:
    module: str
    theorem: str
    level_parameters: tuple[str, ...]
    type_encoding: str
    axioms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResolvedLeanToolchain:
    selector: str
    sysroot: Path
    lean_path: Path
    lake_path: Path
    lean_sha256: str
    lake_sha256: str
    runtime_sha256: str
    lean_version: str
    lake_version: str

    def subprocess_environment(self) -> dict[str, str]:
        return _sanitized_tool_environment(self.sysroot)


def _sanitized_tool_environment(sysroot: Path | None = None) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in _BLOCKED_TOOL_ENVIRONMENT
        and not key.startswith("DYLD_")
        and not key.startswith("LD_")
    }
    trusted_paths = [] if sysroot is None else [str(sysroot / "bin")]
    trusted_paths.extend(("/usr/bin", "/bin", "/usr/sbin", "/sbin"))
    environment["PATH"] = os.pathsep.join(trusted_paths)
    return environment


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _toolchain_runtime_digest(sysroot: Path) -> str:
    """Bind launchers, shared runtime, and every importable sysroot OLean."""

    sysroot = sysroot.resolve()
    files = [sysroot / "bin/lean", sysroot / "bin/lake"]
    library_root = sysroot / "lib/lean"
    files.extend(
        path
        for path in library_root.iterdir()
        if path.is_file() and path.suffix in {".dylib", ".so", ".dll"}
    )
    files.extend(path for path in library_root.rglob("*.olean") if path.is_file())
    if len(files) <= 3 or any(not path.is_file() for path in files):
        raise ProofPolicyError("Lean runtime/OLean inventory is incomplete")
    digest = hashlib.sha256()
    for path in sorted(files):
        relative = path.relative_to(sysroot).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def lean_project_digest(repository_root: Path) -> str:
    """Hash every checked root-project Lean source and configuration file."""

    lean_root = repository_root.resolve() / "src/verification_bw/lean"
    candidates = sorted(lean_root.rglob("*.lean"))
    candidates.extend(
        path
        for name in (
            "lakefile.toml",
            "lakefile.lean",
            "lean-toolchain",
            "lake-manifest.json",
        )
        if (path := lean_root / name).is_file()
    )
    if not candidates:
        raise FileNotFoundError(f"Lean project has no source files: {lean_root}")
    digest = hashlib.sha256()
    for path in sorted(set(candidates)):
        relative = path.relative_to(lean_root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _strict_command_line(
    command: Sequence[str],
    *,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    environment: Mapping[str, str],
) -> str:
    completed = runner(
        list(command),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=30,
        env=dict(environment),
    )
    if (
        completed.returncode != 0
        or not isinstance(completed.stdout, str)
        or not isinstance(completed.stderr, str)
        or completed.stderr
    ):
        raise ProofPolicyError(f"toolchain identity command failed: {command[0]}")
    lines = completed.stdout.splitlines()
    if len(lines) != 1 or not lines[0]:
        raise ProofPolicyError(f"toolchain identity output is invalid: {command[0]}")
    return lines[0]


def resolve_lean_toolchain(
    repository_root: Path,
    *,
    policy: LeanToolchainPolicy | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> ResolvedLeanToolchain:
    """Resolve and validate the exact Lean/Lake binaries used by the gate."""

    root = repository_root.resolve()
    lean_root = root / "src/verification_bw/lean"
    expected = load_proof_policy(root).toolchain if policy is None else policy
    try:
        selector = (lean_root / "lean-toolchain").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as error:
        raise ProofPolicyError("cannot read Lean toolchain selector") from error
    if selector != expected.selector:
        raise ProofPolicyError("Lean toolchain selector does not match proof policy")

    launcher_name = shutil.which("lean")
    if launcher_name is None:
        raise ProofPolicyError("cannot resolve the Lean launcher")
    launcher = Path(launcher_name).resolve()
    discovery_environment = _sanitized_tool_environment()
    sysroot_text = _strict_command_line(
        (str(launcher), "--print-prefix"),
        cwd=lean_root,
        runner=runner,
        environment=discovery_environment,
    )
    sysroot = Path(sysroot_text).expanduser().resolve()
    if not sysroot.is_dir():
        raise ProofPolicyError("resolved Lean sysroot is not a directory")
    lean_path = (sysroot / "bin/lean").resolve()
    lake_path = (sysroot / "bin/lake").resolve()
    if not lean_path.is_file() or not lake_path.is_file():
        raise ProofPolicyError("resolved Lean sysroot has no Lean/Lake binaries")

    lean_version = _strict_command_line(
        (str(lean_path), "--version"),
        cwd=lean_root,
        runner=runner,
        environment=_sanitized_tool_environment(sysroot),
    )
    lake_version = _strict_command_line(
        (str(lake_path), "--version"),
        cwd=lean_root,
        runner=runner,
        environment=_sanitized_tool_environment(sysroot),
    )
    resolved = ResolvedLeanToolchain(
        selector=selector,
        sysroot=sysroot,
        lean_path=lean_path,
        lake_path=lake_path,
        lean_sha256=_file_sha256(lean_path),
        lake_sha256=_file_sha256(lake_path),
        runtime_sha256=_toolchain_runtime_digest(sysroot),
        lean_version=lean_version,
        lake_version=lake_version,
    )
    if (
        resolved.lean_sha256 != expected.lean_sha256
        or resolved.lake_sha256 != expected.lake_sha256
        or resolved.runtime_sha256 != expected.runtime_sha256
        or resolved.lean_version != expected.lean_version
        or resolved.lake_version != expected.lake_version
    ):
        raise ProofPolicyError(
            "resolved Lean/Lake identity does not match proof policy"
        )
    return resolved


def _relative_path(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProofPolicyError(f"{field} must be a non-empty string")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ProofPolicyError(f"{field} must be a normalized repository-relative path")
    return value


def _digest(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ProofPolicyError(f"{field} must be a lowercase SHA-256 digest")
    return value


def load_proof_policy(repository_root: Path) -> ProofPolicy:
    path = repository_root.resolve() / POLICY_RELATIVE_PATH
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProofPolicyError(f"cannot read proof policy {path}: {error}") from error
    if not isinstance(raw, dict) or set(raw) != {
        "schema_version",
        "allowed_axioms",
        "lean_project_sha256",
        "toolchain",
        "cases",
    }:
        raise ProofPolicyError("proof policy has unexpected top-level fields")
    if raw["schema_version"] != 3:
        raise ProofPolicyError("unsupported proof-policy schema version")
    allowed = raw["allowed_axioms"]
    if (
        not isinstance(allowed, list)
        or not allowed
        or any(not isinstance(item, str) or not item for item in allowed)
        or sorted(set(allowed)) != allowed
    ):
        raise ProofPolicyError("allowed_axioms must be a sorted unique string list")
    cases = raw["cases"]
    if not isinstance(cases, dict) or set(cases) != set(POLICY_CASES):
        raise ProofPolicyError(
            "proof policy must define exactly the five configured cases"
        )
    toolchain_raw = raw["toolchain"]
    if not isinstance(toolchain_raw, dict) or set(toolchain_raw) != {
        "selector",
        "lean_sha256",
        "lake_sha256",
        "runtime_sha256",
        "lean_version",
        "lake_version",
    }:
        raise ProofPolicyError("invalid Lean toolchain policy")
    for field in ("selector", "lean_version", "lake_version"):
        if not isinstance(toolchain_raw[field], str) or not toolchain_raw[field]:
            raise ProofPolicyError(f"toolchain.{field} must be non-empty")
    toolchain = LeanToolchainPolicy(
        selector=toolchain_raw["selector"],
        lean_sha256=_digest(toolchain_raw["lean_sha256"], "toolchain.lean_sha256"),
        lake_sha256=_digest(toolchain_raw["lake_sha256"], "toolchain.lake_sha256"),
        runtime_sha256=_digest(
            toolchain_raw["runtime_sha256"], "toolchain.runtime_sha256"
        ),
        lean_version=toolchain_raw["lean_version"],
        lake_version=toolchain_raw["lake_version"],
    )

    parsed: dict[str, ProofPolicyCase] = {}
    for case_id in POLICY_CASES:
        row = cases[case_id]
        if not isinstance(row, dict) or set(row) != {
            "module",
            "theorem",
            "proof_path",
            "elaborated_type_sha256",
            "contract",
        }:
            raise ProofPolicyError(f"invalid proof-policy fields for {case_id}")
        module = row["module"]
        theorem = row["theorem"]
        if not isinstance(module, str) or not module:
            raise ProofPolicyError(f"{case_id}.module must be non-empty")
        if not isinstance(theorem, str) or not theorem:
            raise ProofPolicyError(f"{case_id}.theorem must be non-empty")
        contract_raw = row["contract"]
        contract = None
        if contract_raw is not None:
            if not isinstance(contract_raw, dict) or set(contract_raw) != {
                "path",
                "sha256",
            }:
                raise ProofPolicyError(f"invalid contract binding for {case_id}")
            contract = ProtectedFile(
                path=_relative_path(contract_raw["path"], f"{case_id}.contract.path"),
                sha256=_digest(contract_raw["sha256"], f"{case_id}.contract.sha256"),
            )
        parsed[case_id] = ProofPolicyCase(
            module=module,
            theorem=theorem,
            proof_path=_relative_path(row["proof_path"], f"{case_id}.proof_path"),
            elaborated_type_sha256=_digest(
                row["elaborated_type_sha256"],
                f"{case_id}.elaborated_type_sha256",
            ),
            contract=contract,
        )
    return ProofPolicy(
        allowed_axioms=frozenset(allowed),
        lean_project_sha256=_digest(raw["lean_project_sha256"], "lean_project_sha256"),
        toolchain=toolchain,
        cases=parsed,
    )


def expected_lean_project_digest(repository_root: Path) -> str:
    """Return the reviewed root-project digest pinned by the tracked policy."""

    return load_proof_policy(repository_root).lean_project_sha256


def _strip_lean_comments_and_strings(source: str) -> str:
    """Replace nested comments and strings with spaces while preserving offsets."""

    output = list(source)
    index = 0
    while index < len(source):
        if source.startswith("--", index):
            end = source.find("\n", index + 2)
            if end < 0:
                end = len(source)
            for position in range(index, end):
                output[position] = " "
            index = end
            continue
        if source.startswith("/-", index):
            depth = 1
            cursor = index + 2
            while cursor < len(source) and depth:
                if source.startswith("/-", cursor):
                    depth += 1
                    cursor += 2
                elif source.startswith("-/", cursor):
                    depth -= 1
                    cursor += 2
                else:
                    cursor += 1
            if depth:
                raise ProofPolicyError("unterminated Lean block comment")
            for position in range(index, cursor):
                if output[position] != "\n":
                    output[position] = " "
            index = cursor
            continue
        if source[index] == '"':
            cursor = index + 1
            escaped = False
            while cursor < len(source):
                character = source[cursor]
                if character == '"' and not escaped:
                    cursor += 1
                    break
                if character == "\\" and not escaped:
                    escaped = True
                else:
                    escaped = False
                cursor += 1
            else:
                raise ProofPolicyError("unterminated Lean string literal")
            for position in range(index, cursor):
                if output[position] != "\n":
                    output[position] = " "
            index = cursor
            continue
        index += 1
    return "".join(output)


def _forbidden_tokens_absent(repository_root: Path) -> bool:
    lean_root = repository_root.resolve() / "src/verification_bw/lean"
    sources = sorted(lean_root.rglob("*.lean"))
    if not sources:
        return False
    for path in sources:
        try:
            stripped = _strip_lean_comments_and_strings(
                path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, ProofPolicyError):
            return False
        identifiers = set(_IDENTIFIER_RE.findall(stripped))
        if identifiers & FORBIDDEN_LEAN_IDENTIFIERS:
            return False
    return True


def elaborated_type_sha256(audit: ElaboratedTheoremAudit) -> str:
    """Hash the kernel-checked theorem type without relying on pretty-printing."""

    return canonical_sha256(
        {
            "schema": "lean-elaborated-theorem-v1",
            "level_parameters": list(audit.level_parameters),
            "type_encoding": audit.type_encoding,
        }
    )


def _string_list(value: object, field: str, *, sorted_unique: bool) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise ProofPolicyError(f"{field} must be a non-empty-string list")
    items = tuple(value)
    if len(set(items)) != len(items):
        raise ProofPolicyError(f"{field} must not contain duplicates")
    if sorted_unique and list(items) != sorted(items):
        raise ProofPolicyError(f"{field} must be sorted")
    return items


def _run_elaborated_audit(
    repository_root: Path,
    entry: ProofPolicyCase,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    toolchain: ResolvedLeanToolchain | None = None,
) -> ElaboratedTheoremAudit:
    """Read a theorem from Lean's checked environment using a fixed audit program."""

    root = repository_root.resolve()
    auditor = root / AUDITOR_RELATIVE_PATH
    if not auditor.is_file():
        raise ProofPolicyError(
            f"Lean proof auditor is missing: {AUDITOR_RELATIVE_PATH}"
        )
    active_toolchain = resolve_lean_toolchain(root) if toolchain is None else toolchain
    completed = runner(
        [
            str(active_toolchain.lake_path),
            "env",
            str(active_toolchain.lean_path),
            "--run",
            str(auditor),
            entry.module,
            entry.theorem,
        ],
        cwd=root / "src/verification_bw/lean",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=60,
        env=active_toolchain.subprocess_environment(),
    )
    if (
        completed.returncode != 0
        or not isinstance(completed.stdout, str)
        or not isinstance(completed.stderr, str)
        or completed.stderr
    ):
        raise ProofPolicyError("Lean elaborated-theorem audit failed")
    lines = completed.stdout.splitlines()
    if len(lines) != 1 or not lines[0].startswith(AUDIT_OUTPUT_PREFIX):
        raise ProofPolicyError("Lean elaborated-theorem audit emitted invalid output")
    try:
        raw = json.loads(lines[0][len(AUDIT_OUTPUT_PREFIX) :])
    except json.JSONDecodeError as error:
        raise ProofPolicyError(
            "Lean elaborated-theorem audit emitted invalid JSON"
        ) from error
    if not isinstance(raw, dict) or set(raw) != {
        "schema_version",
        "module",
        "theorem",
        "level_parameters",
        "type_encoding",
        "axioms",
    }:
        raise ProofPolicyError("Lean elaborated-theorem audit has unexpected fields")
    if raw["schema_version"] != 1:
        raise ProofPolicyError("unsupported Lean elaborated-theorem audit schema")
    if raw["module"] != entry.module or raw["theorem"] != entry.theorem:
        raise ProofPolicyError("Lean elaborated-theorem audit identity mismatch")
    type_encoding = raw["type_encoding"]
    if not isinstance(type_encoding, str) or not type_encoding:
        raise ProofPolicyError("Lean elaborated theorem type encoding is empty")
    return ElaboratedTheoremAudit(
        module=entry.module,
        theorem=entry.theorem,
        level_parameters=_string_list(
            raw["level_parameters"], "level_parameters", sorted_unique=False
        ),
        type_encoding=type_encoding,
        axioms=_string_list(raw["axioms"], "axioms", sorted_unique=True),
    )


def proof_policy_digest(repository_root: Path) -> str:
    """Bind policy data, checker dependencies, audit helper, and producers."""

    root = repository_root.resolve()
    policy = load_proof_policy(root)
    toolchain = resolve_lean_toolchain(root, policy=policy.toolchain)
    relatives = {POLICY_RELATIVE_PATH, AUDITOR_RELATIVE_PATH}
    for source_root, patterns in (
        (
            root / "src/workflow/verification/intrinsic_dashboard",
            ("*.py",),
        ),
        (
            root / "src/workflow/verification/lean_backend",
            ("*.py", "*.h"),
        ),
    ):
        for pattern in patterns:
            relatives.update(
                path.relative_to(root) for path in source_root.rglob(pattern)
            )
    lean_toolchain = Path("src/verification_bw/lean/lean-toolchain")
    relatives.add(lean_toolchain)
    files = {}
    for relative in sorted(relatives):
        path = root / relative
        if not path.is_file():
            raise ProofPolicyError(f"proof-policy TCB file is missing: {relative}")
        files[relative.as_posix()] = _file_sha256(path)
    executable = Path(sys.executable).resolve()
    if not executable.is_file():
        raise ProofPolicyError("Python proof-policy executable is missing")
    return canonical_sha256(
        {
            "schema": "proof-policy-tcb-v3",
            "files": files,
            "python": {
                "path": executable.as_posix(),
                "sha256": _file_sha256(executable),
                "version": sys.version,
            },
            "lean_toolchain": {
                "selector": toolchain.selector,
                "sysroot": toolchain.sysroot.as_posix(),
                "lean_path": toolchain.lean_path.as_posix(),
                "lake_path": toolchain.lake_path.as_posix(),
                "lean_sha256": toolchain.lean_sha256,
                "lake_sha256": toolchain.lake_sha256,
                "runtime_sha256": toolchain.runtime_sha256,
                "lean_version": toolchain.lean_version,
                "lake_version": toolchain.lake_version,
            },
            "clang_producer_sha256": clang_producer_digest(),
        }
    )


def run_proof_policy_checks(
    repository_root: Path,
    *,
    cases: Sequence[str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> Mapping[str, bool]:
    """Check protected statements/contracts, proof tokens, axioms, and mutations."""

    root = repository_root.resolve()
    selected = POLICY_CASES if cases is None else tuple(cases)
    unknown = sorted(set(selected) - set(POLICY_CASES))
    if unknown:
        raise ProofPolicyError(f"unknown proof-policy cases: {unknown}")
    result = {case_id: False for case_id in selected}
    try:
        policy = load_proof_policy(root)
        if lean_project_digest(root) != policy.lean_project_sha256:
            return result
        toolchain = resolve_lean_toolchain(root, policy=policy.toolchain)
        tokens_safe = _forbidden_tokens_absent(root)
        mutations = check_semantic_mutation_sensitivity(root)
    except (
        OSError,
        UnicodeError,
        RuntimeError,
        ValueError,
        subprocess.SubprocessError,
    ):
        return result

    for case_id in selected:
        entry = policy.cases[case_id]
        try:
            proof_path = root / entry.proof_path
            expected_proof_path = Path("src/verification_bw/lean") / (
                entry.module.replace(".", "/") + ".lean"
            )
            module_path_current = (
                entry.proof_path == expected_proof_path.as_posix()
                and proof_path.is_file()
            )
            contract_current = entry.contract is None or (
                (root / entry.contract.path).is_file()
                and _file_sha256(root / entry.contract.path) == entry.contract.sha256
            )
            audit = _run_elaborated_audit(
                root, entry, runner=runner, toolchain=toolchain
            )
            type_current = elaborated_type_sha256(audit) == entry.elaborated_type_sha256
            axiom_safe = set(audit.axioms) <= policy.allowed_axioms
            result[case_id] = bool(
                tokens_safe
                and mutations.get(case_id, False)
                and module_path_current
                and type_current
                and contract_current
                and axiom_safe
            )
        except (
            OSError,
            UnicodeError,
            RuntimeError,
            ValueError,
            subprocess.SubprocessError,
        ):
            result[case_id] = False
    return result
