from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from workflow.verification.lean_backend.case_emit import (
    CaseEmissionError,
    emit_case_pair,
)
from workflow.verification.lean_backend.emit_lean import (
    LeanEmissionError,
    _BlockEmitter,
)
from workflow.verification.lean_backend.frontend import parse_kernel
from workflow.verification.lean_backend.model_profiles import SCALE_UP_MODELS
from workflow.verification.lean_backend.profiles import FRONTEND_PROFILES
from workflow.verification.lean_backend.scaleup_catalog import SCALEUP_CATALOGS
from workflow.verification.lean_backend.schema import Architecture


ROOT = Path(__file__).resolve().parents[3]
CASES = tuple(SCALE_UP_MODELS)
pytestmark = pytest.mark.skipif(
    shutil.which("clang") is None, reason="system clang required"
)


def extract(case_id: str, side: str, source: Path | None = None):
    profile = FRONTEND_PROFILES[case_id]
    selected = profile.neon if side == "neon" else profile.rvv
    path = (
        source
        or ROOT
        / "kernels"
        / ("source" if side == "neon" else "target")
        / f"{case_id}.c"
    )
    return parse_kernel(path, profile=selected)


def emit(case_id: str, neon_source: Path | None = None, rvv_source: Path | None = None):
    catalog = SCALEUP_CATALOGS[case_id]
    return emit_case_pair(
        extract(case_id, "neon", neon_source),
        extract(case_id, "rvv", rvv_source),
        profile=SCALE_UP_MODELS[case_id],
        neon_registry=catalog.registry,
        rvv_registry=catalog.registry,
        registry_sha256="0" * 64,
    )


@pytest.mark.parametrize("case_id", CASES)
def test_four_scaleup_cases_emit_independent_neon_and_rvv_models(case_id: str):
    result = emit(case_id)
    module = result.emitted.module_text

    assert f"namespace {SCALE_UP_MODELS[case_id].lean_namespace}" in module
    assert "def neonSourceSha256" in module
    assert "def rvvSourceSha256" in module
    assert f"def {result.emitted.neon_function}" in module
    assert f"def {result.emitted.rvv_function}" in module
    assert "SALT.Intrinsics.Neon." in module
    assert "SALT.Intrinsics.RVV." in module
    assert result.neon_consumed_calls
    assert result.rvv_consumed_calls


def test_s8_emission_consumes_every_neon_and_rvv_call():
    neon = extract("s8-vclamp", "neon")
    rvv = extract("s8-vclamp", "rvv")
    result = emit("s8-vclamp")

    assert len(neon.calls) == 36
    assert len(rvv.calls) == 5
    assert set(result.neon_consumed_calls) == {call.node_id for call in neon.calls}
    assert set(result.rvv_consumed_calls) == {call.node_id for call in rvv.calls}
    assert "def neonBlock8FromIntrinsics" in result.emitted.module_text
    assert "def neonPartialTailLivePrefixFromIntrinsics" in result.emitted.module_text
    assert "def neonValueLoopWithOverreadFromIntrinsics" in result.emitted.module_text
    assert "def neonValueLoopFromIntrinsics" in result.emitted.module_text
    assert "let loaded := (tail ++ overread).take 8" in result.emitted.module_text
    assert "List.replicate 7 (0 : BitVec 8)" in result.emitted.module_text
    overread_model = result.emitted.module_text.split(
        "def neonValueLoopWithOverreadFromIntrinsics", 1
    )[1].split("Zero-filled compatibility specialization", 1)[0]
    assert "List.replicate" not in overread_model


def test_qs8_vcvt_emission_consumes_complete_unbounded_schedule():
    neon = extract("qs8-vcvt", "neon")
    rvv = extract("qs8-vcvt", "rvv")
    result = emit("qs8-vcvt")
    module = result.emitted.module_text

    assert len(neon.calls) == 23
    assert len(rvv.calls) == 11
    assert set(result.neon_consumed_calls) == {call.node_id for call in neon.calls}
    assert set(result.rvv_consumed_calls) == {call.node_id for call in rvv.calls}
    assert "def neonPartialTailLivePrefixFromIntrinsics" in module
    assert "def neonValueLoopWithOverreadFromIntrinsics" in module
    assert "def rvvValueLoopFromIntrinsics" in module
    assert "runFixedChunkTail 8" in module
    assert "PositivePartition input.length" in module
    assert "let loaded := (tail ++ overread).take 8" in module


def test_qs8_vlrelu_emission_consumes_complete_unbounded_schedule():
    neon = extract("qs8-vlrelu", "neon")
    rvv = extract("qs8-vlrelu", "rvv")
    result = emit("qs8-vlrelu")
    module = result.emitted.module_text

    assert len(neon.calls) == 30
    assert len(rvv.calls) == 13
    assert set(result.neon_consumed_calls) == {call.node_id for call in neon.calls}
    assert set(result.rvv_consumed_calls) == {call.node_id for call in rvv.calls}
    assert "def neonPartialTailLivePrefixFromIntrinsics" in module
    assert "def neonValueLoopWithOverreadFromIntrinsics" in module
    assert "def rvvValueLoopFromIntrinsics" in module
    assert "runFixedChunkTail 8" in module
    assert "PositivePartition input.length" in module
    assert "let call_0016 := List.replicate 8 (0)" in module
    assert "vcltq_s16 (vacc_4) (call_0016)" in module


def test_qu8_emission_consumes_every_call_and_emits_binary_value_runners():
    neon = extract("qu8-vadd-minmax", "neon")
    rvv = extract("qu8-vadd-minmax", "rvv")
    result = emit("qu8-vadd-minmax")
    module = result.emitted.module_text

    assert len(neon.calls) == 70
    assert len(rvv.calls) == 21
    assert set(result.neon_consumed_calls) == {call.node_id for call in neon.calls}
    assert set(result.rvv_consumed_calls) == {call.node_id for call in rvv.calls}
    assert "(loadedA loadedB : List (BitVec 8))" in module
    assert "let loadedA := (tailA ++ overreadA).take 8" in module
    assert "let loadedB := (tailB ++ overreadB).take 8" in module
    assert "runFixedChunkTail2 8" in module
    assert "sameLength : input_a.length = input_b.length" in module
    assert "SALT.Kernel.Schedule.processBlocks2" in module


def test_qu8_tail_second_load_cannot_alias_first_input(tmp_path: Path):
    source = (ROOT / "kernels/source/qu8-vadd-minmax.c").read_text(encoding="utf-8")
    old = "const uint8x8_t vb01234567 = vld1_u8(input_b);"
    offset = source.rfind(old)
    assert offset >= 0
    mutated = tmp_path / "qu8-vadd-minmax.c"
    mutated.write_text(
        source[:offset]
        + old.replace("input_b", "input_a")
        + source[offset + len(old) :],
        encoding="utf-8",
    )

    with pytest.raises(CaseEmissionError, match="load base changed for input_b"):
        emit("qu8-vadd-minmax", neon_source=mutated)


def test_supported_qu8_tail_operator_mutation_changes_only_tail_model(tmp_path: Path):
    original = emit("qu8-vadd-minmax").emitted.module_text
    source = (ROOT / "kernels/source/qu8-vadd-minmax.c").read_text(encoding="utf-8")
    old = "vout01234567 = vmin_u8(vout01234567, voutput_max);"
    offset = source.rfind(old)
    assert offset >= 0
    mutated = tmp_path / "qu8-vadd-minmax.c"
    mutated.write_text(
        source[:offset]
        + "vout01234567 = vmax_u8(vout01234567, voutput_max);"
        + source[offset + len(old) :],
        encoding="utf-8",
    )

    changed = emit("qu8-vadd-minmax", neon_source=mutated).emitted.module_text
    assert changed != original
    main, tail = changed.split("def neonPartialTailLivePrefixFromIntrinsics", 1)
    assert main.count("SALT.Intrinsics.Neon.vmin_u8") == 1
    assert tail.count("SALT.Intrinsics.Neon.vmin_u8") == 0
    assert tail.count("SALT.Intrinsics.Neon.vmax_u8") == 2


@pytest.mark.parametrize(
    ("old", "new", "message"),
    (
        (
            "if (batch & (4 * sizeof(uint8_t)))",
            "if (batch & (3 * sizeof(uint8_t)))",
            "Neon control shape changed",
        ),
        (
            "vst1_lane_u16((void*) output",
            "vst1_lane_u16((uint16_t*) output",
            "width-2 lane-store shape changed",
        ),
    ),
)
def test_qu8_tail_control_and_store_mutations_fail_closed(
    tmp_path: Path, old: str, new: str, message: str
):
    source = (ROOT / "kernels/source/qu8-vadd-minmax.c").read_text(encoding="utf-8")
    assert source.count(old) == 1
    mutated = tmp_path / "qu8-vadd-minmax.c"
    mutated.write_text(source.replace(old, new, 1), encoding="utf-8")

    with pytest.raises((CaseEmissionError, LeanEmissionError), match=message):
        emit("qu8-vadd-minmax", neon_source=mutated)


def test_qu8_tail_slide_shadow_declaration_is_rejected(tmp_path: Path):
    source = (ROOT / "kernels/source/qu8-vadd-minmax.c").read_text(encoding="utf-8")
    old = "vout01234567 = vext_u8(vout01234567, vout01234567, 4);"
    assert source.count(old) == 1
    mutated = tmp_path / "qu8-vadd-minmax.c"
    mutated.write_text(
        source.replace(old, f"uint8x8_t {old}", 1),
        encoding="utf-8",
    )

    with pytest.raises(CaseEmissionError, match="width-4 conditional slide changed"):
        emit("qu8-vadd-minmax", neon_source=mutated)


def test_qu8_second_neon_input_update_is_validated(tmp_path: Path):
    source = (ROOT / "kernels/source/qu8-vadd-minmax.c").read_text(encoding="utf-8")
    old = "input_b += 8;"
    assert source.count(old) == 1
    mutated = tmp_path / "qu8-vadd-minmax.c"
    mutated.write_text(source.replace(old, "input_b += 4;", 1), encoding="utf-8")

    with pytest.raises(CaseEmissionError, match="Neon pointer/count updates changed"):
        emit("qu8-vadd-minmax", neon_source=mutated)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    (
        (
            "__riscv_vle8_v_u8m2(input_b, vl)",
            "__riscv_vle8_v_u8m2(input_a, vl)",
            "RVV load footprint/order changed",
        ),
        (
            "__riscv_vle8_v_u8m2(input_b, vl)",
            "__riscv_vle8_v_u8m2(input_b, -vl)",
            "does not consume active vl",
        ),
        ("input_b += vl;", "input_b += 1;", "RVV pointer/count updates changed"),
    ),
)
def test_qu8_second_rvv_input_schedule_mutations_fail_closed(
    tmp_path: Path, old: str, new: str, message: str
):
    source = (ROOT / "kernels/target/qu8-vadd-minmax.c").read_text(encoding="utf-8")
    assert source.count(old) == 1
    mutated = tmp_path / "qu8-vadd-minmax.c"
    mutated.write_text(source.replace(old, new, 1), encoding="utf-8")

    with pytest.raises((CaseEmissionError, LeanEmissionError), match=message):
        emit("qu8-vadd-minmax", rvv_source=mutated)


@pytest.mark.parametrize("declaration", ("vint32m8_t vacc", "vint32m8_t foo"))
def test_qu8_rvv_else_result_must_assign_the_outer_accumulator(
    tmp_path: Path, declaration: str
):
    source = (ROOT / "kernels/target/qu8-vadd-minmax.c").read_text(encoding="utf-8")
    old = "vacc = __riscv_vsll_vx_i32m8(vacc, (size_t)(-shift), vl);"
    assert source.count(old) == 1
    mutated = tmp_path / "qu8-vadd-minmax.c"
    mutated.write_text(
        source.replace(old, f"{declaration} = {old.split(' = ', 1)[1]}", 1),
        encoding="utf-8",
    )

    with pytest.raises(CaseEmissionError, match="signed-shift branch dataflow changed"):
        emit("qu8-vadd-minmax", rvv_source=mutated)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    (
        (
            "if (batch & (4 * sizeof(int8_t)))",
            "if (batch & (3 * sizeof(int8_t)))",
            "Neon control shape changed",
        ),
        (
            "vext_s8(vy, vy, 4)",
            "vext_s8(vy, vy, 2)",
            "conditional slide changed",
        ),
        (
            "output += 4;",
            "output += 3;",
            "prefix-tail pointer updates changed",
        ),
    ),
)
def test_qs8_vlrelu_tail_shape_mutations_fail_closed(
    tmp_path: Path, old: str, new: str, message: str
):
    source = (ROOT / "kernels/source/qs8-vlrelu.c").read_text(encoding="utf-8")
    assert source.count(old) == 1
    mutated = tmp_path / "qs8-vlrelu.c"
    mutated.write_text(source.replace(old, new, 1), encoding="utf-8")

    with pytest.raises((CaseEmissionError, LeanEmissionError), match=message):
        emit("qs8-vlrelu", neon_source=mutated)


def test_supported_qs8_vlrelu_tail_semantic_mutation_changes_model(tmp_path: Path):
    original = emit("qs8-vlrelu").emitted.module_text
    source = (ROOT / "kernels/source/qs8-vlrelu.c").read_text(encoding="utf-8")
    old = "vcltq_s16(vacc, vmovq_n_s16(0))"
    offset = source.rfind(old)
    assert offset >= 0
    new = "vcltq_s16(vacc, vmovq_n_s16(2))"
    mutated = tmp_path / "qs8-vlrelu.c"
    mutated.write_text(
        source[:offset] + new + source[offset + len(old) :], encoding="utf-8"
    )

    changed = emit("qs8-vlrelu", neon_source=mutated).emitted.module_text
    assert changed != original
    main, tail = changed.split("def neonPartialTailLivePrefixFromIntrinsics", 1)
    assert "let call_0006 := List.replicate 8 (0)" in main
    assert "let call_0016 := List.replicate 8 (2)" in tail
    assert "vcltq_s16 (vacc_4) (call_0016)" in tail


def test_qs8_vlrelu_rejects_unused_expression_only_tail_call(tmp_path: Path):
    source = (ROOT / "kernels/source/qs8-vlrelu.c").read_text(encoding="utf-8")
    marker = "    int16x8_t vacc = vsubw_s8(vinput_zero_point, vx);\n"
    offset = source.rfind(marker)
    assert offset >= 0
    mutated = tmp_path / "qs8-vlrelu.c"
    mutated.write_text(
        source[: offset + len(marker)]
        + "    vmovq_n_s16(0);\n"
        + source[offset + len(marker) :],
        encoding="utf-8",
    )

    with pytest.raises(
        CaseEmissionError, match="expression-only tail call vmovq_n_s16 is not consumed"
    ):
        emit("qs8-vlrelu", neon_source=mutated)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    (
        (
            "if (batch & (4 * sizeof(int8_t)))",
            "if (batch & (3 * sizeof(int8_t)))",
            "Neon control shape changed",
        ),
        (
            "vext_s8(vy, vy, 4)",
            "vext_s8(vy, vy, 2)",
            "conditional slide changed",
        ),
        (
            "output += 4;",
            "output += 3;",
            "prefix-tail pointer updates changed",
        ),
        (
            "vst1_lane_u32((void*) output",
            "vst1_lane_u32((uint32_t*) output",
            "width-4 lane-store shape changed",
        ),
    ),
)
def test_qs8_vcvt_tail_shape_mutations_fail_closed(
    tmp_path: Path, old: str, new: str, message: str
):
    source = (ROOT / "kernels/source/qs8-vcvt.c").read_text(encoding="utf-8")
    assert source.count(old) == 1
    mutated = tmp_path / "qs8-vcvt.c"
    mutated.write_text(source.replace(old, new, 1), encoding="utf-8")

    with pytest.raises((CaseEmissionError, LeanEmissionError), match=message):
        emit("qs8-vcvt", neon_source=mutated)


def test_supported_qs8_vcvt_tail_semantic_mutation_changes_model(tmp_path: Path):
    original = emit("qs8-vcvt").emitted.module_text
    source = (ROOT / "kernels/source/qs8-vcvt.c").read_text(encoding="utf-8")
    old = "vacc = vqaddq_s16(vacc, voutput_zero_point);"
    offset = source.rfind(old)
    assert offset >= 0
    new = "vacc = vqrdmulhq_s16(vacc, voutput_zero_point);"
    mutated = tmp_path / "qs8-vcvt.c"
    mutated.write_text(
        source[:offset] + new + source[offset + len(old) :], encoding="utf-8"
    )

    changed = emit("qs8-vcvt", neon_source=mutated).emitted.module_text
    assert changed != original
    tail = changed.split("def neonPartialTailLivePrefixFromIntrinsics", 1)[1]
    assert "SALT.Intrinsics.Neon.vqrdmulhq_s16 (vacc_6) (voutput_zero_point_0)" in tail


def test_generic_lane_store_still_requires_an_endian_contract():
    extraction = extract("s8-vclamp", "neon")
    emitter = _BlockEmitter(
        extraction,
        Architecture.NEON,
        registry=SCALEUP_CATALOGS["s8-vclamp"].registry,
    )
    lane_store = next(
        call for call in extraction.calls if call.spelling == "vst1_lane_u32"
    )

    with pytest.raises(LeanEmissionError, match="requires an endian contract"):
        emitter.emit_registered_call(lane_store)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    (
        ("if (batch & 4)", "if (batch & 3)", "Neon control shape changed"),
        ("if (batch & 2)", "if (batch & 3)", "Neon control shape changed"),
        ("if (batch & 1)", "if (batch & 3)", "Neon control shape changed"),
        (
            "vext_s8(vacc, vacc, 4)",
            "vext_s8(vacc, vacc, 2)",
            "Neon 8-lane/tail call or operand shape changed",
        ),
        (
            "vext_s8(vacc, vacc, 2)",
            "vext_s8(vacc, vacc, 1)",
            "Neon 8-lane/tail call or operand shape changed",
        ),
        ("output += 4;", "output += 3;", "pointer or count updates changed"),
        (
            "vst1_lane_s8(output, vacc, 0)",
            "vst1_lane_s8(output, vacc, 1)",
            "Neon 8-lane/tail call or operand shape changed",
        ),
    ),
)
def test_s8_tail_shape_mutations_fail_closed(
    tmp_path: Path, old: str, new: str, message: str
):
    source = (ROOT / "kernels/source/s8-vclamp.c").read_text(encoding="utf-8")
    assert source.count(old) == 1
    mutated = tmp_path / "s8-vclamp.c"
    mutated.write_text(source.replace(old, new, 1), encoding="utf-8")

    with pytest.raises(CaseEmissionError, match=message):
        emit("s8-vclamp", neon_source=mutated)


@pytest.mark.parametrize(
    ("old", "new"),
    (
        (
            "vacc = vmin_s8(vacc, vget_low_s8(voutput_max));",
            "vacc = vmax_s8(vacc, vget_low_s8(voutput_max));",
        ),
        (
            "vacc = vmax_s8(vacc, vget_low_s8(voutput_min));",
            "vacc = vmin_s8(vacc, vget_low_s8(voutput_min));",
        ),
    ),
)
def test_s8_tail_semantic_operation_mutations_fail_closed(
    tmp_path: Path, old: str, new: str
):
    source = (ROOT / "kernels/source/s8-vclamp.c").read_text(encoding="utf-8")
    offset = source.rfind(old)
    assert offset >= 0
    mutated = tmp_path / "s8-vclamp.c"
    mutated.write_text(
        source[:offset] + new + source[offset + len(old) :],
        encoding="utf-8",
    )

    with pytest.raises(
        CaseEmissionError,
        match="Neon 8-lane/tail call or operand shape changed",
    ):
        emit("s8-vclamp", neon_source=mutated)


def test_supported_neon_semantic_mutation_changes_the_s8_model(tmp_path: Path):
    original = emit("s8-vclamp").emitted.module_text
    source = (ROOT / "kernels/source/s8-vclamp.c").read_text(encoding="utf-8")
    source = source.replace(
        "vacc0 = vmaxq_s8(vacc0, voutput_min);",
        "vacc0 = vminq_s8(vacc0, voutput_min);",
        1,
    )
    mutated = tmp_path / "s8-vclamp.c"
    mutated.write_text(source, encoding="utf-8")

    changed = emit("s8-vclamp", neon_source=mutated).emitted.module_text
    assert changed != original
    assert changed.count("SALT.Intrinsics.Neon.vminq_s8") == 5
    assert changed.count("SALT.Intrinsics.Neon.vmaxq_s8") == 3


def test_changed_neon_pointer_stride_is_rejected(tmp_path: Path):
    source = (ROOT / "kernels/source/s8-vclamp.c").read_text(encoding="utf-8")
    source = source.replace("input += 16;", "input += 8;", 1)
    mutated = tmp_path / "s8-vclamp.c"
    mutated.write_text(source, encoding="utf-8")

    with pytest.raises(CaseEmissionError, match="pointer/count updates changed"):
        emit("s8-vclamp", neon_source=mutated)


def test_nested_neon_block_control_is_rejected(tmp_path: Path):
    source = (ROOT / "kernels/source/s8-vclamp.c").read_text(encoding="utf-8")
    marker = "    int8x16_t vacc3 = vld1q_s8(input); input += 16;\n"
    inserted = marker + "    if (batch > 64) { vst1q_s8(output, vacc3); }\n"
    assert marker in source
    mutated = tmp_path / "s8-vclamp.c"
    mutated.write_text(source.replace(marker, inserted, 1), encoding="utf-8")

    with pytest.raises(CaseEmissionError, match="nested Neon block control"):
        emit("s8-vclamp", neon_source=mutated)


def test_intermediate_narrowing_cast_in_scalar_local_is_rejected(tmp_path: Path):
    source = (ROOT / "kernels/target/qu8-vadd-minmax.c").read_text(encoding="utf-8")
    source = source.replace(
        "const int32_t a_multiplier = params->scalar.a_multiplier;",
        "const int32_t a_multiplier = (int8_t) params->scalar.a_multiplier;",
        1,
    )
    mutated = tmp_path / "qu8-vadd-minmax.c"
    mutated.write_text(source, encoding="utf-8")

    with pytest.raises(CaseEmissionError, match="unreviewed cast"):
        emit("qu8-vadd-minmax", rvv_source=mutated)


def test_changed_scalar_local_signedness_is_rejected(tmp_path: Path):
    source = (ROOT / "kernels/target/qu8-vadd-minmax.c").read_text(encoding="utf-8")
    source = source.replace(
        "const int32_t shift = params->scalar.shift;",
        "const uint32_t shift = params->scalar.shift;",
        1,
    )
    mutated = tmp_path / "qu8-vadd-minmax.c"
    mutated.write_text(source, encoding="utf-8")

    with pytest.raises(CaseEmissionError, match="scalar local types changed"):
        emit("qu8-vadd-minmax", rvv_source=mutated)


def test_narrowed_batch_argument_to_vsetvl_is_rejected(tmp_path: Path):
    source = (ROOT / "kernels/target/s8-vclamp.c").read_text(encoding="utf-8")
    source = source.replace(
        "__riscv_vsetvl_e8m8(batch)",
        "__riscv_vsetvl_e8m8((uint8_t) batch)",
        1,
    )
    mutated = tmp_path / "s8-vclamp.c"
    mutated.write_text(source, encoding="utf-8")

    with pytest.raises(CaseEmissionError, match="vsetvl must consume batch"):
        emit("s8-vclamp", rvv_source=mutated)


def test_changed_rvv_active_length_expression_is_rejected(tmp_path: Path):
    source = (ROOT / "kernels/target/s8-vclamp.c").read_text(encoding="utf-8")
    source = source.replace(
        "__riscv_vle8_v_i8m8(input, vl)",
        "__riscv_vle8_v_i8m8(input, -vl)",
        1,
    )
    mutated = tmp_path / "s8-vclamp.c"
    mutated.write_text(source, encoding="utf-8")

    with pytest.raises(CaseEmissionError, match="does not consume active vl"):
        emit("s8-vclamp", rvv_source=mutated)


def test_changed_qu8_branch_active_length_is_rejected(tmp_path: Path):
    source = (ROOT / "kernels/target/qu8-vadd-minmax.c").read_text(encoding="utf-8")
    source = source.replace(
        "__RISCV_VXRM_RNU, vl)",
        "__RISCV_VXRM_RNU, -vl)",
        1,
    )
    mutated = tmp_path / "qu8-vadd-minmax.c"
    mutated.write_text(source, encoding="utf-8")

    with pytest.raises(CaseEmissionError, match="signed-shift branch dataflow changed"):
        emit("qu8-vadd-minmax", rvv_source=mutated)


def test_qu8_shift_calls_must_be_in_opposite_branch_arms(tmp_path: Path):
    source = (ROOT / "kernels/target/qu8-vadd-minmax.c").read_text(encoding="utf-8")
    old = """    if (shift >= 0) {
      vacc = __riscv_vssra_vx_i32m8(vacc, (size_t)shift, __RISCV_VXRM_RNU, vl);
    } else {
      vacc = __riscv_vsll_vx_i32m8(vacc, (size_t)(-shift), vl);
    }
"""
    new = """    if (shift >= 0) {
      vacc = __riscv_vssra_vx_i32m8(vacc, (size_t)shift, __RISCV_VXRM_RNU, vl);
      vacc = __riscv_vsll_vx_i32m8(vacc, (size_t)(-shift), vl);
    } else {
    }
"""
    assert old in source
    mutated = tmp_path / "qu8-vadd-minmax.c"
    mutated.write_text(source.replace(old, new), encoding="utf-8")

    with pytest.raises(CaseEmissionError, match="signed-shift branch dataflow changed"):
        emit("qu8-vadd-minmax", rvv_source=mutated)


def test_unmodeled_nested_rvv_control_is_rejected(tmp_path: Path):
    source = (ROOT / "kernels/target/qu8-vadd-minmax.c").read_text(encoding="utf-8")
    marker = """    if (shift >= 0) {
      vacc = __riscv_vssra_vx_i32m8(vacc, (size_t)shift, __RISCV_VXRM_RNU, vl);
"""
    inserted = marker + "      while (batch > 0) {}\n"
    assert marker in source
    mutated = tmp_path / "qu8-vadd-minmax.c"
    mutated.write_text(source.replace(marker, inserted, 1), encoding="utf-8")

    with pytest.raises(CaseEmissionError, match="RVV control shape changed"):
        emit("qu8-vadd-minmax", rvv_source=mutated)
