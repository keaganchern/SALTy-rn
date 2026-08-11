import SALT.Kernel.Schedule

namespace SALT.Kernel.ScheduleTest

open SALT.Kernel.Schedule

def fiveElements : PositivePartition 5 where
  chunks := [2, 2, 1]
  positive := by simp
  total := by simp

example : processChunks (fun n : Nat => n + 1) [0, 1, 2, 3, 4] fiveElements =
    [1, 2, 3, 4, 5] := by
  rfl

def fixedTwoWithTail : FixedChunkTail 5 2 where
  partition := fiveElements
  chunkPositive := by simp
  fullChunkCount := 2
  tailSize := 1
  tailBound := by simp
  shape := by rfl

example : processFixedChunkTail (fun n : Nat => n + 1) [0, 1, 2, 3, 4]
    fixedTwoWithTail = [1, 2, 3, 4, 5] := by
  rfl

example {α β : Type} (f : α -> β) (input : List α)
    (schedule : PositivePartition input.length) :
    processChunks f input schedule = input.map f :=
  processChunks_eq_map f input schedule

example : processChunks2 (fun a b : Nat => a + b) [0, 1, 2, 3, 4] [5, 6, 7, 8, 9]
    (by rfl) fiveElements = [5, 7, 9, 11, 13] := by
  rfl

example {α β γ : Type} (f : α -> β -> γ) (inputA : List α) (inputB : List β)
    (sameLength : inputA.length = inputB.length)
    (schedule : PositivePartition inputA.length) :
    processChunks2 f inputA inputB sameLength schedule = List.zipWith f inputA inputB :=
  processChunks2_eq_zipWith f inputA inputB sameLength schedule

end SALT.Kernel.ScheduleTest
