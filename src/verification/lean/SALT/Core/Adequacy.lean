/-
  Adequacy check: each supported intrinsic equals a one-line CoreOp
  expression definitionally (every theorem closes by `rfl`).
-/
import SALT.Core.Lane
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV

namespace SALT.Core.Adequacy

open SALT
open SALT.Core
open SALT.Intrinsics.Neon
open SALT.Intrinsics.RVV

-- NEON adequacy

/-- `vsubl_s8` = sign-extend both inputs to 16b, then binary subtract. -/
theorem vsubl_s8_core (a b : List (BitVec 8)) (h : a.length = b.length) :
    vsubl_s8 a b (h := h) =
      lanewiseBin
        (fun x y => BVBinOp.sub.eval (BVExtOp.sExt.eval 16 x) (BVExtOp.sExt.eval 16 y))
        a b (h := h) := rfl

/-- `vmovl_s16` = lanewise sign extend to 32b. -/
theorem vmovl_s16_core (a : List (BitVec 16)) :
    vmovl_s16 a = lanewise (BVExtOp.sExt.eval 32) a := rfl

/-- `vmulq_s32` = binary multiply against a broadcast scalar. -/
theorem vmulq_s32_core (a : List (BitVec 32)) (scalar : BitVec 32) :
    vmulq_s32 a scalar =
      lanewiseBin BVBinOp.mul.eval a (broadcast scalar a.length) := rfl

/-- `vmlaq_s32` acc + b * c: broadcast-multiply then add. -/
theorem vmlaq_s32_core (acc b : List (BitVec 32)) (c : BitVec 32)
    (h : acc.length = b.length) :
    vmlaq_s32 acc b c (h := h) =
      lanewiseBin BVBinOp.add.eval acc
        (lanewiseBin BVBinOp.mul.eval b (broadcast c b.length))
        (by simpa [broadcast, List.length_zipWith, List.length_replicate] using h) := rfl

/-- `vrshlq_s32` = lanewise NEON-flavored rounding shift right. -/
theorem vrshlq_s32_core (a : List (BitVec 32)) (shift : Nat) :
    vrshlq_s32 a shift =
      lanewise (fun x => (BVShiftOp.roundShr .neon).eval x shift) a := rfl

/-- `vqmovn_s32` = lanewise signed saturating narrow to 16b. -/
theorem vqmovn_s32_core (a : List (BitVec 32)) :
    vqmovn_s32 a = lanewise (BVNarrowOp.sSatNarrow.eval 16) a := rfl

/-- `vqmovn_s16` = lanewise signed saturating narrow to 8b. -/
theorem vqmovn_s16_core (a : List (BitVec 16)) :
    vqmovn_s16 a = lanewise (BVNarrowOp.sSatNarrow.eval 8) a := rfl

/-- `vqaddq_s16` = signed saturating add against a broadcast scalar. -/
theorem vqaddq_s16_core (a : List (BitVec 16)) (scalar : BitVec 16) :
    vqaddq_s16 a scalar =
      lanewiseBin BVBinOp.sSatAdd.eval a (broadcast scalar a.length) := rfl

/-- `vmax_s8` = signed max against a broadcast scalar. -/
theorem vmax_s8_core (a : List (BitVec 8)) (scalar : BitVec 8) :
    vmax_s8 a scalar =
      lanewiseBin BVBinOp.sMax.eval a (broadcast scalar a.length) := rfl

/-- `vmin_s8` = signed min against a broadcast scalar. -/
theorem vmin_s8_core (a : List (BitVec 8)) (scalar : BitVec 8) :
    vmin_s8 a scalar =
      lanewiseBin BVBinOp.sMin.eval a (broadcast scalar a.length) := rfl

-- RVV adequacy

/-- `vwsub_vx` = lanewise sign-extend then subtract the extended scalar. -/
theorem vwsub_vx_core (a : List (BitVec 8)) (scalar : BitVec 8) :
    vwsub_vx a scalar =
      lanewise
        (fun x => BVBinOp.sub.eval (BVExtOp.sExt.eval 16 x) (BVExtOp.sExt.eval 16 scalar))
        a := rfl

/-- `vsext_vf2` = lanewise sign extend to 32b. -/
theorem vsext_vf2_core (a : List (BitVec 16)) :
    vsext_vf2 a = lanewise (BVExtOp.sExt.eval 32) a := rfl

/-- `vmv_v_x` = broadcast. -/
theorem vmv_v_x_core (scalar : BitVec 32) (vl : Nat) :
    vmv_v_x scalar vl = broadcast scalar vl := rfl

/-- `vmul_vx` = binary multiply against a broadcast scalar. -/
theorem vmul_vx_core (a : List (BitVec 32)) (scalar : BitVec 32) :
    vmul_vx a scalar =
      lanewiseBin BVBinOp.mul.eval a (broadcast scalar a.length) := rfl

/-- `vmacc_vx` dest + scalar * src: broadcast-multiply then add. -/
theorem vmacc_vx_core (dest : List (BitVec 32)) (scalar : BitVec 32)
    (src : List (BitVec 32)) (h : dest.length = src.length) :
    vmacc_vx dest scalar src (h := h) =
      lanewiseBin BVBinOp.add.eval dest
        (lanewiseBin BVBinOp.mul.eval src (broadcast scalar src.length))
        (by simpa [broadcast, List.length_zipWith, List.length_replicate] using h) := rfl

/-- `vssra_vx_rnu` = lanewise RVV-RNU-flavored rounding shift right. -/
theorem vssra_vx_rnu_core (a : List (BitVec 32)) (shift : Nat) :
    vssra_vx_rnu a shift =
      lanewise (fun x => (BVShiftOp.roundShr .rvvRnu).eval x shift) a := rfl

/-- `vnclip_wx_i16` = lanewise signed saturating narrow to 16b. -/
theorem vnclip_wx_i16_core (a : List (BitVec 32)) :
    vnclip_wx_i16 a = lanewise (BVNarrowOp.sSatNarrow.eval 16) a := rfl

/-- `vnclip_wx_i8` = lanewise signed saturating narrow to 8b. -/
theorem vnclip_wx_i8_core (a : List (BitVec 16)) :
    vnclip_wx_i8 a = lanewise (BVNarrowOp.sSatNarrow.eval 8) a := rfl

/-- `vsadd_vx` = signed saturating add against a broadcast scalar. -/
theorem vsadd_vx_core (a : List (BitVec 16)) (scalar : BitVec 16) :
    vsadd_vx a scalar =
      lanewiseBin BVBinOp.sSatAdd.eval a (broadcast scalar a.length) := rfl

/-- `vmax_vx` = signed max against a broadcast scalar. -/
theorem vmax_vx_core (a : List (BitVec 8)) (scalar : BitVec 8) :
    vmax_vx a scalar =
      lanewiseBin BVBinOp.sMax.eval a (broadcast scalar a.length) := rfl

/-- `vmin_vx` = signed min against a broadcast scalar. -/
theorem vmin_vx_core (a : List (BitVec 8)) (scalar : BitVec 8) :
    vmin_vx a scalar =
      lanewiseBin BVBinOp.sMin.eval a (broadcast scalar a.length) := rfl

-- FP scalar adequacy

/-- `FPBinOp.fAdd.eval` is plain Float32 `+`. -/
theorem fAdd_scalar (a b : Float32) : FPBinOp.fAdd.eval a b = a + b := rfl

/-- `FPBinOp.fSub.eval` is plain Float32 `-`. -/
theorem fSub_scalar (a b : Float32) : FPBinOp.fSub.eval a b = a - b := rfl

/-- `FPBinOp.fMul.eval` is plain Float32 `*`. -/
theorem fMul_scalar (a b : Float32) : FPBinOp.fMul.eval a b = a * b := rfl

/-- `FPBinOp.fMax.eval` is the NaN-suppressing `fmax` from `SALT.FP`. -/
theorem fMax_scalar (a b : Float32) :
    FPBinOp.fMax.eval a b = SALT.FP.fmax a b := rfl

/-- `FPCmpOp.fLt.eval` is plain Float32 `<`, elaborated into `Bool`. -/
theorem fLt_scalar (a b : Float32) : FPCmpOp.fLt.eval a b = ((a < b) : Bool) := rfl

-- Reinterpret adequacy (Float32 ↔ BitVec 32)

theorem f32ToBits_scalar (x : Float32) :
    ReinterpretOp.f32ToBits.eval x = BitVec.ofNat 32 x.toBits.toNat := rfl

theorem bitsToF32_scalar (b : BitVec 32) :
    ReinterpretOp.bitsToF32.eval b = Float32.ofBits (UInt32.ofNat b.toNat) := rfl

-- Integer scalar adequacy: each `.eval` agrees with Lean's built-in BitVec operators.

theorem add_scalar {w : Nat} (a b : BitVec w) : BVBinOp.add.eval a b = a + b := rfl
theorem sub_scalar {w : Nat} (a b : BitVec w) : BVBinOp.sub.eval a b = a - b := rfl
theorem mul_scalar {w : Nat} (a b : BitVec w) : BVBinOp.mul.eval a b = a * b := rfl
theorem and_scalar {w : Nat} (a b : BitVec w) : BVBinOp.bvAnd.eval a b = a &&& b := rfl
theorem or_scalar  {w : Nat} (a b : BitVec w) : BVBinOp.bvOr.eval  a b = a ||| b := rfl
theorem xor_scalar {w : Nat} (a b : BitVec w) : BVBinOp.bvXor.eval a b = a ^^^ b := rfl
theorem sMin_scalar {w : Nat} (a b : BitVec w) :
    BVBinOp.sMin.eval a b = SALT.bvSignedMin a b := rfl
theorem sMax_scalar {w : Nat} (a b : BitVec w) :
    BVBinOp.sMax.eval a b = SALT.bvSignedMax a b := rfl
theorem sSatAdd_scalar {w : Nat} (a b : BitVec w) :
    BVBinOp.sSatAdd.eval a b = SALT.signedSatAdd a b := rfl

theorem shl_scalar  {w : Nat} (x : BitVec w) (n : Nat) :
    BVShiftOp.shl.eval  x n = x <<< n := rfl
theorem lshr_scalar {w : Nat} (x : BitVec w) (n : Nat) :
    BVShiftOp.lshr.eval x n = x >>> n := rfl
theorem ashr_scalar {w : Nat} (x : BitVec w) (n : Nat) :
    BVShiftOp.ashr.eval x n = x.sshiftRight n := rfl
theorem roundShr_neon_scalar {w : Nat} (x : BitVec w) (n : Nat) :
    (BVShiftOp.roundShr .neon).eval x n = SALT.neonRoundingShiftRight x n := rfl
theorem roundShr_rvvRnu_scalar {w : Nat} (x : BitVec w) (n : Nat) :
    (BVShiftOp.roundShr .rvvRnu).eval x n = SALT.rvvRoundingShiftRight x n := rfl

/-- sExt witness, carrying the `w < w'` hypothesis. -/
theorem sExt_scalar {w w' : Nat} (x : BitVec w) (h : w < w') :
    BVExtOp.sExt.eval w' x h = SALT.sext x w' := rfl

/-- sSatNarrow witness, carrying the `w' < w` hypothesis. -/
theorem sSatNarrow_scalar {w w' : Nat} (x : BitVec w) (h : w' < w) :
    BVNarrowOp.sSatNarrow.eval w' x h = SALT.signedClamp x w' := rfl

end SALT.Core.Adequacy
