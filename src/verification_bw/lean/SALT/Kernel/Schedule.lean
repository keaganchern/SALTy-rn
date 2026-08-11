import Std

namespace SALT.Kernel.Schedule

universe u v w

/-- A complete partition of `n` elements into strictly positive chunk sizes. -/
structure PositivePartition (n : Nat) where
  chunks : List Nat
  positive : forall chunk, chunk ∈ chunks -> 0 < chunk
  total : chunks.sum = n

namespace PositivePartition

def empty : PositivePartition 0 where
  chunks := []
  positive := by simp
  total := by simp

def singleton (n : Nat) (positive : 0 < n) : PositivePartition n where
  chunks := [n]
  positive := by simpa
  total := by simp

end PositivePartition

/-- Execute one element-wise function according to a list of chunk sizes. -/
def processChunkSizes {α : Type u} {β : Type v} (f : α -> β) : List Nat -> List α -> List β
  | [], _ => []
  | chunk :: chunks, input =>
      (input.take chunk).map f ++ processChunkSizes f chunks (input.drop chunk)

theorem processChunkSizes_eq_map {α : Type u} {β : Type v} (f : α -> β)
    (chunks : List Nat) (input : List α)
    (coverage : chunks.sum = input.length) :
    processChunkSizes f chunks input = input.map f := by
  induction chunks generalizing input with
  | nil =>
      cases input with
      | nil => rfl
      | cons head tail => simp at coverage
  | cons chunk chunks ih =>
      have dropCoverage : chunks.sum = (input.drop chunk).length := by
        simp [List.length_drop, ← coverage]
      simp only [processChunkSizes]
      rw [ih (input.drop chunk) dropCoverage]
      rw [← List.map_append, List.take_append_drop]

/-- Process an input according to a complete positive partition of its length. -/
def processChunks {α : Type u} {β : Type v} (f : α -> β) (input : List α)
    (schedule : PositivePartition input.length) : List β :=
  processChunkSizes f schedule.chunks input

theorem processChunks_eq_map {α : Type u} {β : Type v} (f : α -> β) (input : List α)
    (schedule : PositivePartition input.length) :
    processChunks f input schedule = input.map f :=
  processChunkSizes_eq_map f schedule.chunks input schedule.total

/-- Execute one binary element-wise function according to a list of chunk sizes. -/
def processChunkSizes2 {α : Type u} {β : Type v} {γ : Type w} (f : α -> β -> γ)
    (chunks : List Nat) (inputA : List α) (inputB : List β) : List γ :=
  processChunkSizes (fun input => f input.1 input.2) chunks (List.zip inputA inputB)

theorem map_zip_eq_zipWith {α : Type u} {β : Type v} {γ : Type w} (f : α -> β -> γ)
    (inputA : List α) (inputB : List β) :
    (List.zip inputA inputB).map (fun input => f input.1 input.2) =
      List.zipWith f inputA inputB := by
  induction inputA generalizing inputB with
  | nil => simp
  | cons headA tailA ih =>
      cases inputB with
      | nil => simp
      | cons headB tailB => simp [ih]

theorem processChunkSizes2_eq_zipWith {α : Type u} {β : Type v} {γ : Type w}
    (f : α -> β -> γ) (chunks : List Nat) (inputA : List α) (inputB : List β)
    (sameLength : inputA.length = inputB.length)
    (coverage : chunks.sum = inputA.length) :
    processChunkSizes2 f chunks inputA inputB = List.zipWith f inputA inputB := by
  have zipCoverage : chunks.sum = (List.zip inputA inputB).length := by
    calc
      chunks.sum = inputA.length := coverage
      _ = (List.zip inputA inputB).length := by simp [sameLength]
  unfold processChunkSizes2
  rw [processChunkSizes_eq_map _ _ _ zipCoverage]
  exact map_zip_eq_zipWith f inputA inputB

/-- Process two equal-length inputs according to a complete positive partition. -/
def processChunks2 {α : Type u} {β : Type v} {γ : Type w} (f : α -> β -> γ)
    (inputA : List α) (inputB : List β) (_sameLength : inputA.length = inputB.length)
    (schedule : PositivePartition inputA.length) : List γ :=
  processChunkSizes2 f schedule.chunks inputA inputB

theorem processChunks2_eq_zipWith {α : Type u} {β : Type v} {γ : Type w}
    (f : α -> β -> γ) (inputA : List α) (inputB : List β)
    (sameLength : inputA.length = inputB.length)
    (schedule : PositivePartition inputA.length) :
    processChunks2 f inputA inputB sameLength schedule = List.zipWith f inputA inputB :=
  processChunkSizes2_eq_zipWith f schedule.chunks inputA inputB sameLength schedule.total

/-- A positive partition whose full chunks have one fixed width and whose final
    optional tail is no wider than that width. -/
structure FixedChunkTail (n chunkSize : Nat) where
  partition : PositivePartition n
  chunkPositive : 0 < chunkSize
  fullChunkCount : Nat
  tailSize : Nat
  tailBound : tailSize <= chunkSize
  shape :
    partition.chunks =
      List.replicate fullChunkCount chunkSize ++ (if tailSize = 0 then [] else [tailSize])

def processFixedChunkTail {α : Type u} {β : Type v} {chunkSize : Nat}
    (f : α -> β) (input : List α)
    (schedule : FixedChunkTail input.length chunkSize) : List β :=
  processChunks f input schedule.partition

theorem processFixedChunkTail_eq_map {α : Type u} {β : Type v} {chunkSize : Nat}
    (f : α -> β) (input : List α)
    (schedule : FixedChunkTail input.length chunkSize) :
    processFixedChunkTail f input schedule = input.map f :=
  processChunks_eq_map f input schedule.partition

/-- One fixed-width body step followed by its remaining tail preserves `map`. -/
theorem process_one_chunk_then_tail_eq_map {α : Type u} {β : Type v}
    (f : α -> β) (input : List α)
    (chunkSize : Nat) :
    (input.take chunkSize).map f ++ (input.drop chunkSize).map f = input.map f := by
  rw [← List.map_append, List.take_append_drop]

end SALT.Kernel.Schedule
