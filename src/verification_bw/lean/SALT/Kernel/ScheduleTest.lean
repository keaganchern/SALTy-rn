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

def addOneBlock (input : List Nat) : List Nat := input.map (fun n => n + 1)

example : processBlocks addOneBlock [0, 1, 2, 3, 4] fiveElements =
    [1, 2, 3, 4, 5] := by
  rfl

def addBlock2 (inputA inputB : List Nat) : List Nat :=
  List.zipWith (fun a b => a + b) inputA inputB

example : processBlocks2 addBlock2 [0, 1, 2, 3, 4] [5, 6, 7, 8, 9] (by rfl)
    fiveElements = [5, 7, 9, 11, 13] := by
  rfl

example {α β γ : Type} (f : α -> β -> γ) (block : List α -> List β -> List γ)
    (blockRefines : forall inputA inputB, inputA.length = inputB.length ->
      block inputA inputB = List.zipWith f inputA inputB)
    (inputA : List α) (inputB : List β) (sameLength : inputA.length = inputB.length)
    (schedule : PositivePartition inputA.length) :
    processBlocks2 block inputA inputB sameLength schedule = List.zipWith f inputA inputB :=
  processBlocks2_eq_zipWith block f blockRefines inputA inputB sameLength schedule

example : runFixedChunkTail 2 (by decide) addOneBlock addOneBlock [0, 1, 2, 3, 4] =
    [1, 2, 3, 4, 5] := by
  calc
    _ = [0, 1, 2, 3, 4].map (fun n => n + 1) :=
      runFixedChunkTail_eq_map 2 (by decide) addOneBlock addOneBlock
        (fun n => n + 1) (by intro input _; rfl) (by intro input _ _; rfl) _
    _ = _ := by rfl

example : runFixedChunkTail2 2 (by decide) addBlock2 addBlock2
    [0, 1, 2, 3, 4] [5, 6, 7, 8, 9] (by rfl) = [5, 7, 9, 11, 13] := by
  apply runFixedChunkTail2_eq_zipWith 2 (by decide) addBlock2 addBlock2
    (fun a b : Nat => a + b)
  · intro inputA inputB _ _
    rfl
  · intro inputA inputB _ _ _
    rfl

example : runFixedChunkTail2 2 (by decide) addBlock2 addBlock2
    [0, 1, 2, 3, 4] [5, 6, 7, 8, 9] (by rfl) =
      processBlocks2 addBlock2 [0, 1, 2, 3, 4] [5, 6, 7, 8, 9] (by rfl)
        fiveElements := by
  apply runFixedChunkTail2_eq_processBlocks2 2 (by decide) addBlock2 addBlock2 addBlock2
    (fun a b : Nat => a + b)
  · intro inputA inputB _ _
    rfl
  · intro inputA inputB _ _ _
    rfl
  · intro inputA inputB _
    rfl

example : littleEndianPrefixStore8 [0, 1, 2, 3, 4, 5, 6, 7] 7 =
    [0, 1, 2, 3, 4, 5, 6] := by
  rfl

end SALT.Kernel.ScheduleTest
