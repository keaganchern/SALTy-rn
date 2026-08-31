"""Generate the first registry-bound Neon/RVV syntax manifest."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Sequence

from .binding import build_manifest, canonical_json
from .emit_lean import emit_qs8_vadd_minmax_pair
from .frontend import KernelExtraction, parse_kernel


_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def _atomic_write_text(path: Path, text: str, *, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
            temporary_path = Path(stream.name)
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _extract_pair(
    *,
    repository_root: str | Path,
    source: str | Path | None = None,
    target: str | Path | None = None,
    facade: str | Path | None = None,
    clang: str = "clang",
) -> tuple[Path, KernelExtraction, KernelExtraction]:
    """Parse the current pair once for manifest and optional Lean emission."""

    root = Path(repository_root).resolve()
    source_path = Path(source).resolve() if source else root / "kernels/source/qs8-vadd-minmax.c"
    target_path = Path(target).resolve() if target else root / "kernels/target/qs8-vadd-minmax.c"
    facade_path = (
        Path(facade).resolve()
        if facade
        else root / "src/workflow/verification/lean_backend/facade/qs8_vadd_minmax.h"
    )
    neon = parse_kernel(
        source_path, function_name="test_neon", clang=clang, facade=facade_path
    )
    rvv = parse_kernel(
        target_path, function_name="test_rvv", clang=clang, facade=facade_path
    )
    return root, neon, rvv


def generate_manifest(
    *,
    repository_root: str | Path = _REPOSITORY_ROOT,
    source: str | Path | None = None,
    target: str | Path | None = None,
    facade: str | Path | None = None,
    clang: str = "clang",
) -> dict:
    """Parse and bind the current ``qs8-vadd-minmax`` kernel pair."""

    root, neon, rvv = _extract_pair(
        repository_root=repository_root,
        source=source,
        target=target,
        facade=facade,
        clang=clang,
    )
    return build_manifest(neon, rvv, workspace_root=root)


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=_REPOSITORY_ROOT)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--facade", type=Path)
    parser.add_argument("--clang", default="clang")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--lean-out",
        type=Path,
        help="explicit path for the generated Lean block-model module",
    )
    parser.add_argument("--compact", action="store_true")
    arguments = parser.parse_args(argv)

    root, neon, rvv = _extract_pair(
        repository_root=arguments.repository_root,
        source=arguments.source,
        target=arguments.target,
        facade=arguments.facade,
        clang=arguments.clang,
    )
    manifest = build_manifest(neon, rvv, workspace_root=root)
    rendered = canonical_json(manifest, pretty=not arguments.compact)
    emitted_text = (
        emit_qs8_vadd_minmax_pair(neon, rvv).module_text
        if arguments.lean_out is not None
        else None
    )
    if arguments.output is None:
        sys.stdout.write(rendered)
    else:
        _atomic_write_text(arguments.output, rendered, encoding="ascii")
    if arguments.lean_out is not None and emitted_text is not None:
        _atomic_write_text(arguments.lean_out, emitted_text, encoding="ascii")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
