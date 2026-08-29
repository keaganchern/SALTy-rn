from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.compiler import (
    CompilerRequest,
    compile_pair,
)
from workflow.verification.elementwise_compiler.heldout import run_heldout_gate
from workflow.verification.elementwise_compiler.proof import (
    check_proof,
    prepare_proof_task,
    run_proof_agent,
)
from workflow.verification.elementwise_compiler.schema import (
    ProofTask,
    Result,
    ResultStatus,
    canonical_json,
    canonical_sha256,
)


ROOT = Path(__file__).resolve().parents[3]
FACADE = ROOT / "src/workflow/verification/lean_backend/facade/s8_vmax_example.h"
pytestmark = pytest.mark.skipif(
    shutil.which("clang") is None or shutil.which("lean") is None,
    reason="Clang and Lean are required",
)


def _compile(output: Path, namespace: str = "SALT.Generated.ProofGateVMax") -> None:
    compile_pair(
        CompilerRequest(
            ROOT,
            ROOT / "examples/s8-vmax-to-lean/neon.c",
            ROOT / "examples/s8-vmax-to-lean/rvv.c",
            "test_neon",
            "test_rvv",
            FACADE,
            FACADE,
            "aarch64-none-elf",
            "riscv64-none-elf",
            namespace,
            output,
        )
    )


def _proof(namespace: str) -> str:
    return f"""import {namespace}.Spec

namespace {namespace}

theorem proveNeonBlock : neonBlockEqualsMapClaim := by
  intro p input h
  let q : BitVec 8 := p.threshold.truncate 8
  have zipMap : ∀ xs : List (BitVec 8),
      List.zipWith bvSignedMax xs (List.replicate xs.length q) =
        xs.map (fun x => bvSignedMax x q) := by
    intro xs
    induction xs with
    | nil => rfl
    | cons x xs ih =>
        simp only [List.length_cons, List.replicate_succ,
          List.zipWith_cons_cons, List.map_cons]
        rw [ih]
  have scalar (x : BitVec 8) : fNeon p x = bvSignedMax x q := by
    simp [fNeon, neonBlock16FromIntrinsics,
      SALT.Intrinsics.Neon.vmaxq_s8, q]
  unfold neonBlock16FromIntrinsics
  simp only
  rw [← h, List.take_length, SALT.Intrinsics.Neon.vmaxq_s8, zipMap]
  exact List.map_congr_left (fun x _ => (scalar x).symm)

theorem proveRvvChunk : rvvChunkEqualsMapClaim := by
  intro p input
  simp [rvvChunkFromIntrinsics, fRvv, SALT.Intrinsics.RVV.vmax_vx]

theorem proveElements : elementFunctionsEqualClaim := by
  intro p x
  simp [fNeon, fRvv, neonBlock16FromIntrinsics, rvvChunkFromIntrinsics,
    SALT.Intrinsics.Neon.vmaxq_s8, SALT.Intrinsics.RVV.vmax_vx]

theorem proveNeonLoop : neonLoopEqualsMapClaim := by
  intro p input divisible
  exact SALT.Kernel.ElementwiseFamily.runFixedNoTail_eq_map 16 (by omega)
    (neonBlock16FromIntrinsics p) (fNeon p) (proveNeonBlock p) input divisible

theorem proveRvvLoop : rvvLoopEqualsMapClaim := by
  intro p input schedule
  exact SALT.Kernel.Schedule.processBlocks_eq_map
    (rvvChunkFromIntrinsics p) (fRvv p) (proveRvvChunk p) input schedule

theorem completeValueEquivalence : completeValueEquivalenceClaim := by
  intro p input schedule divisible
  rw [proveNeonLoop p input divisible, proveRvvLoop p input schedule]
  exact List.map_congr_left (fun x _ => proveElements p x)

end {namespace}
"""


def test_prepare_and_check_frozen_agent_proof(tmp_path: Path) -> None:
    output = tmp_path / "verified"
    namespace = "SALT.Generated.ProofGateVMax"
    _compile(output, namespace)
    task = prepare_proof_task(ROOT, output)

    assert ProofTask.from_record(json.loads((output / "ProofTask.json").read_text())) == task
    assert task.models.parent_sha256 == task.manifest_sha256
    assert task.spec.parent_sha256 == task.models.sha256
    assert task.theorem == f"{namespace}.completeValueEquivalence"
    assert not (output / "Proof.lean").exists()

    writer = tmp_path / "proof_agent.py"
    writer.write_text(
        "import os\n"
        "from pathlib import Path\n"
        f"Path(os.environ['SALTYRN_PROOF_TASK']).with_name('Proof.lean').write_text({_proof(namespace)!r}, encoding='utf-8')\n",
        encoding="utf-8",
    )
    checked = run_proof_agent(ROOT, output, (sys.executable, str(writer)))

    assert checked.result.status is ResultStatus.VERIFIED_VALUE
    assert checked.result.start_closure_sha256 == checked.result.end_closure_sha256
    assert Result.from_record(json.loads((output / "Result.json").read_text())) == checked.result


def test_missing_or_forbidden_proof_is_not_verified(tmp_path: Path) -> None:
    output = tmp_path / "failed"
    _compile(output)
    task = prepare_proof_task(ROOT, output)

    missing = check_proof(ROOT, output)
    assert missing.task == task
    assert missing.result.status is ResultStatus.PROOF_SEARCH_FAILED

    output.joinpath("Proof.lean").write_text(
        "axiom fabricated : True\n", encoding="utf-8"
    )
    forbidden = check_proof(ROOT, output)
    assert forbidden.result.status is ResultStatus.LEAN_FAILED
    assert "forbidden" in forbidden.result.detail


def test_parent_mutation_invalidates_prepared_task(tmp_path: Path) -> None:
    output = tmp_path / "mutated"
    _compile(output)
    prepare_proof_task(ROOT, output)
    spec = output / "Spec.lean"
    spec.write_text(spec.read_text(encoding="utf-8") + "\n-- mutation\n", encoding="utf-8")

    checked = check_proof(ROOT, output)

    assert checked.result.status is ResultStatus.GENERATION_FAILED
    assert "hash chain" in checked.result.detail


@pytest.mark.parametrize(
    ("binding", "message"),
    (
        ("external_condition", "mandatory external-condition audit"),
        ("cross_phase_audit", "mandatory cross-phase audit"),
    ),
)
def test_proof_task_rejects_missing_mandatory_audit_binding(
    tmp_path: Path, binding: str, message: str
) -> None:
    output = tmp_path / binding
    _compile(output)
    index_path = output / "ArtifactIndex.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index.pop("stack_sha256")
    index.pop(binding)
    index["stack_sha256"] = canonical_sha256(index)
    index_path.write_text(canonical_json(index, pretty=True), encoding="utf-8")

    with pytest.raises(RuntimeError, match=message):
        prepare_proof_task(ROOT, output)


def test_heldout_new_program_and_mutation_matrix() -> None:
    def provide(output: Path, namespace: str) -> None:
        output.joinpath("Proof.lean").write_text(_proof(namespace), encoding="utf-8")

    report = run_heldout_gate(ROOT, provide)

    assert report["positive_a"]["status"] == "verified(value)"
    assert report["positive_b_random_identity"]["status"] == "verified(value)"
    assert report["negative_max_to_min"]["status"] == "lean-failed"
    assert set(report["structural_mutations"]) == {
        "pointer-step",
        "loop-update",
        "entry-assert",
        "active-vl",
    }
    assert report["framework_unchanged"] is True
