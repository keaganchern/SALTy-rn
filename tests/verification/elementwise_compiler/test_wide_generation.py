from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.compiler import CompilerRequest, compile_pair
from workflow.verification.elementwise_compiler.intrinsics import IntrinsicResolutionError
from workflow.verification.elementwise_compiler.proof import prepare_proof_task
from workflow.verification.lean_backend.intrinsic_index import (
    CanonicalIntrinsicIndex,
    DescriptorProvenance,
    IntrinsicOccurrence,
)
from workflow.verification.lean_backend.schema import (
    Architecture,
    FloatingType,
    FunctionSignature,
    ImmediateConstraint,
    LeanArgument,
    OperationShape,
    Parameter,
    PointerType,
    ScalarType,
    ScheduleIntrinsic,
    ScheduleOp,
    SemanticIntrinsic,
    Signedness,
    StructuralIntrinsic,
    StructuralOp,
    ValueType,
    VectorType,
    VoidType,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests/fixtures/elementwise_compiler/wide_copy"
pytestmark = pytest.mark.skipif(
    shutil.which("clang") is None or shutil.which("lean") is None,
    reason="Clang and Lean are required",
)


def _signature(result: ValueType, *parameters: tuple[str, ValueType]) -> FunctionSignature:
    return FunctionSignature(
        tuple(Parameter(name, value_type) for name, value_type in parameters),
        result,
    )


def _copy_index(
    suffix: str,
    scalar: ScalarType | FloatingType,
) -> CanonicalIntrinsicIndex:
    size = ScalarType("size_t", None, Signedness.UNSIGNED)
    integer = ScalarType("int", 32, Signedness.SIGNED)
    fixed4 = VectorType(f"salt_{suffix}x4_t", scalar, fixed_lanes=4)
    fixed2 = VectorType(f"salt_{suffix}x2_t", scalar, fixed_lanes=2)
    scalable = VectorType(f"salt_v{suffix}m1_t", scalar, lmul="m1")
    const_pointer = PointerType(scalar, const=True)
    pointer = PointerType(scalar)
    void = VoidType()

    specs = (
        StructuralIntrinsic(
            f"salt_neon_load4_{suffix}",
            Architecture.NEON,
            _signature(fixed4, ("base", const_pointer)),
            OperationShape.LOAD,
            StructuralOp.LOAD,
        ),
        StructuralIntrinsic(
            f"salt_neon_low2_{suffix}",
            Architecture.NEON,
            _signature(fixed2, ("vector", fixed4)),
            OperationShape.EXTRACT,
            StructuralOp.TAKE_LOW,
        ),
        StructuralIntrinsic(
            f"salt_neon_high2_{suffix}",
            Architecture.NEON,
            _signature(fixed2, ("vector", fixed4)),
            OperationShape.EXTRACT,
            StructuralOp.TAKE_HIGH,
        ),
        StructuralIntrinsic(
            f"salt_neon_store4_{suffix}",
            Architecture.NEON,
            _signature(void, ("base", pointer), ("value", fixed4)),
            OperationShape.STORE,
            StructuralOp.STORE,
        ),
        StructuralIntrinsic(
            f"salt_neon_store2_{suffix}",
            Architecture.NEON,
            _signature(void, ("base", pointer), ("value", fixed2)),
            OperationShape.STORE,
            StructuralOp.STORE,
        ),
        StructuralIntrinsic(
            f"salt_neon_store1_{suffix}",
            Architecture.NEON,
            _signature(
                void,
                ("base", pointer),
                ("value", fixed2),
                ("lane", integer),
            ),
            OperationShape.LANE_STORE,
            StructuralOp.LANE_STORE,
            (ImmediateConstraint(2, frozenset({0})),),
        ),
        ScheduleIntrinsic(
            f"salt_rvv_setvl_{suffix}",
            Architecture.RVV,
            _signature(size, ("remaining", size)),
            OperationShape.SCHEDULE,
            ScheduleOp.SET_ACTIVE_LENGTH,
        ),
        StructuralIntrinsic(
            f"salt_rvv_load_{suffix}",
            Architecture.RVV,
            _signature(scalable, ("base", const_pointer), ("vl", size)),
            OperationShape.LOAD,
            StructuralOp.LOAD,
        ),
        StructuralIntrinsic(
            f"salt_rvv_store_{suffix}",
            Architecture.RVV,
            _signature(void, ("base", pointer), ("value", scalable), ("vl", size)),
            OperationShape.STORE,
            StructuralOp.STORE,
        ),
    )
    occurrences = tuple(
        IntrinsicOccurrence(
            spec,
            DescriptorProvenance(
                case_id=f"heldout-{suffix}-copy",
                source_catalog="test_wide_generation._wide_copy_index",
                architecture=spec.architecture,
                spelling=spec.spelling,
            ),
        )
        for spec in specs
    )
    return CanonicalIntrinsicIndex.from_occurrences(occurrences)


def _wide_copy_index(width: int) -> CanonicalIntrinsicIndex:
    return _copy_index(
        f"u{width}",
        ScalarType(f"uint{width}_t", width, Signedness.UNSIGNED),
    )


def _f32_copy_index() -> CanonicalIntrinsicIndex:
    return _copy_index("f32", FloatingType("float", 32))


def _mixed_i32_i16_index() -> CanonicalIntrinsicIndex:
    i16 = ScalarType("int16_t", 16, Signedness.SIGNED)
    i32 = ScalarType("int32_t", 32, Signedness.SIGNED)
    size = ScalarType("size_t", None, Signedness.UNSIGNED)
    uint = ScalarType("unsigned int", 32, Signedness.UNSIGNED)
    fixed_i32 = VectorType("salt_i32x4_t", i32, fixed_lanes=4)
    fixed_i16 = VectorType("salt_i16x4_t", i16, fixed_lanes=4)
    scalable_i32 = VectorType("salt_vi32m1_t", i32, lmul="m1")
    scalable_i16 = VectorType("salt_vi16m1_t", i16, lmul="m1")
    void = VoidType()
    specs = (
        StructuralIntrinsic(
            "salt_neon_load4_i32",
            Architecture.NEON,
            _signature(fixed_i32, ("base", PointerType(i32, const=True))),
            OperationShape.LOAD,
            StructuralOp.LOAD,
        ),
        SemanticIntrinsic(
            "salt_neon_narrow_i16",
            Architecture.NEON,
            _signature(fixed_i16, ("vector", fixed_i32)),
            OperationShape.VECTOR_UNARY,
            "SALT.Intrinsics.Neon.vqmovn_s32",
            (LeanArgument(0),),
        ),
        StructuralIntrinsic(
            "salt_neon_store4_i16",
            Architecture.NEON,
            _signature(void, ("base", PointerType(i16)), ("value", fixed_i16)),
            OperationShape.STORE,
            StructuralOp.STORE,
        ),
        ScheduleIntrinsic(
            "salt_rvv_setvl_i32_i16",
            Architecture.RVV,
            _signature(size, ("remaining", size)),
            OperationShape.SCHEDULE,
            ScheduleOp.SET_ACTIVE_LENGTH,
        ),
        StructuralIntrinsic(
            "salt_rvv_load_i32",
            Architecture.RVV,
            _signature(
                scalable_i32,
                ("base", PointerType(i32, const=True)),
                ("vl", size),
            ),
            OperationShape.LOAD,
            StructuralOp.LOAD,
        ),
        SemanticIntrinsic(
            "salt_rvv_narrow_i16",
            Architecture.RVV,
            _signature(
                scalable_i16,
                ("vector", scalable_i32),
                ("shift", size),
                ("vxrm", uint),
                ("vl", size),
            ),
            OperationShape.VECTOR_UNARY,
            "SALT.Intrinsics.RVV.vnclip_wx_i16",
            (LeanArgument(0),),
            (
                ImmediateConstraint(1, frozenset({0})),
                ImmediateConstraint(2, frozenset({2})),
            ),
        ),
        StructuralIntrinsic(
            "salt_rvv_store_i16",
            Architecture.RVV,
            _signature(
                void,
                ("base", PointerType(i16)),
                ("value", scalable_i16),
                ("vl", size),
            ),
            OperationShape.STORE,
            StructuralOp.STORE,
        ),
    )
    occurrences = tuple(
        IntrinsicOccurrence(
            spec,
            DescriptorProvenance(
                case_id="heldout-mixed-i32-i16",
                source_catalog="test_wide_generation._mixed_i32_i16_index",
                architecture=spec.architecture,
                spelling=spec.spelling,
            ),
        )
        for spec in specs
    )
    return CanonicalIntrinsicIndex.from_occurrences(occurrences)


@pytest.mark.parametrize("width", (16, 32))
def test_wide_fixed_tail_stack_is_generated_and_elaborates(
    tmp_path: Path, width: int
) -> None:
    output = tmp_path / f"u{width}"
    result = compile_pair(
        CompilerRequest(
            repository_root=ROOT,
            neon_source=FIXTURES / f"u{width}-neon.c",
            rvv_source=FIXTURES / f"u{width}-rvv.c",
            neon_function=f"test_neon_u{width}",
            rvv_function=f"test_rvv_u{width}",
            neon_facade=FIXTURES / "facade.h",
            rvv_facade=FIXTURES / "facade.h",
            neon_target="aarch64-none-elf",
            rvv_target="riscv64-none-elf",
            namespace=f"SALT.Generated.HeldoutU{width}Copy",
            output_directory=output,
        ),
        intrinsic_index=_wide_copy_index(width),
    )

    assert result.recognition.element_width == width
    assert result.recognition.output_width == width
    assert result.recognition.neon.lanes == 4
    assert result.recognition.neon.store_widths == (2, 1)
    assert f"List (BitVec {width})" in result.stack.models_text
    assert "runFixedChunkTail 4" in result.stack.models_text
    assert "theorem " not in result.stack.spec_text

    task = prepare_proof_task(ROOT, output)
    assert task.theorem == f"SALT.Generated.HeldoutU{width}Copy.completeValueEquivalence"


def test_f32_fixed_tail_stack_is_parsed_generated_and_elaborates(tmp_path: Path) -> None:
    output = tmp_path / "f32"
    namespace = "SALT.Generated.HeldoutF32Copy"
    result = compile_pair(
        CompilerRequest(
            repository_root=ROOT,
            neon_source=FIXTURES / "f32-neon.c",
            rvv_source=FIXTURES / "f32-rvv.c",
            neon_function="test_neon_f32",
            rvv_function="test_rvv_f32",
            neon_facade=FIXTURES / "facade.h",
            rvv_facade=FIXTURES / "facade.h",
            neon_target="aarch64-none-elf",
            rvv_target="riscv64-none-elf",
            namespace=namespace,
            output_directory=output,
        ),
        intrinsic_index=_f32_copy_index(),
    )

    assert result.recognition.element_c_type == "float"
    assert result.recognition.element_width == 32
    assert "List (BitVec 32)" in result.stack.models_text
    assert prepare_proof_task(ROOT, output).theorem == f"{namespace}.completeValueEquivalence"


def test_real_f32_structural_library_reaches_proof_task_without_local_index(
    tmp_path: Path,
) -> None:
    output = tmp_path / "real-f32"
    namespace = "SALT.Generated.HeldoutRealF32Copy"
    result = compile_pair(
        CompilerRequest(
            repository_root=ROOT,
            neon_source=FIXTURES / "real-f32-neon.c",
            rvv_source=FIXTURES / "real-f32-rvv.c",
            neon_function="test_neon_real_f32",
            rvv_function="test_rvv_real_f32",
            neon_facade=(
                ROOT
                / "src/workflow/verification/lean_backend/facade/elementwise_shared.h"
            ),
            rvv_facade=(
                ROOT
                / "src/workflow/verification/lean_backend/facade/elementwise_shared.h"
            ),
            neon_target="aarch64-none-elf",
            rvv_target="riscv64-none-elf",
            namespace=namespace,
            output_directory=output,
        )
    )

    assert {item.spelling for item in result.intrinsics.capabilities} == {
        "vget_high_f32",
        "vget_low_f32",
        "vld1q_f32",
        "vst1_f32",
        "vst1_lane_f32",
        "vst1q_f32",
        "__riscv_vsetvl_e32m8",
        "__riscv_vle32_v_f32m8",
        "__riscv_vse32_v_f32m8",
    }
    assert prepare_proof_task(ROOT, output).theorem == f"{namespace}.completeValueEquivalence"


def test_real_f32_lane_store_uses_the_requested_lane(tmp_path: Path) -> None:
    output = tmp_path / "real-f32-lane1"
    result = compile_pair(
        CompilerRequest(
            repository_root=ROOT,
            neon_source=FIXTURES / "real-f32-neon-lane1.c",
            rvv_source=FIXTURES / "real-f32-rvv.c",
            neon_function="test_neon_real_f32_lane1",
            rvv_function="test_rvv_real_f32",
            neon_facade=(
                ROOT
                / "src/workflow/verification/lean_backend/facade/elementwise_shared.h"
            ),
            rvv_facade=(
                ROOT
                / "src/workflow/verification/lean_backend/facade/elementwise_shared.h"
            ),
            neon_target="aarch64-none-elf",
            rvv_target="riscv64-none-elf",
            namespace="SALT.Generated.HeldoutRealF32Lane1",
            output_directory=output,
        )
    )

    assert ").drop 1).take 1" in result.stack.models_text
    assert "then (after2).take 1" not in result.stack.models_text


def test_real_f32_lane_store_rejects_out_of_range_lane(tmp_path: Path) -> None:
    with pytest.raises(
        IntrinsicResolutionError,
        match="vst1_lane_f32: configured index returned same-name-mismatch",
    ):
        compile_pair(
            CompilerRequest(
                repository_root=ROOT,
                neon_source=FIXTURES / "real-f32-neon-lane2.c",
                rvv_source=FIXTURES / "real-f32-rvv.c",
                neon_function="test_neon_real_f32_lane2",
                rvv_function="test_rvv_real_f32",
                neon_facade=(
                    ROOT
                    / "src/workflow/verification/lean_backend/facade/elementwise_shared.h"
                ),
                rvv_facade=(
                    ROOT
                    / "src/workflow/verification/lean_backend/facade/elementwise_shared.h"
                ),
                neon_target="aarch64-none-elf",
                rvv_target="riscv64-none-elf",
                namespace="SALT.Generated.HeldoutRealF32Lane2",
                output_directory=tmp_path / "real-f32-lane2",
            )
        )


def test_u16_no_tail_stack_is_generated_and_elaborates(tmp_path: Path) -> None:
    output = tmp_path / "u16-no-tail"
    namespace = "SALT.Generated.HeldoutU16NoTail"
    result = compile_pair(
        CompilerRequest(
            repository_root=ROOT,
            neon_source=FIXTURES / "u16-no-tail-neon.c",
            rvv_source=FIXTURES / "u16-no-tail-rvv.c",
            neon_function="test_neon_u16_no_tail",
            rvv_function="test_rvv_u16_no_tail",
            neon_facade=FIXTURES / "facade.h",
            rvv_facade=FIXTURES / "facade.h",
            neon_target="aarch64-none-elf",
            rvv_target="riscv64-none-elf",
            namespace=namespace,
            output_directory=output,
        ),
        intrinsic_index=_wide_copy_index(16),
    )

    assert result.recognition.neon.kind.value == "fixed-no-tail"
    assert "runFixedNoTail 4" in result.stack.models_text
    assert "4 ∣ input.length" in result.stack.spec_text
    assert prepare_proof_task(ROOT, output).theorem == f"{namespace}.completeValueEquivalence"


def test_mixed_i32_i16_stack_is_generated_and_elaborates(tmp_path: Path) -> None:
    output = tmp_path / "i32-i16-no-tail"
    namespace = "SALT.Generated.HeldoutI32I16NoTail"
    result = compile_pair(
        CompilerRequest(
            repository_root=ROOT,
            neon_source=FIXTURES / "i32-i16-no-tail-neon.c",
            rvv_source=FIXTURES / "i32-i16-no-tail-rvv.c",
            neon_function="test_neon_i32_i16_no_tail",
            rvv_function="test_rvv_i32_i16_no_tail",
            neon_facade=FIXTURES / "facade.h",
            rvv_facade=FIXTURES / "facade.h",
            neon_target="aarch64-none-elf",
            rvv_target="riscv64-none-elf",
            namespace=namespace,
            output_directory=output,
        ),
        intrinsic_index=_mixed_i32_i16_index(),
    )

    assert result.recognition.element_width == 32
    assert result.recognition.output_width == 16
    assert "(input : List (BitVec 32))" in result.stack.models_text
    assert ": List (BitVec 16) :=" in result.stack.models_text
    assert "(x : BitVec 32) : BitVec 16" in result.stack.models_text
    assert prepare_proof_task(ROOT, output).theorem == f"{namespace}.completeValueEquivalence"


def test_wide_rvv_byte_to_element_count_must_match_stream_type(tmp_path: Path) -> None:
    fixture = Path(tempfile.mkdtemp(prefix=".wide-count-mutation-", dir=ROOT))
    try:
        source = (FIXTURES / "u16-rvv.c").read_text(encoding="utf-8")
        mutated = fixture / "rvv.c"
        mutated.write_text(
            source.replace(
                "size_t n = batch / sizeof(uint16_t)",
                "size_t n = batch / sizeof(uint32_t)",
                1,
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match=r"batch / sizeof\(uint16_t\)"):
            compile_pair(
                CompilerRequest(
                    repository_root=ROOT,
                    neon_source=FIXTURES / "u16-neon.c",
                    rvv_source=mutated,
                    neon_function="test_neon_u16",
                    rvv_function="test_rvv_u16",
                    neon_facade=FIXTURES / "facade.h",
                    rvv_facade=FIXTURES / "facade.h",
                    neon_target="aarch64-none-elf",
                    rvv_target="riscv64-none-elf",
                    namespace="SALT.Generated.RejectedWideCount",
                    output_directory=tmp_path / "rejected",
                ),
                intrinsic_index=_wide_copy_index(16),
            )
    finally:
        shutil.rmtree(fixture)


def test_wide_rvv_cannot_use_byte_count_as_element_count(tmp_path: Path) -> None:
    fixture = Path(tempfile.mkdtemp(prefix=".wide-direct-byte-count-", dir=ROOT))
    try:
        source = (FIXTURES / "u16-rvv.c").read_text(encoding="utf-8")
        mutated = fixture / "rvv.c"
        mutated.write_text(
            source.replace(
                "  size_t n = batch / sizeof(uint16_t);\n  while (n > 0)",
                "  while (batch > 0)",
                1,
            )
            .replace("salt_rvv_setvl_u16(n)", "salt_rvv_setvl_u16(batch)", 1)
            .replace("    n -= vl;", "    batch -= vl;", 1),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="byte count directly"):
            compile_pair(
                CompilerRequest(
                    repository_root=ROOT,
                    neon_source=FIXTURES / "u16-neon.c",
                    rvv_source=mutated,
                    neon_function="test_neon_u16",
                    rvv_function="test_rvv_u16",
                    neon_facade=FIXTURES / "facade.h",
                    rvv_facade=FIXTURES / "facade.h",
                    neon_target="aarch64-none-elf",
                    rvv_target="riscv64-none-elf",
                    namespace="SALT.Generated.RejectedDirectByteCount",
                    output_directory=tmp_path / "rejected-direct-count",
                ),
                intrinsic_index=_wide_copy_index(16),
            )
    finally:
        shutil.rmtree(fixture)
