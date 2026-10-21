"""Shared, immutable Lean toolchain and staged-compilation helpers."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .schema import canonical_sha256


ALLOWED_AXIOMS = frozenset({"Classical.choice", "Quot.sound", "propext"})
_AXIOM_LINE_RE = re.compile(r"depends on axioms:\s*\[(?P<axioms>[^]]*)\]")


class LeanCheckError(RuntimeError):
    """A pinned Lean toolchain or staged check could not be completed."""


@dataclass(frozen=True, slots=True)
class Toolchain:
    lean: Path
    lake: Path
    sysroot: Path
    sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _command(
    arguments: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str] | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(arguments),
            cwd=cwd,
            env=None if environment is None else dict(environment),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise LeanCheckError(f"could not run {arguments[0]!r}: {error}") from error


def _resolve_toolchain(repository_root: Path) -> Toolchain:
    lean_project = repository_root / "src/verification_bw/lean"
    selector_path = lean_project / "lean-toolchain"
    selector = selector_path.read_text(encoding="utf-8").strip()
    launcher = shutil.which("lean")
    lake_launcher = shutil.which("lake")
    if not selector or launcher is None or lake_launcher is None:
        raise LeanCheckError("Lean selector and Lean/Lake launchers are required")
    prefix = _command((launcher, "--print-prefix"), cwd=lean_project)
    if prefix.returncode != 0 or prefix.stderr or len(prefix.stdout.splitlines()) != 1:
        raise LeanCheckError("Lean did not report one trusted sysroot")
    sysroot = Path(prefix.stdout.strip()).resolve()
    lean = (sysroot / "bin/lean").resolve()
    lake = (sysroot / "bin/lake").resolve()
    if not lean.is_file() or not lake.is_file():
        raise LeanCheckError("resolved Lean sysroot is incomplete")
    lean_version = _command((str(lean), "--version"), cwd=lean_project)
    lake_version = _command((str(lake), "--version"), cwd=lean_project)
    if lean_version.returncode != 0 or lake_version.returncode != 0:
        raise LeanCheckError("Lean/Lake version query failed")
    identity = {
        "selector": selector,
        "lean_sha256": _sha256(lean),
        "lake_sha256": _sha256(lake),
        "lean_version": lean_version.stdout.strip(),
        "lake_version": lake_version.stdout.strip(),
    }
    return Toolchain(lean, lake, sysroot, canonical_sha256(identity))


_LEAN_DEPENDENCIES = (
    "SALT/Basic.lean",
    "SALT/Intrinsics/FP32.lean",
    "SALT/Intrinsics/Neon.lean",
    "SALT/Intrinsics/RVV.lean",
    "SALT/Kernel/Schedule.lean",
    "SALT/Kernel/ElementwiseTwoPhase.lean",
    "SALT/Kernel/ElementwiseFamily.lean",
)


def _compile(
    toolchain: Toolchain,
    stage: Path,
    environment: Mapping[str, str],
    path: Path,
    *,
    emit_olean: bool,
) -> subprocess.CompletedProcess[str]:
    arguments = [str(toolchain.lean), "-R", str(stage)]
    if emit_olean:
        arguments.extend(("-o", str(path.with_suffix(".olean"))))
    arguments.append(str(path))
    return _command(arguments, cwd=stage, environment=environment)


def _build_staged_dependencies(
    repository_root: Path,
    toolchain: Toolchain,
    stage: Path,
    environment: Mapping[str, str],
) -> None:
    lean_root = repository_root / "src/verification_bw/lean"
    for relative_text in _LEAN_DEPENDENCIES:
        relative = Path(relative_text)
        source = lean_root / relative
        destination = stage / relative
        if not source.is_file():
            raise LeanCheckError(f"Lean dependency source is absent: {relative_text}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        completed = _compile(
            toolchain, stage, environment, destination, emit_olean=True
        )
        if completed.returncode != 0:
            raise LeanCheckError(
                f"Lean dependency {relative_text} failed:\n"
                f"{completed.stdout}{completed.stderr}"
            )


def _stage(
    repository_root: Path,
    output: Path,
    namespace: str,
    toolchain: Toolchain,
    *,
    include_proof: bool,
) -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, str]]:
    temporary = tempfile.TemporaryDirectory(prefix="saltyrn-elementwise-lean-")
    root = Path(temporary.name).resolve()
    environment = {
        **os.environ,
        "LEAN_PATH": os.pathsep.join((str(root), str(toolchain.sysroot / "lib/lean"))),
    }
    _build_staged_dependencies(repository_root, toolchain, root, environment)
    module_directory = root.joinpath(*namespace.split("."))
    module_directory.mkdir(parents=True, exist_ok=True)
    for name in ("Models.lean", "Spec.lean"):
        shutil.copyfile(output / name, module_directory / name)
    if include_proof:
        shutil.copyfile(output / "Proof.lean", module_directory / "Proof.lean")
    return temporary, root, environment


def _checked_axioms(output: str) -> frozenset[str]:
    match = _AXIOM_LINE_RE.search(output)
    if match is None:
        if "does not depend on any axioms" in output:
            return frozenset()
        raise LeanCheckError("Lean did not report the theorem's transitive axioms")
    body = match.group("axioms").strip()
    return frozenset(item.strip() for item in body.split(",") if item.strip())
