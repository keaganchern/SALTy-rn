/-
  Arbitrary-length value proof for the generated s8-vclamp models.

  The frontend validates and consumes all 36 source Neon calls. The generated
  tail model interprets the 4/2/1 lane stores as a little-endian live-prefix
  value plan. Its stronger theorem accepts arbitrary bytes beyond a short tail
  and proves their contents irrelevant to the live output. This remains a value
  abstraction: it does not establish C memory, alignment, aliasing, overread
  validity, host endianness, or ISA execution.
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

theorem neonPartialTailLivePrefixFromIntrinsics_eq_take_tailMap
    (p : S8ClampParams) (loaded : List (BitVec 8)) (hLength : loaded.length = 8)
    (live : Nat) (hLive : live < 8) :
    neonPartialTailLivePrefixFromIntrinsics p loaded live =
      (loaded.map (neonTailValue p)).take live := by
  change littleEndianPrefixStore8 (neonBlock8FromIntrinsics p loaded) live = _
  rw [littleEndianPrefixStore8_eq_take _ (by simp [
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

theorem neonPartialTailWithOverread_eq_map (p : S8ClampParams)
    (hBounds : (p.min.truncate 8).toInt <= (p.max.truncate 8).toInt)
    (input overread : List (BitVec 8)) (hLength : input.length < 8)
    (hOverread : 8 - input.length <= overread.length) :
    let loaded := (input ++ overread).take 8
    neonPartialTailLivePrefixFromIntrinsics p loaded input.length =
      input.map (clampValue p) := by
  dsimp only
  let loaded := (input ++ overread).take 8
  have hLoaded : loaded.length = 8 := by
    simp [loaded, List.length_take]
    omega
  rw [neonPartialTailLivePrefixFromIntrinsics_eq_take_tailMap
    p loaded hLoaded input.length hLength]
  have hLoadedPrefix : loaded.take input.length = input := by
    simp only [loaded, List.take_take]
    rw [show min input.length 8 = input.length by omega]
    simp
  have hPrefix : (loaded.map (neonTailValue p)).take input.length =
      input.map (neonTailValue p) := by
    rw [<- List.map_take, hLoadedPrefix]
  rw [hPrefix]
  apply List.map_congr_left
  intro x _
  unfold neonTailValue clampValue
  exact min_then_max_eq_max_then_min x _ _ hBounds

theorem neonValueLoopWithOverreadFromIntrinsics_eq_map (p : S8ClampParams)
    (hBounds : (p.min.truncate 8).toInt <= (p.max.truncate 8).toInt)
    (input overread : List (BitVec 8)) (hOverread : 7 <= overread.length) :
    neonValueLoopWithOverreadFromIntrinsics p input overread =
      input.map (clampValue p) := by
  unfold neonValueLoopWithOverreadFromIntrinsics
  apply runFixedChunkTail_eq_map 64 (by decide)
      (neonBlock64FromIntrinsics p) _ (clampValue p)
  · exact neonBlock64FromIntrinsics_eq_map p
  · intro after64 _ _
    apply runFixedChunkTail_eq_map 8 (by decide)
        (neonBlock8FromIntrinsics p) _ (clampValue p)
    · exact neonBlock8FromIntrinsics_eq_map p hBounds
    · intro tail _ hTail
      exact neonPartialTailWithOverread_eq_map p hBounds tail overread hTail (by omega)

theorem neonValueLoopFromIntrinsics_eq_map (p : S8ClampParams)
    (hBounds : (p.min.truncate 8).toInt <= (p.max.truncate 8).toInt)
    (input : List (BitVec 8)) :
    neonValueLoopFromIntrinsics p input = input.map (clampValue p) := by
  unfold neonValueLoopFromIntrinsics
  exact neonValueLoopWithOverreadFromIntrinsics_eq_map p hBounds input _ (by simp)

theorem neonValueLoopWithOverread_irrelevant (p : S8ClampParams)
    (hBounds : (p.min.truncate 8).toInt <= (p.max.truncate 8).toInt)
    (input overreadA overreadB : List (BitVec 8))
    (hOverreadA : 7 <= overreadA.length) (hOverreadB : 7 <= overreadB.length) :
    neonValueLoopWithOverreadFromIntrinsics p input overreadA =
      neonValueLoopWithOverreadFromIntrinsics p input overreadB := by
  rw [neonValueLoopWithOverreadFromIntrinsics_eq_map p hBounds input overreadA
    hOverreadA]
  rw [neonValueLoopWithOverreadFromIntrinsics_eq_map p hBounds input overreadB
    hOverreadB]

/-- Apply the generated RVV chunk model according to an arbitrary complete schedule. -/
def reviewedRVVValueLoop (p : S8ClampParams) (input : List (BitVec 8))
    (schedule : PositivePartition input.length) : List (BitVec 8) :=
  processBlocks (rvvChunkFromIntrinsics p) input schedule

theorem reviewedRVVValueLoop_eq_map (p : S8ClampParams)
    (input : List (BitVec 8)) (schedule : PositivePartition input.length) :
    reviewedRVVValueLoop p input schedule = input.map (clampValue p) :=
  processBlocks_eq_map _ _ (rvvChunkFromIntrinsics_eq_map p) input schedule

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

/-- Arbitrary-length value equality with explicit, arbitrary Neon tail overread.

Seven supplied byte values suffice for every nonempty tail shorter than eight bytes.
The theorem proves content independence, not C-memory readability or ISA adequacy.
-/
theorem allLengthsValueEqualWithOverread (p : S8ClampParams)
    (hBounds : SALT.Kernel.S8VClamp.WellFormedParams p)
    (input overread : List (BitVec 8)) (hOverread : 7 <= overread.length)
    (schedule : PositivePartition input.length) :
    neonValueLoopWithOverreadFromIntrinsics p input overread =
      reviewedRVVValueLoop p input schedule := by
  change (p.min.truncate 8).toInt <= (p.max.truncate 8).toInt at hBounds
  rw [neonValueLoopWithOverreadFromIntrinsics_eq_map p hBounds input overread
    hOverread, reviewedRVVValueLoop_eq_map]

end SALT.Generated.S8VClamp
