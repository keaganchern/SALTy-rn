import Neon2LeanDemo.S8Clamp16.Proof

namespace Neon2LeanDemo.S8Clamp16.Mutation

open Neon2LeanDemo.Production
open Neon2LeanDemo.S8Clamp16
open Neon2LeanDemo.S8Clamp16.Generated

private def replaceMinWithMax (operation : Operation) : Operation :=
  if operation.nodeId = 13 then
    { operation with
      operation := { operation.operation with spelling := "__riscv_vmax_vx_i8m1" } }
  else
    operation

/-- A supported-subset semantic mutation: lowering succeeds and produces different IR. -/
def mutatedTargetIR : KernelIR :=
  { targetIR with
    blocks := targetIR.blocks.map fun block =>
      { block with operations := block.operations.map replaceMinWithMax } }

example : mutatedTargetIR.checkIntegerOnly registry = .ok () := by
  rfl

example : mutatedTargetIR.hasSingleBlockUseOrder = true := by
  rfl

example : mutatedTargetIR.hasConsistentCoverageBinding targetEnvelope = true := by
  decide

def counterexampleInput : List S8Byte :=
  List.replicate 16 (BitVec.ofInt 8 100)

def counterexampleSchedule : List Nat := [3, 5, 8]

example : Neon2LeanDemo.S8VClamp.PositivePartition 16 counterexampleSchedule := by
  simp [counterexampleSchedule, Neon2LeanDemo.S8VClamp.PositivePartition]

/-- Lean execution rejects equivalence even though the mutated operation is supported. -/
example :
    executeValues registry sourceControl sourceIR 100 200
        (BitVec.ofInt 8 (-10)) (BitVec.ofInt 8 20) [] counterexampleInput !=
      executeValues registry targetControl mutatedTargetIR 100 200
        (BitVec.ofInt 8 (-10)) (BitVec.ofInt 8 20) counterexampleSchedule
        counterexampleInput := by
  decide

end Neon2LeanDemo.S8Clamp16.Mutation
