import SALT.Generated.QS8VLReLU.Models
import SALT.Kernel.QS8VLReLU.Contract
import SALT.Proof.QrdmulhEquiv

namespace SALT.Generated.QS8VLReLU

open SALT.Intrinsics
open SALT.Kernel.QS8VLReLU
open SALT.Proof.QrdmulhEquiv

private def neonLane (p : QS8LReLUParams) (x : BitVec 8) : BitVec 8 :=
  let difference := p.input_zero_point.truncate 16 - SALT.sext x 16
  let mask : BitVec 16 :=
    if difference.toInt < 0 then BitVec.allOnes 16 else BitVec.ofNat 16 0
  let positive := -(p.positive_multiplier.truncate 16)
  let negative := -(p.negative_multiplier.truncate 16)
  let multiplier := (mask &&& positive) ||| ((~~~mask) &&& negative)
  let scaled := difference.shiftLeft 7
  SALT.signedClamp
    (SALT.signedSatAdd (Neon.sqrdmulh_s16 scaled multiplier)
      (p.output_zero_point.truncate 16)) 8

private def rvvLane (p : QS8LReLUParams) (x : BitVec 8) : BitVec 8 :=
  let difference := p.input_zero_point.truncate 16 - SALT.sext x 16
  let positive := (-p.positive_multiplier).truncate 16
  let negative := (-p.negative_multiplier).truncate 16
  let multiplier := if difference.toInt < 0 then positive else negative
  let scaled := difference.shiftLeft 7
  let product := BitVec.ofInt 32 (scaled.toInt * multiplier.toInt)
  RVV.vnclipSigned 8 .rdn 0
    (SALT.signedSatAdd (RVV.vnclipSigned 16 .rnu 15 product)
      (p.output_zero_point.truncate 16))

private theorem select_equal (p : QS8LReLUParams) (difference : BitVec 16) :
    (let mask : BitVec 16 :=
        if difference.toInt < 0 then BitVec.allOnes 16 else BitVec.ofNat 16 0;
      (mask &&& (-(p.positive_multiplier.truncate 16))) |||
        ((~~~mask) &&& (-(p.negative_multiplier.truncate 16)))) =
      (if difference.toInt < 0 then (-p.positive_multiplier).truncate 16
        else (-p.negative_multiplier).truncate 16) := by
  have hPositive : (-p.positive_multiplier).truncate 16 =
      -(p.positive_multiplier.truncate 16) :=
    BitVec.setWidth_neg_of_le (x := p.positive_multiplier)
      (w := 16) (v := 32) (by omega)
  have hNegative : (-p.negative_multiplier).truncate 16 =
      -(p.negative_multiplier.truncate 16) :=
    BitVec.setWidth_neg_of_le (x := p.negative_multiplier)
      (w := 16) (v := 32) (by omega)
  rw [hPositive, hNegative]
  by_cases h : difference.toInt < 0
  · simp only [h, if_true, BitVec.not_allOnes, BitVec.allOnes_and,
      BitVec.zero_and, BitVec.or_zero]
  · simp only [h, if_false, BitVec.not_zero, BitVec.zero_and,
      BitVec.allOnes_and, BitVec.zero_or]

private theorem lane_equal (p : QS8LReLUParams) (x : BitVec 8) :
    neonLane p x = rvvLane p x := by
  let difference : BitVec 16 := p.input_zero_point.truncate 16 - SALT.sext x 16
  let scaled : BitVec 16 := difference.shiftLeft 7
  simp only [neonLane, rvvLane]
  change SALT.signedClamp
      (SALT.signedSatAdd
        (Neon.sqrdmulh_s16 scaled
          (let mask : BitVec 16 :=
            if difference.toInt < 0 then BitVec.allOnes 16 else BitVec.ofNat 16 0;
           (mask &&& (-(p.positive_multiplier.truncate 16))) |||
            ((~~~mask) &&& (-(p.negative_multiplier.truncate 16)))))
        (p.output_zero_point.truncate 16)) 8 =
    RVV.vnclipSigned 8 .rdn 0
      (SALT.signedSatAdd
        (RVV.vnclipSigned 16 .rnu 15
          (BitVec.ofInt 32
            (scaled.toInt *
              (if difference.toInt < 0 then (-p.positive_multiplier).truncate 16
               else (-p.negative_multiplier).truncate 16).toInt)))
        (p.output_zero_point.truncate 16))
  rw [select_equal p difference]
  rw [sqrdmulh_eq_rvv_shift15]
  exact signedClamp_eq_vnclip_rdn_zero _

private theorem neon_model_as_map (p : QS8LReLUParams)
    (input : List (BitVec 8)) (hLength : input.length = 8) :
    neonBlock8FromIntrinsics p input = input.map (neonLane p) := by
  simp [neonBlock8FromIntrinsics, Neon.vsubw_s8, Neon.vcltq_s16,
    Neon.vshlq_n_s16, Neon.vbslq_s16, Neon.vqrdmulhq_s16,
    Neon.vqaddq_s16, Neon.vqmovn_s16, neonLane, SALT.sext,
    SALT.zipWith_replicate_left, SALT.zipWith_replicate_right,
    List.map_map, <- hLength]

private theorem rvv_model_as_map (p : QS8LReLUParams)
    (input : List (BitVec 8)) :
    rvvChunkFromIntrinsics p input = input.map (rvvLane p) := by
  simp [rvvChunkFromIntrinsics, RVV.vsext_vf2_i16, RVV.vrsub_vx_i16,
    RVV.vmslt_vx_i16, RVV.vsll_vx_i16, RVV.vmerge_vxm_i16,
    RVV.vwmul_vv_i32, RVV.vnclip_wx_i16_mode, RVV.vsadd_vx,
    RVV.vnclip_wx_i8_mode, RVV.VXRoundingMode.decode, rvvLane, SALT.sext,
    SALT.zipWith_replicate_left, List.map_map]

/-- Equality of the independently generated local blocks for every 32-bit
    parameter representation. This theorem is about lane values, not flags. -/
theorem generated_block_equal_unconditional
    (p : QS8LReLUParams)
    (input : List (BitVec 8))
    (hLength : input.length = 8) :
    neonBlock8FromIntrinsics p input = rvvChunkFromIntrinsics p input := by
  rw [neon_model_as_map p input hLength, rvv_model_as_map]
  apply List.map_congr_left
  intro x _hx
  exact lane_equal p x

/-- Contract-bound entry point for the pinned XNNPACK parameter producer. -/
theorem generated_block_equal
    (p : QS8LReLUParams)
    (_hwf : WellFormedParams p)
    (input : List (BitVec 8))
    (hLength : input.length = 8) :
    neonBlock8FromIntrinsics p input = rvvChunkFromIntrinsics p input :=
  generated_block_equal_unconditional p input hLength

end SALT.Generated.QS8VLReLU
