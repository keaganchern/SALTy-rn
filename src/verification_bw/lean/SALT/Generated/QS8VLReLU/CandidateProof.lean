import SALT.Generated.QS8VLReLU.Proof
import SALT.Generated.QS8VLReLU.Obligation

namespace SALT.Generated.QS8VLReLU

open SALT.Intrinsics
open SALT.Kernel.QS8VLReLU
open SALT.Kernel.Schedule

private def laneValue (p : QS8LReLUParams) (x : BitVec 8) : BitVec 8 :=
  let difference := p.input_zero_point.truncate 16 - SALT.sext x 16
  let positive := (-p.positive_multiplier).truncate 16
  let negative := (-p.negative_multiplier).truncate 16
  let multiplier := if difference.toInt < 0 then positive else negative
  let scaled := difference.shiftLeft 7
  let product := BitVec.ofInt 32 (scaled.toInt * multiplier.toInt)
  RVV.vnclipSigned 8 .rdn 0
    (SALT.signedSatAdd (RVV.vnclipSigned 16 .rnu 15 product)
      (p.output_zero_point.truncate 16))

private theorem rvvChunkFromIntrinsics_eq_map (p : QS8LReLUParams)
    (input : List (BitVec 8)) :
    rvvChunkFromIntrinsics p input = input.map (laneValue p) := by
  simp [rvvChunkFromIntrinsics, RVV.vsext_vf2_i16, RVV.vrsub_vx_i16,
    RVV.vmslt_vx_i16, RVV.vsll_vx_i16, RVV.vmerge_vxm_i16,
    RVV.vwmul_vv_i32, RVV.vnclip_wx_i16_mode, RVV.vsadd_vx,
    RVV.vnclip_wx_i8_mode, RVV.VXRoundingMode.decode, laneValue, SALT.sext,
    SALT.zipWith_replicate_left, List.map_map]

private theorem neonBlock8FromIntrinsics_eq_map (p : QS8LReLUParams)
    (input : List (BitVec 8)) (hLength : input.length = 8) :
    neonBlock8FromIntrinsics p input = input.map (laneValue p) := by
  rw [generated_block_equal_unconditional p input hLength]
  exact rvvChunkFromIntrinsics_eq_map p input

private theorem neonPartialTailLivePrefixFromIntrinsics_eq_take_map
    (p : QS8LReLUParams) (loaded : List (BitVec 8)) (hLength : loaded.length = 8)
    (live : Nat) (hLive : live < 8) :
    neonPartialTailLivePrefixFromIntrinsics p loaded live =
      (loaded.map (laneValue p)).take live := by
  change littleEndianPrefixStore8 (neonBlock8FromIntrinsics p loaded) live = _
  rw [littleEndianPrefixStore8_eq_take _
    (by simp [neonBlock8FromIntrinsics_eq_map, hLength]) _ hLive]
  rw [neonBlock8FromIntrinsics_eq_map p loaded hLength]

private theorem neonPartialTailWithOverread_eq_map
    (p : QS8LReLUParams) (input overread : List (BitVec 8))
    (hLength : input.length < 8)
    (hOverread : 8 - input.length <= overread.length) :
    let loaded := (input ++ overread).take 8
    neonPartialTailLivePrefixFromIntrinsics p loaded input.length =
      input.map (laneValue p) := by
  dsimp only
  let loaded := (input ++ overread).take 8
  have hLoaded : loaded.length = 8 := by
    simp [loaded, List.length_take]
    omega
  rw [neonPartialTailLivePrefixFromIntrinsics_eq_take_map
    p loaded hLoaded input.length hLength]
  have hLoadedPrefix : loaded.take input.length = input := by
    simp only [loaded, List.take_take]
    rw [show min input.length 8 = input.length by omega]
    simp
  rw [<- List.map_take, hLoadedPrefix]

private theorem neonValueLoopWithOverreadFromIntrinsics_eq_map
    (p : QS8LReLUParams) (input overread : List (BitVec 8))
    (hOverread : 7 <= overread.length) :
    neonValueLoopWithOverreadFromIntrinsics p input overread =
      input.map (laneValue p) := by
  unfold neonValueLoopWithOverreadFromIntrinsics
  apply runFixedChunkTail_eq_map 8 (by decide)
      (neonBlock8FromIntrinsics p) _ (laneValue p)
  · exact neonBlock8FromIntrinsics_eq_map p
  · intro tail _ hTail
    exact neonPartialTailWithOverread_eq_map p tail overread hTail (by omega)

private theorem rvvValueLoopFromIntrinsics_eq_map
    (p : QS8LReLUParams) (input : List (BitVec 8))
    (schedule : PositivePartition input.length) :
    rvvValueLoopFromIntrinsics p input schedule = input.map (laneValue p) :=
  processBlocks_eq_map _ _ (rvvChunkFromIntrinsics_eq_map p) input schedule

/-- Candidate proof of the protected arbitrary-length value claim. -/
theorem allLengthsValueEqualWithOverread
    (p : QS8LReLUParams)
    (hwf : WellFormedParams p)
    (input overread : List (BitVec 8))
    (hOverread : 7 <= overread.length)
    (schedule : PositivePartition input.length) :
    allLengthsValueEqualWithOverreadClaim p hwf input overread hOverread schedule := by
  unfold allLengthsValueEqualWithOverreadClaim
  rw [neonValueLoopWithOverreadFromIntrinsics_eq_map p input overread hOverread]
  rw [rvvValueLoopFromIntrinsics_eq_map p input schedule]

end SALT.Generated.QS8VLReLU
