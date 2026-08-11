from __future__ import annotations

from pathlib import Path

import pytest

from workflow.verification.lean_backend.emit_lean import (
    LeanEmissionError,
    emit_qs8_vadd_minmax_pair,
)
from workflow.verification.lean_backend.frontend import parse_kernel


ROOT = Path(__file__).resolve().parents[3]
NEON = ROOT / "kernels/source/qs8-vadd-minmax.c"
RVV = ROOT / "kernels/target/qs8-vadd-minmax.c"


def test_emits_independent_intrinsic_models() -> None:
    emitted = emit_qs8_vadd_minmax_pair(parse_kernel(NEON), parse_kernel(RVV))

    assert "def neonBlock16FromIntrinsics" in emitted.module_text
    assert "def rvvBlockFromIntrinsics" in emitted.module_text
    assert "SALT.Intrinsics.Neon.vmlaq_s32" in emitted.module_text
    assert "SALT.Intrinsics.RVV.vmacc_vx" in emitted.module_text
    assert "SALT.Intrinsics.Neon.vrshlq_s32" in emitted.module_text
    assert "SALT.Intrinsics.RVV.vssra_vx_rnu" in emitted.module_text
    assert "sorry" not in emitted.module_text
    assert "cvc5" not in emitted.module_text.lower()


def test_nonbroadcast_scalar_normalization_is_rejected() -> None:
    neon = parse_kernel(NEON)
    multiply = next(call for call in neon.calls if call.spelling == "vmulq_s32")
    multiply.arguments = (
        multiply.arguments[0],
        multiply.arguments[0],
    )

    with pytest.raises(LeanEmissionError, match="not derived from a reviewed broadcast"):
        emit_qs8_vadd_minmax_pair(neon, parse_kernel(RVV))


def test_wrong_active_vl_is_rejected() -> None:
    rvv = parse_kernel(RVV)
    load = next(call for call in rvv.calls if call.spelling == "__riscv_vle8_v_i8m2")
    load.arguments = (load.arguments[0], load.arguments[0])

    with pytest.raises(LeanEmissionError, match="does not use the active vl"):
        emit_qs8_vadd_minmax_pair(parse_kernel(NEON), rvv)


def test_wrong_neon_pointer_increment_is_rejected() -> None:
    neon = parse_kernel(NEON)
    update = next(
        definition
        for definition in neon.definitions
        if definition.value == "input_a@1"
    )
    object.__setattr__(update, "expression_text", "input_a += 7")

    with pytest.raises(LeanEmissionError, match="pointer/count updates"):
        emit_qs8_vadd_minmax_pair(neon, parse_kernel(RVV))


def test_redefined_rounding_macro_is_rejected(tmp_path: Path) -> None:
    facade_path = ROOT / "src/workflow/verification/lean_backend/facade/qs8_vadd_minmax.h"
    facade_text = facade_path.read_text(encoding="utf-8").replace(
        "#define __RISCV_VXRM_RNU 0",
        "#define __RISCV_VXRM_RNU 2",
        1,
    )
    facade = tmp_path / "wrong-rounding.h"
    facade.write_text(facade_text, encoding="utf-8")

    with pytest.raises(LeanEmissionError, match="pinned parse facade"):
        emit_qs8_vadd_minmax_pair(
            parse_kernel(NEON, facade=facade),
            parse_kernel(RVV, facade=facade),
        )


def test_changed_parameter_field_type_facade_is_rejected(tmp_path: Path) -> None:
    facade_path = ROOT / "src/workflow/verification/lean_backend/facade/qs8_vadd_minmax.h"
    facade_text = facade_path.read_text(encoding="utf-8").replace(
        "int16_t output_zero_point;", "int8_t output_zero_point;", 1
    )
    facade = tmp_path / "wrong-field-type.h"
    facade.write_text(facade_text, encoding="utf-8")

    with pytest.raises(LeanEmissionError, match="pinned parse facade"):
        emit_qs8_vadd_minmax_pair(
            parse_kernel(NEON, facade=facade),
            parse_kernel(RVV, facade=facade),
        )


def test_truncating_scalar_initializer_is_rejected(tmp_path: Path) -> None:
    mutated = RVV.read_text(encoding="utf-8").replace(
        "const int16_t output_zero_point = params->scalar.output_zero_point;",
        "const int16_t output_zero_point = (int8_t) params->scalar.output_zero_point;",
        1,
    )
    path = tmp_path / "truncated-output-zero-point.c"
    path.write_text(mutated, encoding="utf-8")

    with pytest.raises(LeanEmissionError, match="scalar initializers"):
        emit_qs8_vadd_minmax_pair(parse_kernel(NEON), parse_kernel(path, function_name="test_rvv"))


def test_parameter_pointer_update_is_rejected(tmp_path: Path) -> None:
    mutated = RVV.read_text(encoding="utf-8").replace(
        "  const int8_t a_zero_point",
        "  params += 1;\n  const int8_t a_zero_point",
        1,
    )
    path = tmp_path / "shifted-params.c"
    path.write_text(mutated, encoding="utf-8")

    with pytest.raises(LeanEmissionError, match="scalar initializers|scalar source"):
        emit_qs8_vadd_minmax_pair(parse_kernel(NEON), parse_kernel(path, function_name="test_rvv"))


def test_dead_definition_in_selected_block_is_rejected(tmp_path: Path) -> None:
    mutated = NEON.read_text(encoding="utf-8").replace(
        "  for (; batch >= 16 * sizeof(int8_t); batch -= 16 * sizeof(int8_t)) {",
        "  for (; batch >= 16 * sizeof(int8_t); batch -= 16 * sizeof(int8_t)) {\n"
        "    int8_t ignored_value = params->scalar.output_min;",
        1,
    )
    path = tmp_path / "dead-definition.c"
    path.write_text(mutated, encoding="utf-8")

    with pytest.raises(LeanEmissionError, match="untranslated Neon main-body"):
        emit_qs8_vadd_minmax_pair(
            parse_kernel(path, function_name="test_neon"), parse_kernel(RVV)
        )


def test_supported_semantic_mutation_changes_generated_neon_model(
    tmp_path: Path,
) -> None:
    original = emit_qs8_vadd_minmax_pair(parse_kernel(NEON), parse_kernel(RVV))
    mutated_source = NEON.read_text(encoding="utf-8").replace(
        "vmaxq_s8(vout0123456789ABCDEF, voutput_min)",
        "vminq_s8(vout0123456789ABCDEF, voutput_min)",
        1,
    )
    path = tmp_path / "semantic-mutation.c"
    path.write_text(mutated_source, encoding="utf-8")
    mutated = emit_qs8_vadd_minmax_pair(
        parse_kernel(path, function_name="test_neon"),
        parse_kernel(RVV),
    )

    assert mutated.module_text != original.module_text
    assert (
        "SALT.Intrinsics.Neon.vmin_s8 (vout0123456789ABCDEF_0) (p.output_min)"
        in mutated.module_text
    )
