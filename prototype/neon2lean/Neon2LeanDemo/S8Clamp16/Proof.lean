import Neon2LeanDemo.S8Clamp16.Binding
import Neon2LeanDemo.S8Clamp16.Contract
import Neon2LeanDemo.S8VClamp.Proof

namespace Neon2LeanDemo.S8Clamp16

open Neon2LeanDemo.Production
open Neon2LeanDemo.S8Clamp16.Generated

theorem source_chunk_refines (input : List S8Byte) (lo hi : S8Byte)
    (inputBase outputBase : Address)
    (hLength : input.length = 16) :
    executeChunk registry sourceIR
      { inputBase := inputBase
        outputBase := outputBase
        input := input
        lo := lo
        hi := hi
        remaining := 16 } =
      some (input.map (signedClampS8 lo hi)) := by
  simp only [executeChunk, source_registry_checked, source_use_order_checked, Bool.not_true]
  simp [sourceIR, registry, KernelIR.block?, findBlock?, seedEnvironment, seedParameter, RuntimeEnv.insert,
    interpretOperations, interpretOperation, interpretOpcode, operands, RuntimeEnv.lookup?,
    withResult, zipVector, checkedVector, hLength, signedClampS8]

theorem target_chunk_refines (input : List S8Byte) (lo hi : S8Byte) (remaining : Nat)
    (inputBase outputBase : Address)
    (hPositive : 0 < input.length) (hFits : input.length <= remaining) :
    executeChunk registry targetIR
      { inputBase := inputBase
        outputBase := outputBase
        input := input
        lo := lo
        hi := hi
        remaining := remaining } =
      some (input.map (signedClampS8 lo hi)) := by
  simp only [executeChunk, target_registry_checked, target_use_order_checked, Bool.not_true]
  simp [targetIR, registry, KernelIR.block?, findBlock?, seedEnvironment, seedParameter,
    RuntimeEnv.insert, interpretOperations, interpretOperation, interpretOpcode, operands,
    RuntimeEnv.lookup?, withResult, mapVector, vectorLength?, checkedVector, hPositive, hFits,
    signedClampS8]

theorem source_values_refine (input : List S8Byte) (lo hi : S8Byte)
    (inputBase outputBase : Address) (hLength : input.length = 16) :
    executeValues registry sourceControl sourceIR inputBase outputBase lo hi [] input =
      some (input.map (signedClampS8 lo hi)) := by
  simp [executeValues, sourceControl, hLength,
    source_chunk_refines input lo hi inputBase outputBase hLength]

open Neon2LeanDemo.S8VClamp in
theorem target_stripMine_refines (input : List S8Byte) (lo hi : S8Byte)
    (inputBase outputBase : Address) (chunks : List Nat)
    (hLegal : PositivePartition input.length chunks) :
    executeStripMine registry targetIR inputBase outputBase lo hi input.length chunks input =
      some (input.map (signedClampS8 lo hi)) := by
  induction chunks generalizing input inputBase outputBase with
  | nil =>
      have hLength : input.length = 0 := hLegal
      have hInput : input = [] := List.length_eq_zero_iff.mp hLength
      simp [executeStripMine, hInput]
  | cons chunk chunks ih =>
      rcases hLegal with ⟨hPositive, hFits, hRest⟩
      have hTakeLength : (input.take chunk).length = chunk := by
        simp [List.length_take, Nat.min_eq_left hFits]
      have hDropLength : (input.drop chunk).length = input.length - chunk := by
        simp
      have hDropLegal : PositivePartition (input.drop chunk).length chunks := by
        simpa [hDropLength] using hRest
      rw [executeStripMine]
      simp [hPositive, hFits, hTakeLength,
        target_chunk_refines (input.take chunk) lo hi input.length inputBase outputBase]
      rw [← hDropLength]
      rw [ih (input.drop chunk) (inputBase + chunk) (outputBase + chunk) hDropLegal]
      simp [List.take_append_drop]

open Neon2LeanDemo.S8VClamp in
theorem target_values_refine (input : List S8Byte) (lo hi : S8Byte)
    (inputBase outputBase : Address) (chunks : List Nat)
    (hLength : input.length = 16) (hLegal : PositivePartition 16 chunks) :
    executeValues registry targetControl targetIR inputBase outputBase lo hi chunks input =
      some (input.map (signedClampS8 lo hi)) := by
  have hInputLegal : PositivePartition input.length chunks := by
    simpa [hLength] using hLegal
  simp [executeValues, targetControl, hLength]
  rw [← hLength]
  exact target_stripMine_refines input lo hi inputBase outputBase chunks hInputLegal

open Neon2LeanDemo.S8VClamp in
/-- Direct equivalence of the two generated semantic IR programs. -/
theorem generated_value_equivalence (input : List S8Byte) (lo hi : S8Byte)
    (inputBase outputBase : Address) (chunks : List Nat)
    (hLength : input.length = 16) (hLegal : PositivePartition 16 chunks) :
    executeValues registry sourceControl sourceIR inputBase outputBase lo hi [] input =
      executeValues registry targetControl targetIR inputBase outputBase lo hi chunks input := by
  rw [source_values_refine input lo hi inputBase outputBase hLength]
  rw [target_values_refine input lo hi inputBase outputBase chunks hLength hLegal]

open Neon2LeanDemo.S8VClamp in
/-- Both generated IR programs produce the same final memory and exact effect summary. -/
theorem generated_memory_execution_equal (args : KernelArgs) (before : ByteMemory)
    (chunks : List Nat) (hLegal : PositivePartition 16 chunks) :
    executeMemory registry sourceControl sourceIR args before [] =
      executeMemory registry targetControl targetIR args before chunks := by
  cases hLo : args.scalar? "lo" with
  | none => simp [executeMemory, sourceControl, targetControl, ControlMode.totalBytes, hLo]
  | some lo =>
      cases hHi : args.scalar? "hi" with
      | none =>
          simp [executeMemory, sourceControl, targetControl, ControlMode.totalBytes, hLo, hHi]
      | some hi =>
          cases hRead : before.readBytes args.inputBase 16 with
          | none =>
              simp [executeMemory, sourceControl, targetControl, ControlMode.totalBytes,
                hLo, hHi, hRead]
          | some input =>
              have hLength : input.length = 16 := ByteMemory.readBytes_length hRead
              have hSource :
                  executeValues registry (.fixed 16) sourceIR args.inputBase args.outputBase
                      (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi) [] input =
                    some (input.map (signedClampS8 (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi))) := by
                simpa [sourceControl] using
                  source_values_refine input (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi)
                    args.inputBase args.outputBase hLength
              have hTarget :
                  executeValues registry (.positiveStripMine 16) targetIR args.inputBase
                      args.outputBase (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi) chunks input =
                    some (input.map (signedClampS8 (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi))) := by
                simpa [targetControl] using
                  target_values_refine input (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi)
                    args.inputBase args.outputBase chunks hLength hLegal
              unfold executeMemory
              simp only [sourceControl, targetControl, ControlMode.totalBytes]
              rw [hLo, hHi, hRead]
              simp [hSource, hTarget]

theorem source_result_length (args : KernelArgs) (before : ByteMemory)
    (result : KernelResult)
    (hRun : executeMemory registry sourceControl sourceIR args before [] = some result) :
    result.output.length = 16 := by
  cases hLo : args.scalar? "lo" with
  | none => simp [executeMemory, sourceControl, ControlMode.totalBytes, hLo] at hRun
  | some lo =>
      cases hHi : args.scalar? "hi" with
      | none => simp [executeMemory, sourceControl, ControlMode.totalBytes, hLo, hHi] at hRun
      | some hi =>
          cases hRead : before.readBytes args.inputBase 16 with
          | none =>
              simp [executeMemory, sourceControl, ControlMode.totalBytes, hLo, hHi, hRead] at hRun
          | some input =>
              have hLength : input.length = 16 := ByteMemory.readBytes_length hRead
              have hValues := source_values_refine input (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi)
                args.inputBase args.outputBase hLength
              have hValuesFixed :
                  executeValues registry (.fixed 16) sourceIR args.inputBase args.outputBase
                      (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi) [] input =
                    some (input.map (signedClampS8 (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi))) := by
                simpa [sourceControl] using hValues
              cases hWrite : before.writeBytes args.outputBase
                  (input.map (signedClampS8 (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi))) with
              | none =>
                  unfold executeMemory at hRun
                  simp only [sourceControl, ControlMode.totalBytes] at hRun
                  rw [hLo, hHi, hRead] at hRun
                  simp [hValuesFixed, hWrite] at hRun
              | some after =>
                  unfold executeMemory at hRun
                  simp only [sourceControl, ControlMode.totalBytes] at hRun
                  rw [hLo, hHi, hRead] at hRun
                  simp [hValuesFixed, hWrite] at hRun
                  cases hRun
                  simpa using hLength

open Neon2LeanDemo.S8VClamp in
/--
Final-state equivalence, frame, and exact write-address summary for the two generated
IR programs. This theorem still relies on the documented Clang/intrinsic adequacy bridge.
-/
theorem generated_end_to_end (args : KernelArgs) (before : ByteMemory)
    (chunks : List Nat) (sourceResult targetResult : KernelResult)
    (hLegal : PositivePartition 16 chunks)
    (hSource : executeMemory registry sourceControl sourceIR args before [] = some sourceResult)
    (hTarget : executeMemory registry targetControl targetIR args before chunks =
      some targetResult) :
    Observe.equivalent observe args
        { memory := sourceResult.memory, arch := () }
        { memory := targetResult.memory, arch := () } ∧
      before.frameOutside sourceResult.memory { base := args.outputBase, length := 16 } ∧
      before.frameOutside targetResult.memory { base := args.outputBase, length := 16 } ∧
      sourceResult.effects.writeAddresses = contiguousAddresses args.outputBase 16 ∧
      targetResult.effects.writeAddresses = contiguousAddresses args.outputBase 16 := by
  have hExecutions := generated_memory_execution_equal args before chunks hLegal
  rw [hSource, hTarget] at hExecutions
  have hResults : sourceResult = targetResult := Option.some.inj hExecutions
  subst targetResult
  have hLength := source_result_length args before sourceResult hSource
  have hSourceFrame := executeMemory_frame hSource
  have hTargetFrame := executeMemory_frame hTarget
  have hSourceEffects := executeMemory_effects hSource
  have hTargetEffects := executeMemory_effects hTarget
  constructor
  · exact ⟨rfl, trivial⟩
  constructor
  · simpa [hLength] using hSourceFrame
  constructor
  · simpa [hLength] using hTargetFrame
  constructor
  · simpa [hLength] using hSourceEffects
  · simpa [hLength] using hTargetEffects

open Neon2LeanDemo.S8VClamp in
/-- The fixed contract is strong enough for both generated programs to execute successfully. -/
theorem generated_success_under_contract (args : KernelArgs) (before : ByteMemory)
    (chunks : List Nat) (hContract : contract.holds args before)
    (hLegal : PositivePartition 16 chunks) :
    ∃ sourceResult targetResult,
      executeMemory registry sourceControl sourceIR args before [] = some sourceResult ∧
      executeMemory registry targetControl targetIR args before chunks = some targetResult ∧
      Observe.equivalent observe args
          { memory := sourceResult.memory, arch := () }
          { memory := targetResult.memory, arch := () } ∧
        before.frameOutside sourceResult.memory { base := args.outputBase, length := 16 } ∧
        before.frameOutside targetResult.memory { base := args.outputBase, length := 16 } ∧
        sourceResult.effects.writeAddresses = contiguousAddresses args.outputBase 16 ∧
        targetResult.effects.writeAddresses = contiguousAddresses args.outputBase 16 := by
  rcases hContract with ⟨hParameters, hReadable, hWritable, _hAlias⟩
  rcases hParameters with
    ⟨_hBatch, lo, hi, hLo, hHi, _hLoRange, _hOrdered, _hHiRange⟩
  change before.canReadRange args.inputBase 16 = true at hReadable
  change before.canWriteRange args.outputBase 16 = true at hWritable
  let input : List S8Byte :=
    List.ofFn fun offset : Fin 16 => before.bytes (args.inputBase + offset.val)
  have hRead : before.readBytes args.inputBase 16 = some input := by
    simp [ByteMemory.readBytes, hReadable, input]
  have hInputLength : input.length = 16 := by simp [input]
  let output := input.map (signedClampS8 (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi))
  have hOutputLength : output.length = 16 := by simp [output, hInputLength]
  have hSourceValues :
      executeValues registry sourceControl sourceIR args.inputBase args.outputBase
          (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi) [] input = some output := by
    simpa [output] using source_values_refine input (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi)
      args.inputBase args.outputBase hInputLength
  have hTargetValues :
      executeValues registry targetControl targetIR args.inputBase args.outputBase
          (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi) chunks input = some output := by
    simpa [output] using target_values_refine input (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi)
      args.inputBase args.outputBase chunks hInputLength hLegal
  have hSourceValuesFixed :
      executeValues registry (.fixed 16) sourceIR args.inputBase args.outputBase
          (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi) [] input = some output := by
    simpa [sourceControl] using hSourceValues
  have hTargetValuesFixed :
      executeValues registry (.positiveStripMine 16) targetIR args.inputBase args.outputBase
          (BitVec.ofInt 8 lo) (BitVec.ofInt 8 hi) chunks input = some output := by
    simpa [targetControl] using hTargetValues
  cases hWrite : before.writeBytes args.outputBase output with
  | none =>
      unfold ByteMemory.writeBytes at hWrite
      simp [hOutputLength, hWritable] at hWrite
  | some after =>
      let result : KernelResult :=
        { memory := after
          output := output
          effects := { writeAddresses := contiguousAddresses args.outputBase output.length } }
      have hSourceRun :
          executeMemory registry sourceControl sourceIR args before [] = some result := by
        unfold executeMemory
        rw [hLo, hHi]
        simp only [sourceControl, ControlMode.totalBytes]
        rw [hRead]
        simp [hSourceValuesFixed, hWrite, result]
      have hTargetRun :
          executeMemory registry targetControl targetIR args before chunks = some result := by
        unfold executeMemory
        rw [hLo, hHi]
        simp only [targetControl, ControlMode.totalBytes]
        rw [hRead]
        simp [hTargetValuesFixed, hWrite, result]
      refine ⟨result, result, hSourceRun, hTargetRun, ?_⟩
      exact generated_end_to_end args before chunks result result hLegal hSourceRun hTargetRun

end Neon2LeanDemo.S8Clamp16
