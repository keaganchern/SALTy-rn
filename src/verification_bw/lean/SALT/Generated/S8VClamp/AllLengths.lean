/-
  Reviewed arbitrary-length value model for s8-vclamp.

  This module connects the generated Neon 64-lane block and RVV active-chunk
  models to unbounded list schedules. The Neon 8-lane and partial-tail path is
  represented only by its reviewed observable lane values. It does not establish
  a C-memory bridge for the tail's out-of-bounds load, endian-sensitive lane
  stores, pointer updates, or either source loop.
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

/-- The min-then-max order used by the Neon 8-lane and partial-tail paths. -/
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

/-- Reviewed output-lane semantics of the Neon 8-lane and partial-tail pipeline.

This deliberately omits the memory mechanism used to expose only the live prefix.
-/
def reviewedNeonTailValues (p : S8ClampParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let maximum := List.replicate input.length (p.max.truncate 8)
  let minimum := List.replicate input.length (p.min.truncate 8)
  SALT.Intrinsics.Neon.vmax_s8_vec
    (SALT.Intrinsics.Neon.vmin_s8_vec input maximum) minimum

theorem reviewedNeonTailValues_eq_tailMap (p : S8ClampParams)
    (input : List (BitVec 8)) :
    reviewedNeonTailValues p input = input.map (neonTailValue p) := by
  simp [reviewedNeonTailValues, neonTailValue, SALT.Intrinsics.Neon.vmin_s8_vec,
    SALT.Intrinsics.Neon.vmax_s8_vec, SALT.zipWith_replicate_right,
    List.map_map, Function.comp_def]

theorem reviewedNeonTailValues_eq_map (p : S8ClampParams)
    (hBounds : (p.min.truncate 8).toInt <= (p.max.truncate 8).toInt)
    (input : List (BitVec 8)) :
    reviewedNeonTailValues p input = input.map (clampValue p) := by
  rw [reviewedNeonTailValues_eq_tailMap]
  apply List.map_congr_left
  intro x _
  unfold neonTailValue clampValue
  exact min_then_max_eq_max_then_min x _ _ hBounds

/-- Value-level Neon schedule: 64-lane main blocks, then 8-lane blocks and a tail. -/
def reviewedNeonValueLoop (p : S8ClampParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  if input.length >= 64 then
    neonBlock64FromIntrinsics p (input.take 64) ++
      reviewedNeonValueLoop p (input.drop 64)
  else if input.length >= 8 then
    reviewedNeonTailValues p (input.take 8) ++
      reviewedNeonValueLoop p (input.drop 8)
  else
    reviewedNeonTailValues p input
termination_by input.length
decreasing_by all_goals simp_all [List.length_drop]; omega

theorem reviewedNeonValueLoop_eq_map (p : S8ClampParams)
    (hBounds : (p.min.truncate 8).toInt <= (p.max.truncate 8).toInt)
    (input : List (BitVec 8)) :
    reviewedNeonValueLoop p input = input.map (clampValue p) := by
  suffices forall n (xs : List (BitVec 8)), xs.length <= n ->
      reviewedNeonValueLoop p xs = xs.map (clampValue p) from
    this input.length input (by omega)
  intro n
  induction n with
  | zero =>
      intro xs hLength
      have : xs = [] := by cases xs <;> simp_all
      subst xs
      simp [reviewedNeonValueLoop, reviewedNeonTailValues,
        SALT.Intrinsics.Neon.vmin_s8_vec, SALT.Intrinsics.Neon.vmax_s8_vec]
  | succ n ih =>
      intro xs hLength
      unfold reviewedNeonValueLoop
      split
      · have hTake : (xs.take 64).length = 64 := by
          simp [List.length_take]
          omega
        rw [neonBlock64FromIntrinsics_eq_map p _ hTake]
        rw [ih _ (by simp [List.length_drop]; omega)]
        rw [<- List.map_append, List.take_append_drop]
      · split
        · rw [reviewedNeonTailValues_eq_map p hBounds]
          rw [ih _ (by simp [List.length_drop]; omega)]
          rw [<- List.map_append, List.take_append_drop]
        · exact reviewedNeonTailValues_eq_map p hBounds xs

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

The ordered-bounds hypothesis is necessary because the Neon tail reverses the
main path's min/max instruction order. This theorem is not a C-memory or ISA
correspondence result.
-/
theorem allLengthsValueEqual (p : S8ClampParams)
    (hBounds : SALT.Kernel.S8VClamp.WellFormedParams p)
    (input : List (BitVec 8))
    (schedule : PositivePartition input.length) :
    reviewedNeonValueLoop p input = reviewedRVVValueLoop p input schedule := by
  change (p.min.truncate 8).toInt <= (p.max.truncate 8).toInt at hBounds
  rw [reviewedNeonValueLoop_eq_map p hBounds, reviewedRVVValueLoop_eq_map]

end SALT.Generated.S8VClamp
