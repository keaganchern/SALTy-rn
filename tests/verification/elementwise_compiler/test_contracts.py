from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.contracts import (
    ContractParseError,
    contract_type_from_c,
    parse_assertion,
    translate_assertions,
)
from workflow.verification.elementwise_compiler.schema import ContractOp, ContractTypeKind
from workflow.verification.lean_backend.frontend import parse_kernel_explicit
from workflow.verification.lean_backend.schema import Architecture


ROOT = Path(__file__).resolve().parents[3]
FACADE_ROOT = ROOT / "src/workflow/verification/lean_backend/facade"
pytestmark = pytest.mark.skipif(shutil.which("clang") is None, reason="system clang required")


def _extract(case: str, side: str):
    architecture = Architecture.NEON if side == "source" else Architecture.RVV
    function = "test_neon" if side == "source" else "test_rvv"
    triple = "aarch64-none-elf" if side == "source" else "riscv64-none-elf"
    return parse_kernel_explicit(
        ROOT / "kernels" / side / f"{case}.c",
        architecture=architecture,
        function_name=function,
        facade=FACADE_ROOT / f"{case.replace('-', '_')}.h",
        target_triple=triple,
    )


def test_reusable_frontend_translates_equal_entry_contract_and_local_tail_facts() -> None:
    neon = _extract("qs8-vcvt", "source")
    rvv = _extract("qs8-vcvt", "target")

    neon_entry, neon_local = translate_assertions(
        neon.assertions, parameters=neon.parameters
    )
    rvv_entry, rvv_local = translate_assertions(rvv.assertions, parameters=rvv.parameters)

    assert neon.schema_version == 3
    assert neon_entry == rvv_entry
    assert len(neon_entry.clauses) == 4
    assert len(neon_local) == 2
    assert not rvv_local
    assert all(item.parent_control == "control_0001" for item in neon_local)


@pytest.mark.parametrize(
    "case",
    (
        "qs8-vadd-minmax",
        "s8-vclamp",
        "qs8-vcvt",
        "qs8-vlrelu",
        "qu8-vadd-minmax",
    ),
)
def test_explicit_frontend_needs_no_program_profile_for_existing_integer_pairs(
    case: str,
) -> None:
    neon = _extract(case, "source")
    rvv = _extract(case, "target")
    neon_entry, _ = translate_assertions(neon.assertions, parameters=neon.parameters)
    rvv_entry, _ = translate_assertions(rvv.assertions, parameters=rvv.parameters)
    assert neon_entry == rvv_entry
    assert neon.function_name == "test_neon"
    assert rvv.function_name == "test_rvv"


def test_contract_parser_normalizes_commutative_conjunctions_and_pointer_null() -> None:
    variables = {
        "batch": contract_type_from_c("unsigned long"),
        "input": contract_type_from_c("const signed char *"),
    }
    first = parse_assertion(
        "assert(batch != 0 && input != NULL);",
        variable_types=variables,
        parent_control=None,
    )
    second = parse_assertion(
        "assert(input != NULL && batch != 0);",
        variable_types=variables,
        parent_control=None,
    )
    assert first.expression == second.expression
    pointer_comparison = next(
        item for item in first.expression.args if item.args[0].type.kind is ContractTypeKind.POINTER
    )
    assert pointer_comparison.op is ContractOp.NE


@pytest.mark.parametrize(
    "source",
    (
        "assert(++batch != 0);",
        "assert(helper(batch));",
        "assert(input[0] != 0);",
        "assert(batch = 1);",
    ),
)
def test_contract_parser_rejects_effectful_or_unsupported_expressions(source: str) -> None:
    variables = {
        "batch": contract_type_from_c("unsigned long"),
        "input": contract_type_from_c("const signed char *"),
    }
    with pytest.raises(ContractParseError):
        parse_assertion(source, variable_types=variables, parent_control=None)


def test_contract_parser_preserves_sizeof_divisibility_type() -> None:
    parsed = parse_assertion(
        "assert(batch % sizeof(float) == 0);",
        variable_types={"batch": contract_type_from_c("size_t")},
        parent_control=None,
    )
    comparison = parsed.expression
    modulo = next(argument for argument in comparison.args if argument.op is ContractOp.MOD)
    assert modulo.type.c_spelling == "size_t"
    assert any(argument.op is ContractOp.SIZEOF for argument in modulo.args)

