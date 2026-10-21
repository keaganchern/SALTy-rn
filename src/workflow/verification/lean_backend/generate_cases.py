"""Generate reviewed Lean models and protected obligations for scale-up cases."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .binding import registry_content_digest
from .case_emit import emit_case_pair
from .frontend import parse_kernel
from .generate import _atomic_write_text
from .model_profiles import SCALE_UP_MODELS
from .obligation_emit import (
    emit_binary_prefix_tail_obligation,
    emit_unary_prefix_tail_obligation,
)
from .profiles import FRONTEND_PROFILES
from .scaleup_catalog import SCALEUP_CATALOGS


_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_CASE_ORDER = (
    "s8-vclamp",
    "qs8-vcvt",
    "qs8-vlrelu",
    "qu8-vadd-minmax",
)


def generate_case_modules(
    *,
    repository_root: str | Path = _REPOSITORY_ROOT,
    cases: Sequence[str] = _CASE_ORDER,
    clang: str = "clang",
) -> dict[str, str]:
    """Parse every requested C pair and return validated Lean module text."""

    root = Path(repository_root).resolve()
    generated: dict[str, str] = {}
    for case_id in cases:
        try:
            frontend_profile = FRONTEND_PROFILES[case_id]
            model_profile = SCALE_UP_MODELS[case_id]
            catalog = SCALEUP_CATALOGS[case_id]
        except KeyError as error:
            raise ValueError(f"unknown scale-up case {case_id!r}") from error
        if case_id in generated:
            raise ValueError(f"duplicate scale-up case {case_id!r}")

        neon = parse_kernel(
            root / "kernels" / "source" / f"{case_id}.c",
            clang=clang,
            profile=frontend_profile.neon,
        )
        rvv = parse_kernel(
            root / "kernels" / "target" / f"{case_id}.c",
            clang=clang,
            profile=frontend_profile.rvv,
        )
        registry_sha256 = registry_content_digest(
            f"{case_id}-intrinsics", catalog.registry
        )
        emission = emit_case_pair(
            neon,
            rvv,
            profile=model_profile,
            neon_registry=catalog.registry,
            rvv_registry=catalog.registry,
            registry_sha256=registry_sha256,
        )
        generated[case_id] = emission.emitted.module_text
    return generated


def generated_module_path(
    repository_root: str | Path, case_id: str
) -> Path:
    root = Path(repository_root).resolve()
    try:
        directory = SCALE_UP_MODELS[case_id].generated_directory
    except KeyError as error:
        raise ValueError(f"unknown scale-up case {case_id!r}") from error
    return (
        root
        / "src"
        / "verification_bw"
        / "lean"
        / "SALT"
        / "Generated"
        / directory
        / "Models.lean"
    )


def generate_case_obligations(
    *,
    cases: Sequence[str] = _CASE_ORDER,
) -> dict[str, str]:
    """Return deterministic protected obligations for configured loop profiles."""

    generated: dict[str, str] = {}
    for case_id in cases:
        try:
            profile = SCALE_UP_MODELS[case_id]
        except KeyError as error:
            raise ValueError(f"unknown scale-up case {case_id!r}") from error
        if (
            profile.unary_prefix_tail_obligation is None
            and profile.binary_prefix_tail_obligation is None
        ):
            continue
        if case_id in generated:
            raise ValueError(f"duplicate scale-up obligation {case_id!r}")
        if profile.unary_prefix_tail_obligation is not None:
            generated[case_id] = emit_unary_prefix_tail_obligation(profile)
        else:
            generated[case_id] = emit_binary_prefix_tail_obligation(profile)
    return generated


def generated_obligation_path(
    repository_root: str | Path, case_id: str
) -> Path:
    root = Path(repository_root).resolve()
    try:
        profile = SCALE_UP_MODELS[case_id]
    except KeyError as error:
        raise ValueError(f"unknown scale-up case {case_id!r}") from error
    if (
        profile.unary_prefix_tail_obligation is None
        and profile.binary_prefix_tail_obligation is None
    ):
        raise ValueError(f"case {case_id!r} has no generated obligation")
    return (
        root
        / "src"
        / "verification_bw"
        / "lean"
        / "SALT"
        / "Generated"
        / profile.generated_directory
        / "Obligation.lean"
    )


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=_REPOSITORY_ROOT)
    parser.add_argument("--clang", default="clang")
    parser.add_argument(
        "--case",
        action="append",
        choices=_CASE_ORDER,
        dest="cases",
        help="generate one case; repeat to select several (default: all)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if checked-in modules differ instead of writing them",
    )
    arguments = parser.parse_args(argv)

    cases = tuple(arguments.cases) if arguments.cases else _CASE_ORDER
    generated = generate_case_modules(
        repository_root=arguments.repository_root,
        cases=cases,
        clang=arguments.clang,
    )
    obligations = generate_case_obligations(cases=cases)
    artifacts = {
        generated_module_path(arguments.repository_root, case_id): module_text
        for case_id, module_text in generated.items()
    }
    artifacts.update(
        {
            generated_obligation_path(arguments.repository_root, case_id): module_text
            for case_id, module_text in obligations.items()
        }
    )
    stale: list[Path] = []
    for path, module_text in artifacts.items():
        if arguments.check:
            if not path.is_file() or path.read_text(encoding="ascii") != module_text:
                stale.append(path)
        else:
            _atomic_write_text(path, module_text, encoding="ascii")
            sys.stdout.write(f"generated {path}\n")
    if stale:
        for path in stale:
            sys.stderr.write(f"stale generated artifact: {path}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
