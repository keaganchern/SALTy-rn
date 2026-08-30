from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.compiler import (
    CompilerRequest,
    _compiler_dependencies,
    _compiler_digest,
    compile_pair,
)
from workflow.verification.elementwise_compiler.schema import ProgramManifest


ROOT = Path(__file__).resolve().parents[3]
FACADE_ROOT = ROOT / "src/workflow/verification/lean_backend/facade"
pytestmark = pytest.mark.skipif(
    shutil.which("clang") is None, reason="system clang required"
)


def _request(
    case: str,
    output: Path,
    *,
    neon_source: Path | None = None,
    namespace: str | None = None,
):
    facade = FACADE_ROOT / f"{case.replace('-', '_')}.h"
    return CompilerRequest(
        repository_root=ROOT,
        neon_source=neon_source or ROOT / "kernels/source" / f"{case}.c",
        rvv_source=ROOT / "kernels/target" / f"{case}.c",
        neon_function="test_neon",
        rvv_function="test_rvv",
        neon_facade=facade,
        rvv_facade=facade,
        neon_target="aarch64-none-elf",
        rvv_target="riscv64-none-elf",
        namespace=namespace or "SALT.Generated.AutomaticFixture",
        output_directory=output,
    )


def _vmax_request(output: Path, namespace: str = "SALT.Generated.HeldoutVMax"):
    facade = FACADE_ROOT / "s8_vmax_example.h"
    return CompilerRequest(
        repository_root=ROOT,
        neon_source=ROOT / "examples/s8-vmax-to-lean/neon.c",
        rvv_source=ROOT / "examples/s8-vmax-to-lean/rvv.c",
        neon_function="test_neon",
        rvv_function="test_rvv",
        neon_facade=facade,
        rvv_facade=facade,
        neon_target="aarch64-none-elf",
        rvv_target="riscv64-none-elf",
        namespace=namespace,
        output_directory=output,
    )


def _shared_request(case: str, output: Path, namespace: str):
    facade = FACADE_ROOT / "elementwise_shared.h"
    return CompilerRequest(
        repository_root=ROOT,
        neon_source=ROOT / "kernels/source" / f"{case}.c",
        rvv_source=ROOT / "kernels/target" / f"{case}.c",
        neon_function="test_neon",
        rvv_function="test_rvv",
        neon_facade=facade,
        rvv_facade=facade,
        neon_target="aarch64-none-elf",
        rvv_target="riscv64-none-elf",
        namespace=namespace,
        output_directory=output,
    )


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("ascii"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_compiler_digest_tracks_only_reachable_generation_code(tmp_path: Path) -> None:
    fixture = tmp_path / "repository"
    shutil.copytree(ROOT / "src/workflow", fixture / "src/workflow")
    dependencies = {
        path.relative_to(fixture).as_posix()
        for path in _compiler_dependencies(fixture)
    }
    assert "src/workflow/verification/elementwise_compiler/compiler.py" in dependencies
    assert "src/workflow/verification/elementwise_compiler/emit.py" in dependencies
    assert "src/workflow/verification/lean_backend/intrinsic_library.py" in dependencies
    assert "src/workflow/verification/elementwise_compiler/proof.py" not in dependencies
    assert (
        "src/workflow/verification/elementwise_compiler/program_reviews.py"
        not in dependencies
    )

    original = _compiler_digest(fixture)
    proof = fixture / "src/workflow/verification/elementwise_compiler/proof.py"
    proof.write_text(proof.read_text(encoding="utf-8") + "\n# unrelated\n", encoding="utf-8")
    assert _compiler_digest(fixture) == original

    emitter = fixture / "src/workflow/verification/elementwise_compiler/emit.py"
    emitter.write_text(
        emitter.read_text(encoding="utf-8") + "\n# generation change\n",
        encoding="utf-8",
    )
    assert _compiler_digest(fixture) != original


def test_real_fixed_tail_pair_generates_complete_deterministic_stack(
    tmp_path: Path,
) -> None:
    output = tmp_path / "first"
    first = compile_pair(_request("qs8-vcvt", output))
    first_digest = _tree_digest(output)
    shutil.rmtree(output)
    second = compile_pair(_request("qs8-vcvt", output))

    assert _tree_digest(output) == first_digest
    assert first.manifest == second.manifest
    assert first.models == second.models
    assert first.spec == second.spec
    assert len(first.recognition.local_assertions) == 2
    assert len(first.intrinsics.capabilities) == 25

    manifest_record = json.loads((output / "ProgramManifest.json").read_text())
    assert ProgramManifest.from_record(manifest_record) == first.manifest
    index = json.loads((output / "ArtifactIndex.json").read_text())
    assert index["manifest"]["sha256"] == first.manifest.sha256
    assert index["models"]["parent_sha256"] == first.manifest.sha256
    assert index["spec"]["parent_sha256"] == first.models.sha256


def test_regeneration_replaces_legacy_capability_copies_with_global_refs(
    tmp_path: Path,
) -> None:
    output = tmp_path / "out"
    compile_pair(_request("qs8-vcvt", output))
    stale = output / "Capabilities/stale-capability.json"
    stale.parent.mkdir()
    stale.write_text("{}\n", encoding="utf-8")

    compilation = compile_pair(_request("qs8-vcvt", output))
    index = json.loads((output / "ArtifactIndex.json").read_text(encoding="utf-8"))
    expected = {
        *compilation.manifest.intrinsic_capabilities,
        compilation.manifest.layout.capability,
        *(schedule.capability for schedule in compilation.manifest.schedules),
    }
    assert not (output / "Capabilities").exists()
    assert {
        (item["capability_id"], item["version"], item["sha256"])
        for item in index["capabilities"]
    } == {(item.capability_id, item.version, item.sha256) for item in expected}


def test_normalized_fixed_no_tail_pair_uses_same_generic_compiler(
    tmp_path: Path,
) -> None:
    result = compile_pair(_vmax_request(tmp_path / "vmax"))
    assert result.recognition.neon.kind.value == "fixed-no-tail"
    assert result.manifest.contracts.neon == result.manifest.contracts.rvv
    assert "runFixedNoTail 16" in result.stack.models_text
    assert "16 ∣ input.length" in result.stack.spec_text


def test_generated_models_and_spec_are_separate_and_proof_free(tmp_path: Path) -> None:
    result = compile_pair(_request("qs8-vcvt", tmp_path / "out"))
    models = result.stack.models_text
    spec = result.stack.spec_text
    assert "def fNeon" in models
    assert "def fRvv" in models
    assert "neonValueLoopWithOverreadFromIntrinsics" in models
    assert "def completeValueEquivalenceClaim : Prop" in spec
    assert "theorem " not in spec
    for forbidden in ("sorry", "admit", "axiom", "unsafe"):
        assert forbidden not in spec


def test_binary_pair_uses_same_compiler_and_schedule_capabilities(
    tmp_path: Path,
) -> None:
    unary = compile_pair(_request("qs8-vcvt", tmp_path / "unary"))
    binary = compile_pair(
        _request(
            "qu8-vadd-minmax",
            tmp_path / "binary",
            namespace="SALT.Randomized.Deep.BinaryFixture",
        )
    )
    assert len(unary.recognition.inputs) == 1
    assert len(binary.recognition.inputs) == 2
    assert (
        unary.recognition.schedule_capabilities
        == binary.recognition.schedule_capabilities
    )
    assert "List.zipWith (fNeon p)" in binary.stack.spec_text
    assert "SALT.Randomized.Deep.BinaryFixture" in binary.stack.models_text


def test_scalar_broadcast_pair_remains_a_unary_map(tmp_path: Path) -> None:
    result = compile_pair(
        _shared_request(
            "f32-vmulc",
            tmp_path / "f32-vmulc",
            "SALT.Generated.F32VMulCBroadcast",
        )
    )

    assert result.recognition.inputs == ("input_a",)
    assert result.recognition.broadcast_inputs == ("input_b",)
    assert result.recognition.layout_capability.kind.value == (
        "scalar-lane-with-broadcast"
    )
    assert result.manifest.layout.broadcast_input_streams == ("input_b",)
    assert "broadcast_input_b : BitVec 32" in result.stack.models_text
    assert "List.replicate 4 (p.broadcast_input_b)" in result.stack.models_text
    assert "vfmul_vf_f32 (va_0) (p.broadcast_input_b)" in result.stack.models_text
    assert "input_a.map (fNeon p)" in result.stack.spec_text
    assert "List.zipWith (fNeon p)" not in result.stack.spec_text


def test_parameter_storage_widths_come_from_the_c_facade(tmp_path: Path) -> None:
    result = compile_pair(
        _shared_request(
            "qs8-vmul-minmax-fp32",
            tmp_path / "qs8-vmul",
            "SALT.Generated.QS8VMulStorageWidths",
        )
    )
    models = result.stack.models_text

    for declaration in (
        "a_zero_point : BitVec 8",
        "b_zero_point : BitVec 8",
        "output_zero_point : BitVec 16",
        "output_min : BitVec 8",
        "output_max : BitVec 8",
        "scale : BitVec 32",
    ):
        assert declaration in models
    assert "(p.output_zero_point).signExtend 32" in models
    assert "vfcvt_x_f_v_i32_rne" in models
    assert "vqmovn_high_s32" in models


def test_nested_binary_two_phase_pair_generates_the_parameterized_schedule(
    tmp_path: Path,
) -> None:
    result = compile_pair(
        _request(
            "qs8-vadd-minmax",
            tmp_path / "two-phase",
            namespace="SALT.Randomized.NestedTwoPhase",
        )
    )

    assert result.recognition.neon.phase_widths == (16, 8)
    assert "runTwoPhaseTail2 16 8" in result.stack.models_text
    assert "def neonBlock8FromIntrinsics" in result.stack.models_text
    assert "def fNeonSecondary" in result.stack.models_text
    assert "List.zipWith (fNeonSecondary p)" in result.stack.spec_text
    assert "def neonPhaseFunctionsEqualClaim : Prop" in result.stack.spec_text
    assert "List.zipWith (fNeon p)" in result.stack.spec_text
    assert "theorem " not in result.stack.spec_text


def test_separate_loop_two_phase_pair_uses_the_same_parameterized_schedule(
    tmp_path: Path,
) -> None:
    result = compile_pair(
        _request(
            "s8-vclamp",
            tmp_path / "two-phase",
            namespace="SALT.Randomized.SeparateTwoPhase",
        )
    )

    assert result.recognition.neon.phase_widths == (64, 8)
    assert "runTwoPhaseTail 64 8" in result.stack.models_text
    assert "def neonBlock8FromIntrinsics" in result.stack.models_text
    assert "def fNeonSecondary" in result.stack.models_text
    assert "input.map (fNeonSecondary p)" in result.stack.spec_text
    assert "def neonPhaseFunctionsEqualClaim : Prop" in result.stack.spec_text
    assert "s8-vclamp" not in result.stack.models_text
    assert "call_0018" not in result.stack.models_text


def test_separate_two_phase_adapter_survives_shifted_call_ids_and_random_identity(
    tmp_path: Path,
) -> None:
    fixture = Path(tempfile.mkdtemp(prefix=".elementwise-two-phase-", dir=ROOT))
    try:
        neon = (ROOT / "kernels/source/s8-vclamp.c").read_text(encoding="utf-8")
        marker = "    vacc0 = vmaxq_s8(vacc0, voutput_min);\n"
        assert neon.count(marker) == 1
        neon = neon.replace(marker, marker + marker, 1).replace(
            "test_neon", "randomized_neon_phase", 1
        )
        rvv = (ROOT / "kernels/target/s8-vclamp.c").read_text(encoding="utf-8")
        rvv = rvv.replace("test_rvv", "randomized_rvv_phase", 1)
        neon_path = fixture / "unseen_left.c"
        rvv_path = fixture / "unseen_right.c"
        neon_path.write_text(neon, encoding="utf-8")
        rvv_path.write_text(rvv, encoding="utf-8")
        facade = FACADE_ROOT / "s8_vclamp.h"

        result = compile_pair(
            CompilerRequest(
                repository_root=ROOT,
                neon_source=neon_path,
                rvv_source=rvv_path,
                neon_function="randomized_neon_phase",
                rvv_function="randomized_rvv_phase",
                neon_facade=facade,
                rvv_facade=facade,
                neon_target="aarch64-none-elf",
                rvv_target="riscv64-none-elf",
                namespace="SALT.Randomized.ShiftedTwoPhase",
                output_directory=tmp_path / "shifted",
            )
        )

        assert result.recognition.neon.phase_widths == (64, 8)
        assert "runTwoPhaseTail 64 8" in result.stack.models_text
        assert "SALT.Intrinsics.Neon.vmaxq_s8" in result.stack.models_text
    finally:
        shutil.rmtree(fixture)


def test_pointer_step_mutation_fails_before_artifacts_are_written(
    tmp_path: Path,
) -> None:
    source = ROOT / "kernels/source/qs8-vcvt.c"
    mutated = ROOT / "kernels/source/compiler-heldout-pointer-step.c"
    mutated.write_text(
        source.read_text(encoding="utf-8").replace("input += 8", "input += 7", 1),
        encoding="utf-8",
    )
    try:
        output = tmp_path / "rejected"
        with pytest.raises(Exception, match="pointer|update|footprint"):
            compile_pair(_request("qs8-vcvt", output, neon_source=mutated))
        assert not (output / "ArtifactIndex.json").exists()
    finally:
        mutated.unlink(missing_ok=True)


def test_intrinsic_capabilities_are_reused_across_program_manifests(
    tmp_path: Path,
) -> None:
    first = compile_pair(_request("qs8-vcvt", tmp_path / "first"))
    second = compile_pair(_request("qs8-vlrelu", tmp_path / "second"))
    first_refs = set(first.manifest.intrinsic_capabilities)
    second_refs = set(second.manifest.intrinsic_capabilities)
    assert first_refs & second_refs
    assert first.manifest.sha256 != second.manifest.sha256
