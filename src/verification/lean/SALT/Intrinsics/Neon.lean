/- NEON intrinsics shallow-embedded over CoreOp via lane combinators. -/
import SALT.Core.Lane

namespace SALT.Intrinsics.Neon

open SALT
open SALT.Core

-- vsubl_s8: signed subtract long (8→16). result[i] = sext16(a[i]) - sext16(b[i]).
def vsubl_s8 (a b : List (BitVec 8))
    (h : a.length = b.length := by simp) : List (BitVec 16) :=
  lanewiseBin
    (fun x y => BVBinOp.sub.eval (BVExtOp.sExt.eval 16 x) (BVExtOp.sExt.eval 16 y))
    a b h

-- vmovl_s16: signed move long (16→32). result[i] = sext32(a[i]).
def vmovl_s16 (a : List (BitVec 16)) : List (BitVec 32) :=
  lanewise (BVExtOp.sExt.eval 32) a

-- vmulq_s32: multiply each lane by scalar. result[i] = a[i] * scalar.
def vmulq_s32 (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  lanewiseBin BVBinOp.mul.eval a (broadcast scalar a.length)

-- vmlaq_s32: multiply-accumulate. result[i] = acc[i] + b[i] * c.
def vmlaq_s32 (acc b : List (BitVec 32)) (c : BitVec 32)
    (h : acc.length = b.length := by simp) : List (BitVec 32) :=
  lanewiseBin BVBinOp.add.eval acc
    (lanewiseBin BVBinOp.mul.eval b (broadcast c b.length))
    (by simpa [broadcast, List.length_zipWith, List.length_replicate] using h)

-- vrshlq_s32: rounding shift right.
def vrshlq_s32 (a : List (BitVec 32)) (shift : Nat) : List (BitVec 32) :=
  lanewise (fun x => (BVShiftOp.roundShr .neon).eval x shift) a

-- vqmovn_s32: signed saturating narrow (32→16). result[i] = signedClamp(a[i], 16).
def vqmovn_s32 (a : List (BitVec 32)) : List (BitVec 16) :=
  lanewise (BVNarrowOp.sSatNarrow.eval 16) a

-- vqmovn_s16: signed saturating narrow (16→8). result[i] = signedClamp(a[i], 8).
def vqmovn_s16 (a : List (BitVec 16)) : List (BitVec 8) :=
  lanewise (BVNarrowOp.sSatNarrow.eval 8) a

-- vqaddq_s16: signed saturating add. result[i] = signedSatAdd(a[i], scalar).
def vqaddq_s16 (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 16) :=
  lanewiseBin BVBinOp.sSatAdd.eval a (broadcast scalar a.length)

-- vmax_s8 / vmin_s8: signed element-wise max/min against a scalar.
def vmax_s8 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  lanewiseBin BVBinOp.sMax.eval a (broadcast scalar a.length)

def vmin_s8 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  lanewiseBin BVBinOp.sMin.eval a (broadcast scalar a.length)

-- Half-vector extract / combine, used by the split-recombine widening idiom.
-- At the list level these are take/drop and ++; widening happens in vmovl_s16.

/-- First half of a vector. -/
def vget_low_s16 (v : List (BitVec 16)) : List (BitVec 16) :=
  v.take (v.length / 2)

/-- Second half of a vector. -/
def vget_high_s16 (v : List (BitVec 16)) : List (BitVec 16) :=
  v.drop (v.length / 2)

/-- Concatenate two widened halves into one vector. -/
def vcombine_s32 (lo hi : List (BitVec 32)) : List (BitVec 32) :=
  lo ++ hi

/-- Combining the widened halves equals widening the whole vector. -/
theorem vcombine_widen_eq_vmovl (v : List (BitVec 16)) :
    vcombine_s32 (vmovl_s16 (vget_low_s16 v)) (vmovl_s16 (vget_high_s16 v)) =
    vmovl_s16 v := by
  simp [vcombine_s32, vmovl_s16, vget_low_s16, vget_high_s16,
        SALT.Core.lanewise, List.map_take, List.map_drop, List.take_append_drop]

-- Length lemmas (@[simp]) for closing call-site length obligations.

@[simp] theorem length_vsubl_s8 (a b : List (BitVec 8))
    {h : a.length = b.length} :
    (vsubl_s8 a b h).length = a.length := by
  simp [vsubl_s8, List.length_zipWith, h]

@[simp] theorem length_vmovl_s16 (a : List (BitVec 16)) :
    (vmovl_s16 a).length = a.length := by simp [vmovl_s16]

@[simp] theorem length_vmulq_s32 (a : List (BitVec 32)) (scalar : BitVec 32) :
    (vmulq_s32 a scalar).length = a.length := by
  simp [vmulq_s32, List.length_zipWith, broadcast]

@[simp] theorem length_vmlaq_s32 (acc b : List (BitVec 32)) (c : BitVec 32)
    {h : acc.length = b.length} :
    (vmlaq_s32 acc b c h).length = acc.length := by
  simp [vmlaq_s32, List.length_zipWith, broadcast, h]

@[simp] theorem length_vrshlq_s32 (a : List (BitVec 32)) (shift : Nat) :
    (vrshlq_s32 a shift).length = a.length := by simp [vrshlq_s32]

@[simp] theorem length_vqmovn_s32 (a : List (BitVec 32)) :
    (vqmovn_s32 a).length = a.length := by simp [vqmovn_s32]

@[simp] theorem length_vqmovn_s16 (a : List (BitVec 16)) :
    (vqmovn_s16 a).length = a.length := by simp [vqmovn_s16]

@[simp] theorem length_vqaddq_s16 (a : List (BitVec 16)) (scalar : BitVec 16) :
    (vqaddq_s16 a scalar).length = a.length := by
  simp [vqaddq_s16, List.length_zipWith, broadcast]

@[simp] theorem length_vmax_s8 (a : List (BitVec 8)) (scalar : BitVec 8) :
    (vmax_s8 a scalar).length = a.length := by
  simp [vmax_s8, List.length_zipWith, broadcast]

@[simp] theorem length_vmin_s8 (a : List (BitVec 8)) (scalar : BitVec 8) :
    (vmin_s8 a scalar).length = a.length := by
  simp [vmin_s8, List.length_zipWith, broadcast]

@[simp] theorem length_vget_low_s16 (v : List (BitVec 16)) :
    (vget_low_s16 v).length = v.length / 2 := by
  have : v.length / 2 ≤ v.length := Nat.div_le_self _ _
  simp [vget_low_s16, List.length_take, Nat.min_eq_left this]

@[simp] theorem length_vget_high_s16 (v : List (BitVec 16)) :
    (vget_high_s16 v).length = v.length - v.length / 2 := by
  simp [vget_high_s16, List.length_drop]

@[simp] theorem length_vcombine_s32 (lo hi : List (BitVec 32)) :
    (vcombine_s32 lo hi).length = lo.length + hi.length := by
  simp [vcombine_s32]

end SALT.Intrinsics.Neon
