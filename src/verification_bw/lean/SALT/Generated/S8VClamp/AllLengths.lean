/-
  Arbitrary-length value proof for the generated s8-vclamp models.

  The frontend validates and consumes all 36 source Neon calls. The generated
  tail model interprets the 4/2/1 lane stores as a little-endian live-prefix
  value plan. This remains a value abstraction: it does not establish C memory,
  alignment, aliasing, overread validity, host endianness, or ISA execution.
-/
import SALT.Generated.S8VClamp.Proof
import SALT.Kernel.Schedule
import SALT.Kernel.S8VClamp.Contract

namespace SALT.Generated.S8VClamp

open SALT
open SALT.Kernel.Schedule

/-- The max-then-min lane function used by the generated main-block and RVV models. -/
def clampValue (p : S8ClampParams) (x : BitVec 8) : BitVec 8 :=
  bvSignedMin (bvSignedMax x (p.min.truncate 8)) (p.max.truncate 8)

/-- The min-then-max order used by the generated Neon 8-lane and partial-tail models. -/
def neonTailValue (p : S8ClampParams) (x : BitVec 8) : BitVec 8 :=
  bvSignedMax (bvSignedMin x (p.max.truncate 8)) (p.min.truncate 8)

private theorem min_then_max_eq_max_then_min {n : Nat} (x lo hi : BitVec n)
    (hBounds : lo.toInt <= hi.toInt) :
    bvSignedMax (bvSignedMin x hi) lo = bvSignedMin (bvSignedMax x lo) hi := by
  unfold bvSignedMin bvSignedMax
  split <;> split <;> simp_all <;> omega

theorem rvvChunkFromIntrinsics_eq_map (p : S8ClampParams)
    (input : List (BitVec 8)) :
    rvvChunkFromIntrinsics p input = input.map (clampValue p) := by
  simp [rvvChunkFromIntrinsics, clampValue, SALT.Intrinsics.RVV.vmax_vx,
    SALT.Intrinsics.RVV.vmin_vx, List.map_map, Function.comp_def]

theorem neonBlock64FromIntrinsics_eq_map (p : S8ClampParams)
    (input : List (BitVec 8)) (hLength : input.length = 64) :
    neonBlock64FromIntrinsics p input = input.map (clampValue p) := by
  rw [generated_block_equal p input hLength, rvvChunkFromIntrinsics_eq_map]

theorem neonBlock8FromIntrinsics_eq_tailMap (p : S8ClampParams)
    (input : List (BitVec 8)) (hLength : input.length = 8) :
    neonBlock8FromIntrinsics p input = input.map (neonTailValue p) := by
  have hTake : input.take 8 = input := by
    simpa only [hLength] using (List.take_length (l := input))
  simp only [neonBlock8FromIntrinsics, SALT.Intrinsics.Neon.vmin_s8_vec,
    SALT.Intrinsics.Neon.vmax_s8_vec]
  rw [hTake]
  simp only [List.take_replicate]
  rw [show min 8 16 = 8 by decide]
  rw [SALT.zipWith_replicate_right SALT.bvSignedMin
    (p.max.truncate 8) input 8 (by omega)]
  rw [SALT.zipWith_replicate_right SALT.bvSignedMax
    (p.min.truncate 8)
    (input.map (fun x => SALT.bvSignedMin x (p.max.truncate 8))) 8
    (by simp [hLength])]
  simp only [List.map_map, Function.comp_def]
  rfl

theorem neonBlock8FromIntrinsics_eq_map (p : S8ClampParams)
    (hBounds : (p.min.truncate 8).toInt <= (p.max.truncate 8).toInt)
    (input : List (BitVec 8)) (hLength : input.length = 8) :
    neonBlock8FromIntrinsics p input = input.map (clampValue p) := by
  rw [neonBlock8FromIntrinsics_eq_tailMap p input hLength]
  apply List.map_congr_left
  intro x _
  unfold neonTailValue clampValue
  exact min_then_max_eq_max_then_min x _ _ hBounds

private def littleEndianPrefixStorePlan (values : List (BitVec 8))
    (live : Nat) : List (BitVec 8) :=
  let stored4 := if live.testBit 2 then values.take 4 else []
  let shifted4 := ((values ++ values).drop 4).take 8
  let after4 := if live.testBit 2 then shifted4 else values
  let stored2 := if live.testBit 1 then after4.take 2 else []
  let shifted2 := ((after4 ++ after4).drop 2).take 8
  let after2 := if live.testBit 1 then shifted2 else after4
  let stored1 := if live.testBit 0 then after2.take 1 else []
  stored4 ++ stored2 ++ stored1

private theorem littleEndianPrefixStorePlan_eq_take (values : List (BitVec 8))
    (hLength : values.length = 8) (live : Nat) (hLive : live < 8) :
    littleEndianPrefixStorePlan values live = values.take live := by
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
    subst live <;> simp [littleEndianPrefixStorePlan, Nat.testBit]

theorem neonPartialTailLivePrefixFromIntrinsics_eq_take_tailMap
    (p : S8ClampParams) (loaded : List (BitVec 8)) (hLength : loaded.length = 8)
    (live : Nat) (hLive : live < 8) :
    neonPartialTailLivePrefixFromIntrinsics p loaded live =
      (loaded.map (neonTailValue p)).take live := by
  change littleEndianPrefixStorePlan (neonBlock8FromIntrinsics p loaded) live = _
  rw [littleEndianPrefixStorePlan_eq_take _ (by simp [
    neonBlock8FromIntrinsics_eq_tailMap, hLength]) _ hLive]
  rw [neonBlock8FromIntrinsics_eq_tailMap p loaded hLength]

theorem neonPartialTailFromInput_eq_map (p : S8ClampParams)
    (hBounds : (p.min.truncate 8).toInt <= (p.max.truncate 8).toInt)
    (input : List (BitVec 8)) (hLength : input.length < 8) :
    let loaded := input ++ List.replicate (8 - input.length) (0 : BitVec 8)
    neonPartialTailLivePrefixFromIntrinsics p loaded input.length =
      input.map (clampValue p) := by
  dsimp only
  let loaded := input ++ List.replicate (8 - input.length) (0 : BitVec 8)
  have hLoaded : loaded.length = 8 := by simp [loaded]; omega
  rw [neonPartialTailLivePrefixFromIntrinsics_eq_take_tailMap
    p loaded hLoaded input.length hLength]
  have hPrefix : (loaded.map (neonTailValue p)).take input.length =
      input.map (neonTailValue p) := by
    simp [loaded]
  rw [hPrefix]
  apply List.map_congr_left
  intro x _
  unfold neonTailValue clampValue
  exact min_then_max_eq_max_then_min x _ _ hBounds

theorem neonValueLoopFromIntrinsics_eq_map (p : S8ClampParams)
    (hBounds : (p.min.truncate 8).toInt <= (p.max.truncate 8).toInt)
    (input : List (BitVec 8)) :
    neonValueLoopFromIntrinsics p input = input.map (clampValue p) := by
  suffices forall n (xs : List (BitVec 8)), xs.length <= n ->
      neonValueLoopFromIntrinsics p xs = xs.map (clampValue p) from
    this input.length input (by omega)
  intro n
  induction n with
  | zero =>
      intro xs hLength
      have : xs = [] := by cases xs <;> simp_all
      subst xs
      simpa [neonValueLoopFromIntrinsics] using
        neonPartialTailFromInput_eq_map p hBounds [] (by decide)
  | succ n ih =>
      intro xs hLength
      unfold neonValueLoopFromIntrinsics
      split
      · have hTake : (xs.take 64).length = 64 := by
          simp [List.length_take]
          omega
        rw [neonBlock64FromIntrinsics_eq_map p _ hTake]
        rw [ih _ (by simp [List.length_drop]; omega)]
        rw [<- List.map_append, List.take_append_drop]
      · split
        · have hTake : (xs.take 8).length = 8 := by
            simp [List.length_take]
            omega
          rw [neonBlock8FromIntrinsics_eq_map p hBounds _ hTake]
          rw [ih _ (by simp [List.length_drop]; omega)]
          rw [<- List.map_append, List.take_append_drop]
        · exact neonPartialTailFromInput_eq_map p hBounds xs (by omega)

private def processBlockSizes {alpha beta : Type}
    (block : List alpha -> List beta) : List Nat -> List alpha -> List beta
  | [], _ => []
  | chunk :: chunks, input =>
      block (input.take chunk) ++ processBlockSizes block chunks (input.drop chunk)

private theorem processBlockSizes_eq_map {alpha beta : Type}
    (block : List alpha -> List beta) (f : alpha -> beta)
    (hBlock : forall xs, block xs = xs.map f)
    (chunks : List Nat) (input : List alpha)
    (coverage : chunks.sum = input.length) :
    processBlockSizes block chunks input = input.map f := by
  induction chunks generalizing input with
  | nil => cases input <;> simp_all [processBlockSizes]
  | cons chunk chunks ih =>
      simp only [processBlockSizes]
      rw [hBlock, ih (input.drop chunk) (by simp [List.length_drop, <- coverage])]
      rw [<- List.map_append, List.take_append_drop]

/-- Apply the generated RVV chunk model according to an arbitrary complete schedule. -/
def reviewedRVVValueLoop (p : S8ClampParams) (input : List (BitVec 8))
    (schedule : PositivePartition input.length) : List (BitVec 8) :=
  processBlockSizes (rvvChunkFromIntrinsics p) schedule.chunks input

theorem reviewedRVVValueLoop_eq_map (p : S8ClampParams)
    (input : List (BitVec 8)) (schedule : PositivePartition input.length) :
    reviewedRVVValueLoop p input schedule = input.map (clampValue p) :=
  processBlockSizes_eq_map _ _ (rvvChunkFromIntrinsics_eq_map p)
    schedule.chunks input schedule.total

/-- Arbitrary-length value equality for every complete positive RVV partition.

The ordered-bounds hypothesis is necessary because the generated Neon tail reverses
the main path's min/max instruction order. This theorem is not a C-memory or ISA
correspondence result.
-/
theorem allLengthsValueEqual (p : S8ClampParams)
    (hBounds : SALT.Kernel.S8VClamp.WellFormedParams p)
    (input : List (BitVec 8))
    (schedule : PositivePartition input.length) :
    neonValueLoopFromIntrinsics p input = reviewedRVVValueLoop p input schedule := by
  change (p.min.truncate 8).toInt <= (p.max.truncate 8).toInt at hBounds
  rw [neonValueLoopFromIntrinsics_eq_map p hBounds, reviewedRVVValueLoop_eq_map]

end SALT.Generated.S8VClamp
