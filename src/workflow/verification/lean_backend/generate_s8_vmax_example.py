"""Generate the synthetic S8 vmax teaching example through the real backend."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .binding import registry_content_digest
from .case_emit import CaseEmission, emit_case_pair
from .frontend import parse_kernel
from .generate import _atomic_write_text
from .model_profiles import ModelProfile, ParameterField
from .profiles import (
    FrontendAssertion,
    FrontendIntrinsicSpec,
    FrontendProfile,
    FrontendSideProfile,
)
from .scaleup_catalog import KernelIntrinsicCatalog, S8_VCLAMP_CATALOG
from .schema import Architecture, IntrinsicSpec, render_clang_function_type


_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_FACADE = Path(__file__).with_name("facade") / "s8_vmax_example.h"

_NEON_NAMES = (
    "vdupq_n_s8",
    "vld1q_s8",
    "vmaxq_s8",
    "vminq_s8",
    "vst1q_s8",
)
_RVV_NAMES = (
    "__riscv_vsetvl_e8m8",
    "__riscv_vle8_v_i8m8",
    "__riscv_vmax_vx_i8m8",
    "__riscv_vse8_v_i8m8",
)


def _select_specs(names: tuple[str, ...]) -> tuple[IntrinsicSpec, ...]:
    return tuple(S8_VCLAMP_CATALOG.registry[name] for name in names)


S8_VMAX_EXAMPLE_CATALOG = KernelIntrinsicCatalog(
    "s8-vmax-example",
    _select_specs(_NEON_NAMES),
    _select_specs(_RVV_NAMES),
)


def _frontend_specs(
    specs: tuple[IntrinsicSpec, ...]
) -> tuple[FrontendIntrinsicSpec, ...]:
    return tuple(
        FrontendIntrinsicSpec(
            spelling=spec.spelling,
            arity=len(spec.signature.parameters),
            function_type=render_clang_function_type(spec.signature),
        )
        for spec in specs
    )


_PARAMETERS = (
    ("batch", "unsigned long"),
    ("input", "const int8_t *"),
    ("output", "int8_t *"),
    ("params", "const struct salt_s8_vmax_params *restrict"),
)
_FUNCTION_TYPE = (
    "void (size_t, const int8_t *, int8_t *, "
    "const struct salt_s8_vmax_params *restrict)"
)

S8_VMAX_EXAMPLE_FRONTEND = FrontendProfile(
    kernel_name="s8-vmax-example",
    neon=FrontendSideProfile(
        architecture=Architecture.NEON,
        facade_path=_FACADE,
        intrinsic_specs=_frontend_specs(S8_VMAX_EXAMPLE_CATALOG.neon_specs),
        function_name="test_neon",
        target_triple="aarch64-none-elf",
        function_type=_FUNCTION_TYPE,
        parameters=_PARAMETERS,
        assertions=(
            FrontendAssertion("assert(batch!=0);", None),
            FrontendAssertion("assert(batch%16==0);", None),
            FrontendAssertion("assert(input!=NULL);", None),
            FrontendAssertion("assert(output!=NULL);", None),
        ),
    ),
    rvv=FrontendSideProfile(
        architecture=Architecture.RVV,
        facade_path=_FACADE,
        intrinsic_specs=_frontend_specs(S8_VMAX_EXAMPLE_CATALOG.rvv_specs),
        function_name="test_rvv",
        target_triple="riscv64-none-elf",
        function_type=_FUNCTION_TYPE,
        parameters=_PARAMETERS,
        assertions=(
            FrontendAssertion("assert(batch!=0);", None),
            FrontendAssertion("assert(input!=NULL);", None),
            FrontendAssertion("assert(output!=NULL);", None),
        ),
    ),
)

S8_VMAX_EXAMPLE_MODEL = ModelProfile(
    case_id="s8-vmax-example",
    lean_namespace="SALT.Example.S8VMax",
    parameter_type="S8VMaxParams",
    parameter_fields=(ParameterField("threshold", 8),),
    rvv_scalar_types=(("threshold", "signed char"),),
    inputs=("input",),
    neon_block_lanes=16,
    neon_loop_condition="batch >= 16",
    neon_loop_update="batch -= 16",
)


def generated_module_path(repository_root: str | Path = _REPOSITORY_ROOT) -> Path:
    return (
        Path(repository_root).resolve()
        / "src/verification_bw/lean/SALT/Example/S8VMax/Models.lean"
    )


def emit_s8_vmax_example(
    *,
    repository_root: str | Path = _REPOSITORY_ROOT,
    neon_source: str | Path | None = None,
    rvv_source: str | Path | None = None,
    clang: str = "clang",
) -> CaseEmission:
    root = Path(repository_root).resolve()
    neon_path = (
        Path(neon_source)
        if neon_source is not None
        else root / "examples/s8-vmax-to-lean/neon.c"
    )
    rvv_path = (
        Path(rvv_source)
        if rvv_source is not None
        else root / "examples/s8-vmax-to-lean/rvv.c"
    )
    neon = parse_kernel(neon_path, clang=clang, profile=S8_VMAX_EXAMPLE_FRONTEND.neon)
    rvv = parse_kernel(rvv_path, clang=clang, profile=S8_VMAX_EXAMPLE_FRONTEND.rvv)
    digest = registry_content_digest(
        "s8-vmax-example-intrinsics", S8_VMAX_EXAMPLE_CATALOG.registry
    )
    return emit_case_pair(
        neon,
        rvv,
        profile=S8_VMAX_EXAMPLE_MODEL,
        neon_registry=S8_VMAX_EXAMPLE_CATALOG.registry,
        rvv_registry=S8_VMAX_EXAMPLE_CATALOG.registry,
        registry_sha256=digest,
    )


def generate_s8_vmax_example(
    *, repository_root: str | Path = _REPOSITORY_ROOT, clang: str = "clang"
) -> str:
    return emit_s8_vmax_example(
        repository_root=repository_root, clang=clang
    ).emitted.module_text


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=_REPOSITORY_ROOT)
    parser.add_argument("--clang", default="clang")
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the checked-in Lean model differs instead of writing it",
    )
    arguments = parser.parse_args(argv)
    module_text = generate_s8_vmax_example(
        repository_root=arguments.repository_root, clang=arguments.clang
    )
    output = generated_module_path(arguments.repository_root)
    if arguments.check:
        if not output.is_file() or output.read_text(encoding="ascii") != module_text:
            sys.stderr.write(f"stale generated module: {output}\n")
            return 1
        return 0
    _atomic_write_text(output, module_text, encoding="ascii")
    sys.stdout.write(f"generated {output}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
