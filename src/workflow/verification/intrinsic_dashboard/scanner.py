"""Fail-closed lexical intrinsic inventory for the pinned XNNPACK gitlink.

This module deliberately does not claim to parse C or establish intrinsic
semantics.  It reads the generated XNNPACK C microkernel manifests from the
commit pinned by the parent repository and counts direct call-shaped tokens:

* ``v...(...)`` in Neon-family manifest entries; and
* ``__riscv_...(...)`` in RVV-family manifest entries.

The result is a reproducible lexical candidate inventory.  Typed Clang AST
extraction and semantic review are separate gates.
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Collection, Iterable, Literal, Sequence


Architecture = Literal["neon", "rvv"]
LEXICAL_METHOD = "direct-call-lexical-v1"

_OID_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_FAMILY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MANIFEST_RE = re.compile(
    r"^cmake/gen/(?P<variant>(?:neon|rvv)[a-z0-9_]*)_microkernels\.cmake$"
)
_SET_START_RE = re.compile(
    r"^SET\((?P<tier>PROD|NON_PROD)_(?P<variant>[A-Z0-9_]+)"
    r"_MICROKERNEL_SRCS(?P<remainder>.*)$"
)
_NEON_CALL_RE = re.compile(r"\b(v[A-Za-z][A-Za-z0-9_]*)\s*\(")
_RVV_CALL_RE = re.compile(r"\b(__riscv_[A-Za-z0-9_]+)\s*\(")
_NEON_EXCLUSIONS = frozenset({"void"})


class InventoryScanError(RuntimeError):
    """The pinned repository or lexical inventory failed validation."""


@dataclass(frozen=True, order=True)
class MicrokernelProgram:
    """One C program selected by an architecture manifest."""

    architecture: Architecture
    production: bool
    family: str
    path: str
    manifest_path: str


@dataclass(frozen=True, order=True)
class IntrinsicUsage:
    """Occurrences of one direct lexical callee in one concrete program."""

    architecture: Architecture
    operator: str
    family: str
    program_path: str
    production: bool
    occurrences: int


@dataclass(frozen=True, order=True)
class OperatorSummary:
    """Aggregate relations for one architecture-specific lexical operator."""

    architecture: Architecture
    operator: str
    occurrences: int
    family_count: int
    program_count: int
    production_occurrences: int
    production_family_count: int
    production_program_count: int


@dataclass(frozen=True)
class LexicalInventory:
    """Deterministic inventory tied to a parent gitlink commit."""

    pinned_commit: str
    method: str
    manifests: tuple[str, ...]
    programs: tuple[MicrokernelProgram, ...]
    usages: tuple[IntrinsicUsage, ...]

    def operator_summaries(self) -> tuple[OperatorSummary, ...]:
        grouped: dict[tuple[Architecture, str], list[IntrinsicUsage]] = defaultdict(
            list
        )
        for usage in self.usages:
            grouped[(usage.architecture, usage.operator)].append(usage)

        summaries = []
        for (architecture, operator), usages in grouped.items():
            production = [usage for usage in usages if usage.production]
            summaries.append(
                OperatorSummary(
                    architecture=architecture,
                    operator=operator,
                    occurrences=sum(usage.occurrences for usage in usages),
                    family_count=len({usage.family for usage in usages}),
                    program_count=len({usage.program_path for usage in usages}),
                    production_occurrences=sum(
                        usage.occurrences for usage in production
                    ),
                    production_family_count=len({usage.family for usage in production}),
                    production_program_count=len(
                        {usage.program_path for usage in production}
                    ),
                )
            )
        return tuple(sorted(summaries))


def _run_git(
    arguments: Sequence[str],
    *,
    cwd: Path | None = None,
    git_dir: Path | None = None,
    input_bytes: bytes | None = None,
) -> bytes:
    command = ["git"]
    if git_dir is not None:
        command.append(f"--git-dir={git_dir}")
    if cwd is not None:
        command.extend(("-C", str(cwd)))
    command.extend(arguments)
    try:
        completed = subprocess.run(
            command,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as error:
        raise InventoryScanError(f"could not execute git: {error}") from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise InventoryScanError(
            f"git command failed ({' '.join(command)}): {detail or 'no stderr'}"
        )
    return completed.stdout


def pinned_submodule_commit(
    repository_root: Path,
    submodule_path: PurePosixPath = PurePosixPath("benchmark/XNNPACK"),
) -> str:
    """Read and validate the submodule commit recorded by the parent ``HEAD``."""

    repository_root = repository_root.resolve()
    raw = _run_git(
        ("ls-tree", "-z", "HEAD", "--", submodule_path.as_posix()),
        cwd=repository_root,
    )
    records = [record for record in raw.split(b"\0") if record]
    if len(records) != 1:
        raise InventoryScanError(
            f"expected one gitlink for {submodule_path}, found {len(records)}"
        )
    try:
        metadata, recorded_path = records[0].split(b"\t", 1)
        mode, object_type, oid = metadata.decode("ascii").split()
        path = recorded_path.decode("utf-8")
    except (UnicodeDecodeError, ValueError) as error:
        raise InventoryScanError("malformed parent ls-tree gitlink record") from error
    if mode != "160000" or object_type != "commit":
        raise InventoryScanError(
            f"{submodule_path} is not a gitlink: mode={mode}, type={object_type}"
        )
    if path != submodule_path.as_posix() or not _OID_RE.fullmatch(oid):
        raise InventoryScanError(
            f"unexpected gitlink path or object id: path={path!r}, oid={oid!r}"
        )
    return oid


def _discover_object_git_dir(
    repository_root: Path,
    submodule_path: PurePosixPath,
    pinned_commit: str,
    explicit_git_dir: Path | None,
) -> Path:
    if explicit_git_dir is not None:
        git_dir = explicit_git_dir.resolve()
    else:
        checkout = repository_root.joinpath(*submodule_path.parts)
        checkout_git_dir: Path | None = None
        if checkout.is_dir():
            try:
                raw_git_dir = _run_git(
                    ("rev-parse", "--absolute-git-dir"), cwd=checkout
                )
                checkout_git_dir = Path(raw_git_dir.decode("utf-8").strip())
                checkout_head = _run_git(("rev-parse", "HEAD"), cwd=checkout)
                actual_head = checkout_head.decode("ascii").strip()
                if actual_head != pinned_commit:
                    raise InventoryScanError(
                        "XNNPACK checkout HEAD does not match the parent gitlink: "
                        f"checkout={actual_head}, pinned={pinned_commit}"
                    )
            except InventoryScanError as error:
                if "checkout HEAD does not match" in str(error):
                    raise
                checkout_git_dir = None
        if checkout_git_dir is not None:
            git_dir = checkout_git_dir
        else:
            relative_modules_path = f"modules/{submodule_path.as_posix()}"
            raw_git_dir = _run_git(
                ("rev-parse", "--git-path", relative_modules_path),
                cwd=repository_root,
            )
            git_dir = Path(raw_git_dir.decode("utf-8").strip())
            if not git_dir.is_absolute():
                git_dir = (repository_root / git_dir).resolve()

    if not git_dir.is_dir():
        raise InventoryScanError(f"XNNPACK object database is unavailable: {git_dir}")
    _run_git(("cat-file", "-e", f"{pinned_commit}^{{commit}}"), git_dir=git_dir)
    return git_dir


def _tree_blob_paths(git_dir: Path, commit: str) -> tuple[str, ...]:
    raw = _run_git(
        ("ls-tree", "-r", "-z", "--full-tree", commit, "--", "cmake/gen"),
        git_dir=git_dir,
    )
    paths = []
    for record in (record for record in raw.split(b"\0") if record):
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, oid = metadata.decode("ascii").split()
            path = raw_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as error:
            raise InventoryScanError("malformed XNNPACK ls-tree record") from error
        if object_type != "blob" or mode not in {"100644", "100755"}:
            continue
        if not _OID_RE.fullmatch(oid):
            raise InventoryScanError(f"malformed blob object id for {path}: {oid}")
        paths.append(path)
    return tuple(sorted(paths))


def _read_blobs(git_dir: Path, commit: str, paths: Iterable[str]) -> dict[str, str]:
    ordered_paths = tuple(paths)
    if len(set(ordered_paths)) != len(ordered_paths):
        raise InventoryScanError("duplicate paths requested from git cat-file")
    if not ordered_paths:
        return {}
    for path in ordered_paths:
        if "\n" in path or "\r" in path or ":" in path:
            raise InventoryScanError(f"unsupported git object path: {path!r}")

    requests = b"".join(f"{commit}:{path}\n".encode("utf-8") for path in ordered_paths)
    raw = _run_git(("cat-file", "--batch"), git_dir=git_dir, input_bytes=requests)
    offset = 0
    result: dict[str, str] = {}
    for path in ordered_paths:
        header_end = raw.find(b"\n", offset)
        if header_end < 0:
            raise InventoryScanError(f"truncated cat-file header for {path}")
        header = raw[offset:header_end]
        offset = header_end + 1
        if header.endswith(b" missing"):
            raise InventoryScanError(
                f"manifest references a path absent from {commit}: {path}"
            )
        try:
            _oid, object_type, raw_size = header.decode("ascii").split()
            size = int(raw_size)
        except (UnicodeDecodeError, ValueError) as error:
            raise InventoryScanError(
                f"malformed cat-file header for {path}: {header!r}"
            ) from error
        if object_type != "blob" or size < 0 or offset + size >= len(raw):
            raise InventoryScanError(f"invalid cat-file blob record for {path}")
        content = raw[offset : offset + size]
        offset += size
        if raw[offset : offset + 1] != b"\n":
            raise InventoryScanError(f"missing cat-file separator after {path}")
        offset += 1
        try:
            result[path] = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise InventoryScanError(
                f"non-UTF-8 C source or manifest: {path}"
            ) from error
    if offset != len(raw):
        raise InventoryScanError("unexpected trailing data from git cat-file")
    return result


def _manifest_variant(manifest_path: str) -> tuple[Architecture, str]:
    match = _MANIFEST_RE.fullmatch(manifest_path)
    if match is None:
        raise InventoryScanError(f"unsupported manifest path: {manifest_path}")
    variant = match.group("variant")
    architecture: Architecture = "rvv" if variant.startswith("rvv") else "neon"
    return architecture, variant.upper()


def _validate_program_path(path: str, manifest_path: str) -> str:
    pure_path = PurePosixPath(path)
    if (
        pure_path.is_absolute()
        or ".." in pure_path.parts
        or len(pure_path.parts) < 3
        or pure_path.parts[0] != "src"
        or pure_path.suffix != ".c"
    ):
        raise InventoryScanError(
            f"invalid C microkernel path in {manifest_path}: {path!r}"
        )
    family = pure_path.parts[1]
    if not _FAMILY_RE.fullmatch(family):
        raise InventoryScanError(
            f"invalid kernel family in {manifest_path}: {family!r}"
        )
    return family


def parse_microkernel_manifest(
    content: str, manifest_path: str
) -> tuple[MicrokernelProgram, ...]:
    """Strictly parse the two generated C source lists in one manifest."""

    architecture, expected_variant = _manifest_variant(manifest_path)
    expected_variables = {
        "PROD": f"PROD_{expected_variant}_MICROKERNEL_SRCS",
        "NON_PROD": f"NON_PROD_{expected_variant}_MICROKERNEL_SRCS",
    }
    lists: dict[str, list[str]] = {}
    lines = content.splitlines()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        match = _SET_START_RE.fullmatch(stripped)
        if match is None:
            index += 1
            continue
        tier = match.group("tier")
        variable = f"{tier}_{match.group('variant')}_MICROKERNEL_SRCS"
        if variable != expected_variables[tier]:
            raise InventoryScanError(
                f"unexpected source-list variable in {manifest_path}: {variable}"
            )
        if tier in lists:
            raise InventoryScanError(f"duplicate {tier} source list in {manifest_path}")

        remainder = match.group("remainder").strip()
        paths: list[str] = []
        if remainder == ")":
            lists[tier] = paths
            index += 1
            continue
        if remainder:
            raise InventoryScanError(
                f"unsupported text after {variable} in {manifest_path}: {remainder!r}"
            )

        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            closes = candidate.endswith(")")
            if closes:
                candidate = candidate[:-1].strip()
            if candidate:
                if candidate.startswith("#") or any(
                    char.isspace() for char in candidate
                ):
                    raise InventoryScanError(
                        f"unsupported source-list entry in {manifest_path}: "
                        f"{candidate!r}"
                    )
                paths.append(candidate)
            index += 1
            if closes:
                break
        else:
            raise InventoryScanError(f"unterminated {variable} list in {manifest_path}")
        lists[tier] = paths

    if set(lists) != set(expected_variables):
        missing = sorted(set(expected_variables) - set(lists))
        raise InventoryScanError(
            f"missing source lists in {manifest_path}: {', '.join(missing)}"
        )

    seen_paths: set[str] = set()
    programs = []
    for tier in ("PROD", "NON_PROD"):
        production = tier == "PROD"
        for path in lists[tier]:
            if path in seen_paths:
                raise InventoryScanError(
                    f"duplicate C microkernel path in {manifest_path}: {path}"
                )
            seen_paths.add(path)
            family = _validate_program_path(path, manifest_path)
            programs.append(
                MicrokernelProgram(
                    architecture=architecture,
                    production=production,
                    family=family,
                    path=path,
                    manifest_path=manifest_path,
                )
            )
    return tuple(sorted(programs))


def _without_comments_and_literals(source: str, path: str) -> str:
    output: list[str] = []
    index = 0
    state = "normal"
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if state == "normal":
            if char == "/" and following == "/":
                output.extend((" ", " "))
                index += 2
                state = "line-comment"
                continue
            if char == "/" and following == "*":
                output.extend((" ", " "))
                index += 2
                state = "block-comment"
                continue
            if char == '"':
                output.append(" ")
                index += 1
                state = "string"
                continue
            if char == "'":
                output.append(" ")
                index += 1
                state = "character"
                continue
            output.append(char)
            index += 1
            continue

        if state == "line-comment":
            output.append("\n" if char == "\n" else " ")
            index += 1
            if char == "\n":
                state = "normal"
            continue

        if state == "block-comment":
            if char == "*" and following == "/":
                output.extend((" ", " "))
                index += 2
                state = "normal"
            else:
                output.append("\n" if char == "\n" else " ")
                index += 1
            continue

        delimiter = '"' if state == "string" else "'"
        if char == "\\":
            output.append(" ")
            index += 1
            if index < len(source):
                output.append("\n" if source[index] == "\n" else " ")
                index += 1
            continue
        if char == delimiter:
            output.append(" ")
            index += 1
            state = "normal"
            continue
        output.append("\n" if char == "\n" else " ")
        index += 1

    if state not in {"normal", "line-comment"}:
        raise InventoryScanError(f"unterminated C lexical construct in {path}: {state}")
    return "".join(output)


def lexical_call_counts(
    architecture: Architecture, source: str, path: str
) -> Counter[str]:
    """Return direct call-shaped candidates from one C source string.

    This is the same deliberately lexical method used for the pinned XNNPACK
    inventory.  It does not establish that a callee is declared by an ISA header.
    """

    cleaned = _without_comments_and_literals(source, path)
    expression = _NEON_CALL_RE if architecture == "neon" else _RVV_CALL_RE
    counts = Counter(match.group(1) for match in expression.finditer(cleaned))
    if architecture == "neon":
        for excluded in _NEON_EXCLUSIONS:
            counts.pop(excluded, None)
    return counts


# Kept private for compatibility with the original scanner tests and callers.
_lexical_call_counts = lexical_call_counts


def scan_pinned_xnnpack(
    repository_root: Path,
    *,
    submodule_path: PurePosixPath = PurePosixPath("benchmark/XNNPACK"),
    families: Collection[str] | None = None,
    xnnpack_git_dir: Path | None = None,
) -> LexicalInventory:
    """Scan direct call-shaped intrinsic candidates at the pinned gitlink.

    ``families`` limits concrete program rows after strict manifest parsing.  It
    does not change the pinned commit or permit fuzzy family matching.
    """

    repository_root = repository_root.resolve()
    if families is None:
        family_filter = None
    else:
        family_filter = frozenset(families)
        malformed = sorted(
            family for family in family_filter if not _FAMILY_RE.fullmatch(family)
        )
        if malformed:
            raise InventoryScanError(f"malformed family filters: {malformed}")

    commit = pinned_submodule_commit(repository_root, submodule_path)
    git_dir = _discover_object_git_dir(
        repository_root, submodule_path, commit, xnnpack_git_dir
    )
    all_tree_paths = _tree_blob_paths(git_dir, commit)
    manifest_paths = tuple(
        path for path in all_tree_paths if _MANIFEST_RE.fullmatch(path)
    )
    architecture_counts = Counter(_manifest_variant(path)[0] for path in manifest_paths)
    if architecture_counts["neon"] == 0 or architecture_counts["rvv"] == 0:
        raise InventoryScanError(
            "pinned XNNPACK tree must contain both Neon and RVV C manifests"
        )

    manifest_contents = _read_blobs(git_dir, commit, manifest_paths)
    programs_by_path: dict[str, MicrokernelProgram] = {}
    for manifest_path in manifest_paths:
        for program in parse_microkernel_manifest(
            manifest_contents[manifest_path], manifest_path
        ):
            if family_filter is not None and program.family not in family_filter:
                continue
            previous = programs_by_path.get(program.path)
            if previous is not None:
                raise InventoryScanError(
                    "C microkernel appears in multiple architecture/tier manifests: "
                    f"{program.path} ({previous.manifest_path}, "
                    f"{program.manifest_path})"
                )
            programs_by_path[program.path] = program

    programs = tuple(sorted(programs_by_path.values()))
    source_contents = _read_blobs(
        git_dir, commit, (program.path for program in programs)
    )
    usages = []
    for program in programs:
        counts = lexical_call_counts(
            program.architecture, source_contents[program.path], program.path
        )
        for operator, occurrences in counts.items():
            if occurrences <= 0:
                raise InventoryScanError(
                    f"invalid lexical occurrence count for {operator}: {occurrences}"
                )
            usages.append(
                IntrinsicUsage(
                    architecture=program.architecture,
                    operator=operator,
                    family=program.family,
                    program_path=program.path,
                    production=program.production,
                    occurrences=occurrences,
                )
            )

    return LexicalInventory(
        pinned_commit=commit,
        method=LEXICAL_METHOD,
        manifests=manifest_paths,
        programs=programs,
        usages=tuple(sorted(usages)),
    )
