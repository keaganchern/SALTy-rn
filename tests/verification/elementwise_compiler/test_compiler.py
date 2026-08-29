from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.compiler import (
    CompilerRequest,
    compile_pair,
)
from workflow.verification.elementwise_compiler.schema import ProgramManifest


ROOT = Path(__file__).resolve().parents[3]
FACADE_ROOT = ROOT / "src/workflow/verification/lean_backend/facade"
pytestmark = pytest.mark.skipif(shutil.which("clang") is None, reason="system clang required")


def _request(case: str, output: Path, *, neon_source: Path | None = None, namespace: str | None = None):
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


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("ascii"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_real_fixed_tail_pair_generates_complete_deterministic_stack(tmp_path: Path) -> None:
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


def test_normalized_fixed_no_tail_pair_uses_same_generic_compiler(tmp_path: Path) -> None:
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


def test_binary_pair_uses_same_compiler_and_schedule_capabilities(tmp_path: Path) -> None:
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
    assert unary.recognition.schedule_capabilities == binary.recognition.schedule_capabilities
    assert "List.zipWith (fNeon p)" in binary.stack.spec_text
    assert "SALT.Randomized.Deep.BinaryFixture" in binary.stack.models_text


def test_pointer_step_mutation_fails_before_artifacts_are_written(tmp_path: Path) -> None:
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


def test_intrinsic_capabilities_are_reused_across_program_manifests(tmp_path: Path) -> None:
    first = compile_pair(_request("qs8-vcvt", tmp_path / "first"))
    second = compile_pair(_request("qs8-vlrelu", tmp_path / "second"))
    first_refs = set(first.manifest.intrinsic_capabilities)
    second_refs = set(second.manifest.intrinsic_capabilities)
    assert first_refs & second_refs
    assert first.manifest.sha256 != second.manifest.sha256
