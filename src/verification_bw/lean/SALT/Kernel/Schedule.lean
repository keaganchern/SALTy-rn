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

/-- Execute a generated block model according to explicit chunk sizes. Unlike
    `processChunkSizes`, `block` receives the whole active chunk. -/
def processBlockSizes {α : Type u} {β : Type v} (block : List α -> List β) :
    List Nat -> List α -> List β
  | [], _ => []
  | chunk :: chunks, input =>
      block (input.take chunk) ++ processBlockSizes block chunks (input.drop chunk)

theorem processBlockSizes_eq_map {α : Type u} {β : Type v}
    (block : List α -> List β) (f : α -> β)
    (blockRefines : forall input, block input = input.map f)
    (chunks : List Nat) (input : List α)
    (coverage : chunks.sum = input.length) :
    processBlockSizes block chunks input = input.map f := by
  induction chunks generalizing input with
  | nil =>
      cases input <;> simp_all [processBlockSizes]
  | cons chunk chunks ih =>
      simp only [processBlockSizes]
      rw [blockRefines]
      rw [ih (input.drop chunk) (by simp [List.length_drop, <- coverage])]
      rw [<- List.map_append, List.take_append_drop]

/-- Execute a generated block model according to a complete positive partition. -/
def processBlocks {α : Type u} {β : Type v} (block : List α -> List β)
    (input : List α) (schedule : PositivePartition input.length) : List β :=
  processBlockSizes block schedule.chunks input

theorem processBlocks_eq_map {α : Type u} {β : Type v}
    (block : List α -> List β) (f : α -> β)
    (blockRefines : forall input, block input = input.map f)
    (input : List α) (schedule : PositivePartition input.length) :
    processBlocks block input schedule = input.map f :=
  processBlockSizes_eq_map block f blockRefines schedule.chunks input schedule.total

/-- Execute fixed-width generated blocks, followed by a nonempty short-tail model.
    The empty input never invokes `tail`, matching a C `if (batch != 0)` guard. -/
def runFixedChunkTail {α : Type u} {β : Type v} (width : Nat)
    (widthPositive : 0 < width) (body tail : List α -> List β)
    (input : List α) : List β :=
  if input = [] then
    []
  else if width <= input.length then
    body (input.take width) ++
      runFixedChunkTail width widthPositive body tail (input.drop width)
  else
    tail input
termination_by input.length
decreasing_by
  simp only [List.length_drop]
  exact Nat.sub_lt_self widthPositive (by omega)

theorem runFixedChunkTail_eq_map {α : Type u} {β : Type v}
    (width : Nat) (widthPositive : 0 < width)
    (body tail : List α -> List β) (f : α -> β)
    (bodyRefines : forall input, input.length = width -> body input = input.map f)
    (tailRefines : forall input, 0 < input.length -> input.length < width ->
      tail input = input.map f)
    (input : List α) :
    runFixedChunkTail width widthPositive body tail input = input.map f := by
  suffices forall n (xs : List α), xs.length <= n ->
      runFixedChunkTail width widthPositive body tail xs = xs.map f from
    this input.length input (by omega)
  intro n
  induction n with
  | zero =>
      intro xs hLength
      have : xs = [] := by cases xs <;> simp_all
      subst xs
      simp [runFixedChunkTail]
  | succ n ih =>
      intro xs hLength
      unfold runFixedChunkTail
      split
      · simp_all
      · split
        · have hTake : (xs.take width).length = width := by
            simp [List.length_take]
            omega
          rw [bodyRefines _ hTake]
          rw [ih _ (by simp [List.length_drop]; omega)]
          rw [<- List.map_append, List.take_append_drop]
        · rw [tailRefines xs (by cases xs <;> simp_all) (by omega)]

/-- Combine a fixed-width Neon-style executor with an arbitrary RVV-style
    positive partition once both generated block models refine the same map. -/
theorem runFixedChunkTail_eq_processBlocks {α : Type u} {β : Type v}
    (width : Nat) (widthPositive : 0 < width)
    (body tail block : List α -> List β) (f : α -> β)
    (bodyRefines : forall input, input.length = width -> body input = input.map f)
    (tailRefines : forall input, 0 < input.length -> input.length < width ->
      tail input = input.map f)
    (blockRefines : forall input, block input = input.map f)
    (input : List α) (schedule : PositivePartition input.length) :
    runFixedChunkTail width widthPositive body tail input =
      processBlocks block input schedule := by
  rw [runFixedChunkTail_eq_map width widthPositive body tail f bodyRefines
    tailRefines input]
  rw [processBlocks_eq_map block f blockRefines input schedule]

/-- Value-level interpretation of the reviewed little-endian 4/2/1 lane-store
    sequence used by an eight-byte prefix tail. This is not a C-memory theorem. -/
def littleEndianPrefixStore8 {α : Type u} (values : List α) (live : Nat) : List α :=
  let stored4 := if live.testBit 2 then values.take 4 else []
  let shifted4 := ((values ++ values).drop 4).take 8
  let after4 := if live.testBit 2 then shifted4 else values
  let stored2 := if live.testBit 1 then after4.take 2 else []
  let shifted2 := ((after4 ++ after4).drop 2).take 8
  let after2 := if live.testBit 1 then shifted2 else after4
  let stored1 := if live.testBit 0 then after2.take 1 else []
  stored4 ++ stored2 ++ stored1

theorem littleEndianPrefixStore8_eq_take {α : Type u} (values : List α)
    (hLength : values.length = 8) (live : Nat) (hLive : live < 8) :
    littleEndianPrefixStore8 values live = values.take live := by
  rcases values with _ | ⟨x0, xs⟩
  · simp at hLength
  rcases xs with _ | ⟨x1, xs⟩
  · simp at hLength
  rcases xs with _ | ⟨x2, xs⟩
  · simp at hLength
  rcases xs with _ | ⟨x3, xs⟩
  · simp at hLength
  rcases xs with _ | ⟨x4, xs⟩
  · simp at hLength
  rcases xs with _ | ⟨x5, xs⟩
  · simp at hLength
  rcases xs with _ | ⟨x6, xs⟩
  · simp at hLength
  rcases xs with _ | ⟨x7, xs⟩
  · simp at hLength
  have hTail : xs = [] := by cases xs <;> simp_all
  subst xs
  have hCases : live = 0 ∨ live = 1 ∨ live = 2 ∨ live = 3 ∨
      live = 4 ∨ live = 5 ∨ live = 6 ∨ live = 7 := by omega
  rcases hCases with h | h | h | h | h | h | h | h <;>
    subst live <;> simp [littleEndianPrefixStore8, Nat.testBit]

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
