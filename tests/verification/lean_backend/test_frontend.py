from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from workflow.verification.lean_backend.frontend import (
    UnsupportedConstructError,
    parse_kernel,
)


pytestmark = pytest.mark.skipif(shutil.which("clang") is None, reason="system clang required")

ROOT = Path(__file__).resolve().parents[3]
NEON = ROOT / "kernels/source/qs8-vadd-minmax.c"
RVV = ROOT / "kernels/target/qs8-vadd-minmax.c"
FACADE = (
    ROOT
    / "src/workflow/verification/lean_backend/facade/qs8_vadd_minmax.h"
)


def test_extracts_typed_neon_calls_dataflow_and_control() -> None:
    result = parse_kernel(NEON)

    assert result.function_name == "test_neon"
    assert result.dialect == "neon"
    assert result.target_triple == "aarch64-none-elf"
    assert len(result.preprocessed_sha256) == 64
    assert [parameter.name for parameter in result.parameters] == [
        "batch",
        "input_a",
        "input_b",
        "output",
        "params",
    ]
    assert len(result.calls) == 93
    assert {call.spelling for call in result.calls} == {
        "vcombine_s16",
        "vcombine_s8",
        "vdup_n_s8",
        "vdupq_n_s16",
        "vdupq_n_s32",
        "vdupq_n_s8",
        "vext_s8",
        "vget_high_s16",
        "vget_low_s16",
        "vget_low_s8",
        "vld1_s8",
        "vmax_s8",
        "vmaxq_s8",
        "vmin_s8",
        "vminq_s8",
        "vmlaq_s32",
        "vmovl_s16",
        "vmulq_s32",
        "vqaddq_s16",
        "vqmovn_s16",
        "vqmovn_s32",
        "vreinterpret_u16_s8",
        "vreinterpret_u32_s8",
        "vrshlq_s32",
        "vst1_lane_s8",
        "vst1_lane_u16",
        "vst1_lane_u32",
        "vst1_s8",
        "vst1q_s8",
        "vsubl_s8",
    }

    multiply = next(
        call
        for call in result.calls
        if call.spelling == "vmulq_s32" and call.assigned_to == "vacc0123@0"
    )
    assert multiply.result_type == "int32x4_t"
    assert multiply.callee_type == "int32x4_t (int32x4_t, int32x4_t)"
    assert multiply.arguments[0].source_text == "vmovl_s16(vget_low_s16(vxa01234567))"
    assert multiply.arguments[0].dependencies == ("call:call_0017",)
    assert multiply.arguments[1].dependencies == ("va_multiplier@0",)
    assert multiply.source.begin_line == 50
    assert multiply.source.end_offset > multiply.source.begin_offset

    accumulate = next(
        call
        for call in result.calls
        if call.spelling == "vmlaq_s32" and call.assigned_to == "vacc0123@1"
    )
    assert accumulate.dependencies == (
        "vacc0123@0",
        "call:call_0029",
        "vb_multiplier@0",
    )

    assert [(control.kind, control.parent_control) for control in result.controls] == [
        ("ForStmt", None),
        ("IfStmt", None),
        ("DoStmt", "control_0001"),
        ("IfStmt", "control_0002"),
        ("IfStmt", "control_0003"),
        ("IfStmt", "control_0003"),
        ("IfStmt", "control_0003"),
    ]
    assert result.controls[0].condition_text == "batch >= 16 * sizeof(int8_t)"
    assert result.controls[0].update_text == "batch -= 16 * sizeof(int8_t)"
    assert result.controls[-1].condition_text == "batch & (1 * sizeof(int8_t))"


def test_extracts_rvv_active_length_dataflow() -> None:
    result = parse_kernel(RVV)

    assert result.function_name == "test_rvv"
    assert result.dialect == "rvv"
    assert result.target_triple == "riscv64-none-elf"
    assert len(result.preprocessed_sha256) == 64
    assert [call.spelling for call in result.calls] == [
        "__riscv_vsetvl_e8m2",
        "__riscv_vle8_v_i8m2",
        "__riscv_vle8_v_i8m2",
        "__riscv_vwsub_vx_i16m4",
        "__riscv_vwsub_vx_i16m4",
        "__riscv_vsext_vf2_i32m8",
        "__riscv_vsext_vf2_i32m8",
        "__riscv_vmul_vx_i32m8",
        "__riscv_vmacc_vx_i32m8",
        "__riscv_vssra_vx_i32m8",
        "__riscv_vnclip_wx_i16m4",
        "__riscv_vsadd_vx_i16m4",
        "__riscv_vnclip_wx_i8m2",
        "__riscv_vmax_vx_i8m2",
        "__riscv_vmin_vx_i8m2",
        "__riscv_vse8_v_i8m2",
    ]
    assert result.calls[0].assigned_to == "vl@0"
    assert result.calls[0].dependencies == ("batch@0",)

    rounding_calls = [
        call
        for call in result.calls
        if call.spelling
        in {
            "__riscv_vssra_vx_i32m8",
            "__riscv_vnclip_wx_i16m4",
            "__riscv_vnclip_wx_i8m2",
        }
    ]
    assert len(rounding_calls) == 3
    for call in rounding_calls:
        assert call.arguments[2].type_spelling == "unsigned int"
        assert "unsigned int" in call.callee_type
    assert rounding_calls[0].arguments[2].source_text == "__RISCV_VXRM_RNU"
    assert rounding_calls[0].arguments[2].constant_value == 0
    assert rounding_calls[1].arguments[1].constant_value == 0
    assert rounding_calls[1].arguments[2].source_text == "__RISCV_VXRM_RDN"
    assert rounding_calls[1].arguments[2].constant_value == 2

    for call in result.calls[1:]:
        assert any(
            "vl@0" in argument.dependencies for argument in call.arguments
        ), call.spelling

    store = result.calls[-1]
    assert store.result_type == "void"
    assert store.dependencies == ("output@0", "vout@2", "vl@0")
    assert store.source.begin_line == 48
    assert [(control.kind, control.condition_text) for control in result.controls] == [
        ("WhileStmt", "batch > 0")
    ]

    updates = {
        definition.variable: definition.dependencies
        for definition in result.definitions
        if definition.definition_kind.startswith("compound")
    }
    assert updates["input_a"] == ("input_a@0", "vl@0")
    assert updates["input_b"] == ("input_b@0", "vl@0")
    assert updates["output"] == ("output@0", "vl@0")
    assert updates["batch"] == ("batch@0", "vl@0")


def test_unknown_declared_call_fails_closed(tmp_path: Path) -> None:
    mutated = NEON.read_text(encoding="utf-8")
    mutated = mutated.replace(
        "void test_neon(", "void unsupported_helper(void);\n\nvoid test_neon(", 1
    )
    mutated = mutated.replace(
        "    vst1q_s8(output, vout0123456789ABCDEF); output += 16;",
        "    unsupported_helper();\n"
        "    vst1q_s8(output, vout0123456789ABCDEF); output += 16;",
        1,
    )
    path = tmp_path / "mutated.c"
    path.write_text(mutated, encoding="utf-8")

    with pytest.raises(UnsupportedConstructError, match="unknown call spelling"):
        parse_kernel(path, function_name="test_neon")


def test_changed_intrinsic_signature_fails_closed(tmp_path: Path) -> None:
    facade_text = FACADE.read_text(encoding="utf-8").replace(
        "vint32m8_t __riscv_vssra_vx_i32m8("
        "vint32m8_t, size_t, unsigned int, size_t);",
        "vint32m8_t __riscv_vssra_vx_i32m8("
        "vint32m8_t, size_t, int, size_t);",
        1,
    )
    facade = tmp_path / "changed_facade.h"
    facade.write_text(facade_text, encoding="utf-8")

    with pytest.raises(UnsupportedConstructError, match="facade type changed"):
        parse_kernel(RVV, facade=facade)


def test_source_definition_cannot_replace_intrinsic_semantics(tmp_path: Path) -> None:
    mutated = NEON.read_text(encoding="utf-8").replace(
        "void test_neon(",
        "int8x8_t vmax_s8(int8x8_t left, int8x8_t right) { return left; }\n\n"
        "void test_neon(",
        1,
    )
    path = tmp_path / "shadowed-intrinsic.c"
    path.write_text(mutated, encoding="utf-8")

    with pytest.raises(UnsupportedConstructError, match="parse-facade declaration"):
        parse_kernel(path, function_name="test_neon")


def test_changed_kernel_signature_fails_closed(tmp_path: Path) -> None:
    mutated = RVV.read_text(encoding="utf-8").replace(
        "    size_t batch,", "    uint32_t batch,", 1
    )
    path = tmp_path / "changed-signature.c"
    path.write_text(mutated, encoding="utf-8")

    with pytest.raises(UnsupportedConstructError, match="kernel signature changed"):
        parse_kernel(path, function_name="test_rvv")


def test_kernel_linkage_redeclaration_fails_closed(tmp_path: Path) -> None:
    prototype = (
        "void test_rvv(size_t, const int8_t*, const int8_t*, int8_t*, "
        "const struct xnn_qs8_add_minmax_params* restrict) "
        '__asm__("evil_test_rvv");\n\n'
    )
    path = tmp_path / "changed-linkage.c"
    path.write_text(prototype + RVV.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(UnsupportedConstructError, match="linkage name|redeclarations"):
        parse_kernel(path, function_name="test_rvv")


def test_assert_argument_side_effect_fails_closed(tmp_path: Path) -> None:
    mutated = RVV.read_text(encoding="utf-8").replace(
        "assert(batch != 0);",
        "assert((output[0] = 42, batch != 0));",
        1,
    )
    path = tmp_path / "side-effecting-assert.c"
    path.write_text(mutated, encoding="utf-8")

    with pytest.raises(UnsupportedConstructError, match="kernel assertions changed"):
        parse_kernel(path, function_name="test_rvv")


def test_non_ascii_source_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "non-ascii.c"
    path.write_text("/* \N{SNOWMAN} */\n" + RVV.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(UnsupportedConstructError, match="non-ASCII source"):
        parse_kernel(path, function_name="test_rvv")


def test_source_pragma_cannot_redirect_intrinsic_linkage(tmp_path: Path) -> None:
    mutated = NEON.read_text(encoding="utf-8").replace(
        "void test_neon(",
        "#pragma redefine_extname vmax_s8 evil_vmax\n\nvoid test_neon(",
        1,
    )
    path = tmp_path / "redirected-intrinsic.c"
    path.write_text(mutated, encoding="utf-8")

    with pytest.raises(UnsupportedConstructError, match="preprocessor directive"):
        parse_kernel(path, function_name="test_neon")


def test_comment_prefixed_source_directive_fails_closed(tmp_path: Path) -> None:
    macro = (
        "/**/#define __riscv_vmul_vx_i32m8(a,b,vl) "
        "__riscv_vmul_vx_i32m8((a), -(b), (vl))\n"
    )
    path = tmp_path / "comment-prefixed-directive.c"
    path.write_text(macro + RVV.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(UnsupportedConstructError, match="preprocessor directive"):
        parse_kernel(path, function_name="test_rvv")


def test_trigraph_source_directive_fails_closed(tmp_path: Path) -> None:
    directives = "??=undef assert\n??=define assert(condition) (batch = 0)\n"
    path = tmp_path / "trigraph-directive.c"
    path.write_text(directives + RVV.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(UnsupportedConstructError, match="preprocessor directive"):
        parse_kernel(path, function_name="test_rvv")


def test_line_spliced_digraph_directive_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "line-spliced-directive.c"
    path.write_text(
        "%\\\n:define UNUSED_AUDIT 1\n" + RVV.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    with pytest.raises(UnsupportedConstructError, match="preprocessor directive"):
        parse_kernel(path, function_name="test_rvv")


def test_extension_line_spliced_digraph_directive_fails_closed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "extension-line-spliced-directive.c"
    path.write_text(
        "%\\   \n:define UNUSED_AUDIT 1\n" + RVV.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    with pytest.raises(UnsupportedConstructError, match="preprocessor directive"):
        parse_kernel(path, function_name="test_rvv")


def test_volatile_local_effect_fails_closed(tmp_path: Path) -> None:
    mutated = NEON.read_text(encoding="utf-8").replace(
        "  for (; batch >= 16 * sizeof(int8_t);",
        "  volatile int8_t audit_effect = params->scalar.output_min;\n\n"
        "  for (; batch >= 16 * sizeof(int8_t);",
        1,
    )
    path = tmp_path / "volatile-effect.c"
    path.write_text(mutated, encoding="utf-8")

    with pytest.raises(UnsupportedConstructError, match="volatile/atomic"):
        parse_kernel(path, function_name="test_neon")


def test_untracked_expression_statement_fails_closed(tmp_path: Path) -> None:
    mutated = RVV.read_text(encoding="utf-8").replace(
        "  while (batch > 0)", "  batch;\n  while (batch > 0)", 1
    )
    path = tmp_path / "untracked-expression.c"
    path.write_text(mutated, encoding="utf-8")

    with pytest.raises(UnsupportedConstructError, match="standalone expression"):
        parse_kernel(path, function_name="test_rvv")


def test_cast_function_callee_fails_closed(tmp_path: Path) -> None:
    mutated = NEON.read_text(encoding="utf-8").replace(
        "void test_neon(",
        "typedef int8x16_t (*weirdq_fn)(int8x16_t, int8x16_t) "
        "__attribute__((preserve_most));\n\nvoid test_neon(",
        1,
    ).replace(
        "vmaxq_s8(vout0123456789ABCDEF, voutput_min)",
        "((weirdq_fn) vmaxq_s8)(vout0123456789ABCDEF, voutput_min)",
        1,
    )
    path = tmp_path / "cast-callee.c"
    path.write_text(mutated, encoding="utf-8")

    with pytest.raises(UnsupportedConstructError, match="unknown call spelling"):
        parse_kernel(path, function_name="test_neon")


def test_extraction_is_deterministic() -> None:
    first = parse_kernel(RVV).to_dict()
    second = parse_kernel(RVV).to_dict()
    assert first == second
