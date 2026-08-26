import SALT.Generated.QU8VAddMinmax.Proof
import SALT.Generated.QU8VAddMinmax.Obligation

namespace SALT.Generated.QU8VAddMinmax

open SALT.Intrinsics
open SALT.Kernel.QU8VAddMinmax
open SALT.Kernel.Schedule

private def laneValue (p : QU8AddMinmaxParams)
    (a b : BitVec 8) : BitVec 8 :=
  let xa := (a.zeroExtend 16 - p.a_zero_point.zeroExtend 16).signExtend 32
  let xb := (b.zeroExtend 16 - p.b_zero_point.zeroExtend 16).signExtend 32
  let aProduct := xa * p.a_multiplier
  let bProduct := xb * p.b_multiplier
  let acc := aProduct + bProduct
  let shifted :=
    if p.shift.toInt >= 0 then
      BitVec.ofInt 32 (RVV.roundShiftSigned .rnu acc p.shift.toNat)
    else
      aProduct.shiftLeft (-p.shift.toInt).toNat +
        bProduct.shiftLeft (-p.shift.toInt).toNat
  let narrowed := RVV.vnclipSigned 16 .rdn 0 shifted
  let withZeroPoint := SALT.signedSatAdd narrowed p.output_zero_point
  let nonnegative := SALT.bvSignedMax withZeroPoint (BitVec.ofNat 16 0)
  let asUnsigned := RVV.vnclipUnsigned 8 .rdn 0 nonnegative
  let aboveMin :=
    if asUnsigned.toNat >= p.output_min.toNat then asUnsigned else p.output_min
  if aboveMin.toNat <= p.output_max.toNat then aboveMin else p.output_max

private theorem rvvChunkFromIntrinsics_eq_zipWith
    (p : QU8AddMinmaxParams) (inputA inputB : List (BitVec 8)) :
    rvvChunkFromIntrinsics p inputA inputB =
      List.zipWith (laneValue p) inputA inputB := by
  unfold laneValue
  by_cases hShift : p.shift.toInt >= 0
  · simp [rvvChunkFromIntrinsics, RVV.vwsubu_vx_u16, RVV.vsext_vf2,
      RVV.vmul_vx, RVV.vmacc_vx, RVV.vssra_vx_i32_mode,
      RVV.vnclip_wx_i16_mode, RVV.vsadd_vx,
      RVV.vmax_vx_i16, RVV.vnclipu_wx_u8_mode, RVV.vmaxu_vx_u8,
      RVV.vminu_vx_u8, RVV.VXRoundingMode.decode, SALT.sext, hShift,
      List.map_map]
  · simp [rvvChunkFromIntrinsics, RVV.vwsubu_vx_u16, RVV.vsext_vf2,
      RVV.vmul_vx, RVV.vmacc_vx, RVV.vsll_vx_i32,
      RVV.vnclip_wx_i16_mode, RVV.vsadd_vx,
      RVV.vmax_vx_i16, RVV.vnclipu_wx_u8_mode, RVV.vmaxu_vx_u8,
      RVV.vminu_vx_u8, RVV.VXRoundingMode.decode, SALT.sext, hShift,
      List.map_map]

private theorem neonBlock8FromIntrinsics_eq_zipWith
    (p : QU8AddMinmaxParams) (hwf : WellFormedParams p)
    (inputA inputB : List (BitVec 8))
    (sameLength : inputA.length = inputB.length)
    (hLength : inputA.length = 8) :
    neonBlock8FromIntrinsics p inputA inputB =
      List.zipWith (laneValue p) inputA inputB := by
  have hB : inputB.length = 8 := by omega
  rw [generated_block_equal p hwf inputA inputB hLength hB]
  exact rvvChunkFromIntrinsics_eq_zipWith p inputA inputB

private theorem neonPartialTailLivePrefixFromIntrinsics_eq_take_zipWith
    (p : QU8AddMinmaxParams) (hwf : WellFormedParams p)
    (loadedA loadedB : List (BitVec 8))
    (sameLength : loadedA.length = loadedB.length)
    (hLength : loadedA.length = 8)
    (live : Nat) (hLive : live < 8) :
    neonPartialTailLivePrefixFromIntrinsics p loadedA loadedB live =
      (List.zipWith (laneValue p) loadedA loadedB).take live := by
  change littleEndianPrefixStore8
      (neonBlock8FromIntrinsics p loadedA loadedB) live = _
  rw [neonBlock8FromIntrinsics_eq_zipWith p hwf loadedA loadedB sameLength hLength]
  exact littleEndianPrefixStore8_eq_take _ (by
    simp [List.length_zipWith]
    omega) live hLive

private theorem neonPartialTailWithOverread_eq_zipWith
    (p : QU8AddMinmaxParams) (hwf : WellFormedParams p)
    (inputA inputB overreadA overreadB : List (BitVec 8))
    (sameLength : inputA.length = inputB.length)
    (hPositive : 0 < inputA.length) (hLength : inputA.length < 8)
    (hOverreadA : 8 - inputA.length <= overreadA.length)
    (hOverreadB : 8 - inputB.length <= overreadB.length) :
    let loadedA := (inputA ++ overreadA).take 8
    let loadedB := (inputB ++ overreadB).take 8
    neonPartialTailLivePrefixFromIntrinsics p loadedA loadedB inputA.length =
      List.zipWith (laneValue p) inputA inputB := by
  dsimp only
  let loadedA := (inputA ++ overreadA).take 8
  let loadedB := (inputB ++ overreadB).take 8
  have hLoadedA : loadedA.length = 8 := by
    simp [loadedA, List.length_take]
    omega
  have hLoadedB : loadedB.length = 8 := by
    simp [loadedB, List.length_take]
    omega
  have hLoadedSame : loadedA.length = loadedB.length := by omega
  rw [neonPartialTailLivePrefixFromIntrinsics_eq_take_zipWith
    p hwf loadedA loadedB hLoadedSame hLoadedA inputA.length hLength]
  rw [List.take_zipWith]
  have hPrefixA : loadedA.take inputA.length = inputA := by
    simp only [loadedA, List.take_take]
    rw [show min inputA.length 8 = inputA.length by omega]
    simp
  have hPrefixB : loadedB.take inputA.length = inputB := by
    simp only [loadedB, List.take_take]
    rw [show min inputA.length 8 = inputA.length by omega]
    rw [sameLength]
    simp
  rw [hPrefixA, hPrefixB]

private theorem neonValueLoopWithOverreadFromIntrinsics_eq_zipWith
    (p : QU8AddMinmaxParams) (hwf : WellFormedParams p)
    (inputA inputB overreadA overreadB : List (BitVec 8))
    (sameLength : inputA.length = inputB.length)
    (hOverreadA : 7 <= overreadA.length)
    (hOverreadB : 7 <= overreadB.length) :
    neonValueLoopWithOverreadFromIntrinsics
        p inputA inputB overreadA overreadB sameLength =
      List.zipWith (laneValue p) inputA inputB := by
  unfold neonValueLoopWithOverreadFromIntrinsics
  apply runFixedChunkTail2_eq_zipWith 8 (by decide)
      (neonBlock8FromIntrinsics p) _ (laneValue p)
  · intro blockA blockB hSame hBlockLength
    exact neonBlock8FromIntrinsics_eq_zipWith
      p hwf blockA blockB hSame hBlockLength
  · intro tailA tailB hSame hPositive hTailLength
    exact neonPartialTailWithOverread_eq_zipWith p hwf tailA tailB
      overreadA overreadB hSame hPositive hTailLength (by omega) (by omega)

private theorem rvvValueLoopFromIntrinsics_eq_zipWith
    (p : QU8AddMinmaxParams) (inputA inputB : List (BitVec 8))
    (sameLength : inputA.length = inputB.length)
    (schedule : PositivePartition inputA.length) :
    rvvValueLoopFromIntrinsics p inputA inputB sameLength schedule =
      List.zipWith (laneValue p) inputA inputB :=
  processBlocks2_eq_zipWith _ _
    (fun blockA blockB _ => rvvChunkFromIntrinsics_eq_zipWith p blockA blockB)
    inputA inputB sameLength schedule

/-- Candidate proof of the protected arbitrary-length value claim. -/
theorem allLengthsValueEqualWithOverread
    (p : QU8AddMinmaxParams)
    (hwf : WellFormedParams p)
    (inputA inputB overreadA overreadB : List (BitVec 8))
    (sameLength : inputA.length = inputB.length)
    (hOverreadA : 7 <= overreadA.length)
    (hOverreadB : 7 <= overreadB.length)
    (schedule : PositivePartition inputA.length) :
    allLengthsValueEqualWithOverreadClaim p hwf inputA inputB overreadA overreadB
      sameLength hOverreadA hOverreadB schedule := by
  unfold allLengthsValueEqualWithOverreadClaim
  rw [neonValueLoopWithOverreadFromIntrinsics_eq_zipWith
    p hwf inputA inputB overreadA overreadB sameLength hOverreadA hOverreadB]
  rw [rvvValueLoopFromIntrinsics_eq_zipWith p inputA inputB sameLength schedule]

end SALT.Generated.QU8VAddMinmax
