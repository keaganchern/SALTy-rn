/- RVV integer intrinsics shallow-embedded over CoreOp via lane combinators.
   LMUL is not modelled: a vector is a `List (BitVec w)` at element width `w`. -/
import SALT.Core.Lane

namespace SALT.Intrinsics.RVV

open SALT
open SALT.Core

-- Section 1. Integer arithmetic (same-width). One def per width covers
-- both signed and unsigned (identical two's-complement bit patterns).

-- vadd_vv: lanewise add. res[i] = op1[i] + op2[i].
def vadd_vv_i8 (a b : List (BitVec 8))
    (h : a.length = b.length := by simp) : List (BitVec 8) :=
  lanewiseBin BVBinOp.add.eval a b h

def vadd_vv_i16 (a b : List (BitVec 16))
    (h : a.length = b.length := by simp) : List (BitVec 16) :=
  lanewiseBin BVBinOp.add.eval a b h

def vadd_vv_i32 (a b : List (BitVec 32))
    (h : a.length = b.length := by simp) : List (BitVec 32) :=
  lanewiseBin BVBinOp.add.eval a b h

-- vadd_vx: add scalar to each lane. res[i] = a[i] + scalar.
def vadd_vx_i8 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  lanewiseBin BVBinOp.add.eval a (broadcast scalar a.length)

def vadd_vx_i16 (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 16) :=
  lanewiseBin BVBinOp.add.eval a (broadcast scalar a.length)

def vadd_vx_i32 (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  lanewiseBin BVBinOp.add.eval a (broadcast scalar a.length)

-- vsub_vv: lanewise sub. res[i] = op1[i] - op2[i].
def vsub_vv_i8 (a b : List (BitVec 8))
    (h : a.length = b.length := by simp) : List (BitVec 8) :=
  lanewiseBin BVBinOp.sub.eval a b h

def vsub_vv_i16 (a b : List (BitVec 16))
    (h : a.length = b.length := by simp) : List (BitVec 16) :=
  lanewiseBin BVBinOp.sub.eval a b h

def vsub_vv_i32 (a b : List (BitVec 32))
    (h : a.length = b.length := by simp) : List (BitVec 32) :=
  lanewiseBin BVBinOp.sub.eval a b h

-- vsub_vx: subtract scalar from each lane. res[i] = a[i] - scalar.
def vsub_vx_i8 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  lanewiseBin BVBinOp.sub.eval a (broadcast scalar a.length)

def vsub_vx_i16 (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 16) :=
  lanewiseBin BVBinOp.sub.eval a (broadcast scalar a.length)

def vsub_vx_i32 (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  lanewiseBin BVBinOp.sub.eval a (broadcast scalar a.length)

-- vrsub_vx: reverse subtract. res[i] = scalar - a[i].
def vrsub_vx_i8 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  lanewise (fun x => BVBinOp.sub.eval scalar x) a

def vrsub_vx_i16 (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 16) :=
  lanewise (fun x => BVBinOp.sub.eval scalar x) a

def vrsub_vx_i32 (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  lanewise (fun x => BVBinOp.sub.eval scalar x) a

-- vmul_vv / vmul_vx at 32-bit element width.
def vmul_vv_i32 (a b : List (BitVec 32))
    (h : a.length = b.length := by simp) : List (BitVec 32) :=
  lanewiseBin BVBinOp.mul.eval a b h

-- Section 2. Bitwise (same-width): lanewise AND / OR / XOR.

def vand_vv_i8 (a b : List (BitVec 8))
    (h : a.length = b.length := by simp) : List (BitVec 8) :=
  lanewiseBin BVBinOp.bvAnd.eval a b h

def vand_vv_i32 (a b : List (BitVec 32))
    (h : a.length = b.length := by simp) : List (BitVec 32) :=
  lanewiseBin BVBinOp.bvAnd.eval a b h

def vand_vx_i8 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  lanewiseBin BVBinOp.bvAnd.eval a (broadcast scalar a.length)

def vand_vx_i16 (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 16) :=
  lanewiseBin BVBinOp.bvAnd.eval a (broadcast scalar a.length)

def vand_vx_i32 (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  lanewiseBin BVBinOp.bvAnd.eval a (broadcast scalar a.length)

def vor_vv_i8 (a b : List (BitVec 8))
    (h : a.length = b.length := by simp) : List (BitVec 8) :=
  lanewiseBin BVBinOp.bvOr.eval a b h

def vor_vx_i8 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  lanewiseBin BVBinOp.bvOr.eval a (broadcast scalar a.length)

def vxor_vv_i8 (a b : List (BitVec 8))
    (h : a.length = b.length := by simp) : List (BitVec 8) :=
  lanewiseBin BVBinOp.bvXor.eval a b h

def vxor_vx_i8 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  lanewiseBin BVBinOp.bvXor.eval a (broadcast scalar a.length)

-- Section 3. Shifts (non-rounding). vsll = left, vsra = arithmetic right,
-- vsrl = logical right; same shift amount across all lanes.

def vsll_vx_i8 (a : List (BitVec 8)) (shift : Nat) : List (BitVec 8) :=
  lanewise (fun x => BVShiftOp.shl.eval x shift) a

def vsll_vx_i16 (a : List (BitVec 16)) (shift : Nat) : List (BitVec 16) :=
  lanewise (fun x => BVShiftOp.shl.eval x shift) a

def vsll_vx_i32 (a : List (BitVec 32)) (shift : Nat) : List (BitVec 32) :=
  lanewise (fun x => BVShiftOp.shl.eval x shift) a

-- m8 LMUL spelling, identical to vsll_vx_i32; kept for existing kernel proofs.
def vsll_vx_i32m8 (a : List (BitVec 32)) (shift : Nat) : List (BitVec 32) :=
  lanewise (fun x => BVShiftOp.shl.eval x shift) a

def vsra_vx_i16 (a : List (BitVec 16)) (shift : Nat) : List (BitVec 16) :=
  lanewise (fun x => BVShiftOp.ashr.eval x shift) a

def vsra_vx_i32 (a : List (BitVec 32)) (shift : Nat) : List (BitVec 32) :=
  lanewise (fun x => BVShiftOp.ashr.eval x shift) a

def vsrl_vx_u8 (a : List (BitVec 8)) (shift : Nat) : List (BitVec 8) :=
  lanewise (fun x => BVShiftOp.lshr.eval x shift) a

def vsrl_vx_u16 (a : List (BitVec 16)) (shift : Nat) : List (BitVec 16) :=
  lanewise (fun x => BVShiftOp.lshr.eval x shift) a

def vsrl_vx_u32 (a : List (BitVec 32)) (shift : Nat) : List (BitVec 32) :=
  lanewise (fun x => BVShiftOp.lshr.eval x shift) a

-- Section 4. Rounding shift: vssra_vx at vxrm=RNU (signed arithmetic shift
-- right, round-to-nearest-up).

def vssra_vx_rnu (a : List (BitVec 32)) (shift : Nat) : List (BitVec 32) :=
  lanewise (fun x => (BVShiftOp.roundShr .rvvRnu).eval x shift) a

def vssra_vx_rnu_i16 (a : List (BitVec 16)) (shift : Nat) : List (BitVec 16) :=
  lanewise (fun x => (BVShiftOp.roundShr .rvvRnu).eval x shift) a

def vssra_vx_rnu_i8 (a : List (BitVec 8)) (shift : Nat) : List (BitVec 8) :=
  lanewise (fun x => (BVShiftOp.roundShr .rvvRnu).eval x shift) a

-- Section 5. Signed min / max. _vx clamps against a scalar; _vv compares
-- two vectors element-wise.

def vmax_vx (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  lanewiseBin BVBinOp.sMax.eval a (broadcast scalar a.length)

def vmax_vx_i16 (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 16) :=
  lanewiseBin BVBinOp.sMax.eval a (broadcast scalar a.length)

def vmax_vx_i32 (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  lanewiseBin BVBinOp.sMax.eval a (broadcast scalar a.length)

def vmin_vx (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  lanewiseBin BVBinOp.sMin.eval a (broadcast scalar a.length)

def vmin_vx_i16 (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 16) :=
  lanewiseBin BVBinOp.sMin.eval a (broadcast scalar a.length)

def vmin_vx_i32 (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  lanewiseBin BVBinOp.sMin.eval a (broadcast scalar a.length)

def vmax_vv_i32 (a b : List (BitVec 32))
    (h : a.length = b.length := by simp) : List (BitVec 32) :=
  lanewiseBin BVBinOp.sMax.eval a b h

def vmin_vv_i32 (a b : List (BitVec 32))
    (h : a.length = b.length := by simp) : List (BitVec 32) :=
  lanewiseBin BVBinOp.sMin.eval a b h

-- Section 6. Signed saturating add (_vv lanewise, _vx against a scalar).

def vsadd_vx (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 16) :=
  lanewiseBin BVBinOp.sSatAdd.eval a (broadcast scalar a.length)

def vsadd_vx_i8 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  lanewiseBin BVBinOp.sSatAdd.eval a (broadcast scalar a.length)

def vsadd_vx_i32 (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  lanewiseBin BVBinOp.sSatAdd.eval a (broadcast scalar a.length)

def vsadd_vv_i8 (a b : List (BitVec 8))
    (h : a.length = b.length := by simp) : List (BitVec 8) :=
  lanewiseBin BVBinOp.sSatAdd.eval a b h

def vsadd_vv_i16 (a b : List (BitVec 16))
    (h : a.length = b.length := by simp) : List (BitVec 16) :=
  lanewiseBin BVBinOp.sSatAdd.eval a b h

def vsadd_vv_i32 (a b : List (BitVec 32))
    (h : a.length = b.length := by simp) : List (BitVec 32) :=
  lanewiseBin BVBinOp.sSatAdd.eval a b h

-- Section 7. Signed widening: operands sign-extended to 2w, then arithmetic
-- in the wider width. vwmacc accumulates into a pre-existing wide vector.

-- Widening subtract vector-scalar (8 → 16).
def vwsub_vx (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 16) :=
  lanewise
    (fun x => BVBinOp.sub.eval (BVExtOp.sExt.eval 16 x) (BVExtOp.sExt.eval 16 scalar))
    a

def vwsub_vx_i32 (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 32) :=
  lanewise
    (fun x => BVBinOp.sub.eval (BVExtOp.sExt.eval 32 x) (BVExtOp.sExt.eval 32 scalar))
    a

def vwsub_vv_i16 (a b : List (BitVec 8))
    (h : a.length = b.length := by simp) : List (BitVec 16) :=
  lanewiseBin
    (fun x y => BVBinOp.sub.eval (BVExtOp.sExt.eval 16 x) (BVExtOp.sExt.eval 16 y))
    a b h

def vwsub_vv_i32 (a b : List (BitVec 16))
    (h : a.length = b.length := by simp) : List (BitVec 32) :=
  lanewiseBin
    (fun x y => BVBinOp.sub.eval (BVExtOp.sExt.eval 32 x) (BVExtOp.sExt.eval 32 y))
    a b h

def vwadd_vv_i16 (a b : List (BitVec 8))
    (h : a.length = b.length := by simp) : List (BitVec 16) :=
  lanewiseBin
    (fun x y => BVBinOp.add.eval (BVExtOp.sExt.eval 16 x) (BVExtOp.sExt.eval 16 y))
    a b h

def vwadd_vv_i32 (a b : List (BitVec 16))
    (h : a.length = b.length := by simp) : List (BitVec 32) :=
  lanewiseBin
    (fun x y => BVBinOp.add.eval (BVExtOp.sExt.eval 32 x) (BVExtOp.sExt.eval 32 y))
    a b h

def vwadd_vx_i16 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 16) :=
  lanewise
    (fun x => BVBinOp.add.eval (BVExtOp.sExt.eval 16 x) (BVExtOp.sExt.eval 16 scalar))
    a

def vwadd_vx_i32 (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 32) :=
  lanewise
    (fun x => BVBinOp.add.eval (BVExtOp.sExt.eval 32 x) (BVExtOp.sExt.eval 32 scalar))
    a

-- vwadd_wv: wide + narrow. The first operand is already at the wide width;
-- the second is sign-extended. Result stays wide. op1[i] + sext(op2[i]).
def vwadd_wv_i16 (a : List (BitVec 16)) (b : List (BitVec 8))
    (h : a.length = b.length := by simp) : List (BitVec 16) :=
  lanewiseBin (fun x y => BVBinOp.add.eval x (BVExtOp.sExt.eval 16 y)) a b h

def vwadd_wv_i32 (a : List (BitVec 32)) (b : List (BitVec 16))
    (h : a.length = b.length := by simp) : List (BitVec 32) :=
  lanewiseBin (fun x y => BVBinOp.add.eval x (BVExtOp.sExt.eval 32 y)) a b h

-- vwmul: signed widening multiply (both operands sign-extended, then multiplied).
def vwmul_vv_i32 (a b : List (BitVec 16))
    (h : a.length = b.length := by simp) : List (BitVec 32) :=
  lanewiseBin
    (fun x y => BVBinOp.mul.eval (BVExtOp.sExt.eval 32 x) (BVExtOp.sExt.eval 32 y))
    a b h

def vwmul_vx_i32 (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 32) :=
  lanewise
    (fun x => BVBinOp.mul.eval (BVExtOp.sExt.eval 32 x) (BVExtOp.sExt.eval 32 scalar))
    a

-- vwmacc: widening multiply-accumulate. acc (wide) += sext(a) * sext(b).
def vwmacc_vv_i32 (acc : List (BitVec 32)) (a b : List (BitVec 16))
    (hab : a.length = b.length := by simp)
    (hacc : acc.length = a.length := by simp) : List (BitVec 32) :=
  lanewiseBin BVBinOp.add.eval acc (vwmul_vv_i32 a b hab)
    (by simpa [vwmul_vv_i32, List.length_zipWith, hab] using hacc)

def vwmacc_vx_i32 (acc : List (BitVec 32)) (scalar : BitVec 16)
    (b : List (BitVec 16))
    (hacc : acc.length = b.length := by simp) : List (BitVec 32) :=
  lanewiseBin BVBinOp.add.eval acc (vwmul_vx_i32 b scalar)
    (by simpa [vwmul_vx_i32, List.length_map] using hacc)

-- vwcvt_x_x_v: widening sign-extend with no arithmetic. Same as vsext.
def vwcvt_x_x_v_i16 (a : List (BitVec 8)) : List (BitVec 16) :=
  lanewise (BVExtOp.sExt.eval 16) a

def vwcvt_x_x_v_i32 (a : List (BitVec 16)) : List (BitVec 32) :=
  lanewise (BVExtOp.sExt.eval 32) a

-- Section 8. Sign extension (vsext): vf2 widens by 2, vf4 by 4.

def vsext_vf2_i16 (a : List (BitVec 8)) : List (BitVec 16) :=
  lanewise (BVExtOp.sExt.eval 16) a

-- 16 → 32 widening.
def vsext_vf2 (a : List (BitVec 16)) : List (BitVec 32) :=
  lanewise (BVExtOp.sExt.eval 32) a

def vsext_vf4_i32 (a : List (BitVec 8)) : List (BitVec 32) :=
  lanewise (BVExtOp.sExt.eval 32) a

-- Section 9. Narrowing. vnclip_wx = rounding-shift-then-saturating-narrow,
-- vnsra_wx = arithmetic-shift-then-truncate, vncvt_x_x_w = plain truncate.

-- vnclip_wx at vxrm=RNU, shift=0: pure signed saturating narrow.
def vnclip_wx_i16 (a : List (BitVec 32)) : List (BitVec 16) :=
  lanewise (BVNarrowOp.sSatNarrow.eval 16) a

def vnclip_wx_i8 (a : List (BitVec 16)) : List (BitVec 8) :=
  lanewise (BVNarrowOp.sSatNarrow.eval 8) a

-- vnsra_wx: arithmetic shift right, then truncate.
def vnsra_wx_i16 (a : List (BitVec 32)) (shift : Nat) : List (BitVec 16) :=
  lanewise (fun x => (BVShiftOp.ashr.eval x shift).truncate 16) a

def vnsra_wx_i8 (a : List (BitVec 16)) (shift : Nat) : List (BitVec 8) :=
  lanewise (fun x => (BVShiftOp.ashr.eval x shift).truncate 8) a

-- vncvt_x_x_w: narrow by truncating the low bits.
def vncvt_x_x_w_i16 (a : List (BitVec 32)) : List (BitVec 16) :=
  lanewise (fun x => x.truncate 16) a

def vncvt_x_x_w_i8 (a : List (BitVec 16)) : List (BitVec 8) :=
  lanewise (fun x => x.truncate 8) a

-- Section 10. Broadcast (vmv_v_x): length-vl vector with every lane = scalar.

def vmv_v_x_i8 (scalar : BitVec 8) (vl : Nat) : List (BitVec 8) :=
  broadcast scalar vl

def vmv_v_x_i16 (scalar : BitVec 16) (vl : Nat) : List (BitVec 16) :=
  broadcast scalar vl

def vmv_v_x (scalar : BitVec 32) (vl : Nat) : List (BitVec 32) :=
  broadcast scalar vl

-- Section 11. vmul_vx = lanewise multiply by scalar; vmacc_vx = dest += scalar * src.

def vmul_vx (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  lanewiseBin BVBinOp.mul.eval a (broadcast scalar a.length)

def vmacc_vx (dest : List (BitVec 32)) (scalar : BitVec 32) (src : List (BitVec 32))
    (h : dest.length = src.length := by simp) : List (BitVec 32) :=
  lanewiseBin BVBinOp.add.eval dest
    (lanewiseBin BVBinOp.mul.eval src (broadcast scalar src.length))
    (by simpa [broadcast, List.length_zipWith, List.length_replicate] using h)

-- Section 12. Reductions. Fold the vector into the scalar accumulator init;
-- result is a 1-lane vector (RVV writes lane 0). vwredsum sign-extends each
-- source lane into the wider accumulator width before adding.

def vredsum_vs_i32 (src : List (BitVec 32)) (init : BitVec 32) : List (BitVec 32) :=
  [src.foldl (fun acc x => BVBinOp.add.eval acc x) init]

def vwredsum_vs_i32 (src : List (BitVec 16)) (init : BitVec 32) : List (BitVec 32) :=
  [src.foldl (fun acc x => BVBinOp.add.eval acc (BVExtOp.sExt.eval 32 x)) init]

def vwredsum_vs_i16 (src : List (BitVec 8)) (init : BitVec 16) : List (BitVec 16) :=
  [src.foldl (fun acc x => BVBinOp.add.eval acc (BVExtOp.sExt.eval 16 x)) init]

-- Length lemmas (@[simp]) for closing call-site length obligations.

section Lengths

-- Section 1: arithmetic

@[simp] theorem length_vadd_vv_i8 (a b : List (BitVec 8))
    {h : a.length = b.length} : (vadd_vv_i8 a b h).length = a.length := by
  simp [vadd_vv_i8, List.length_zipWith, h]

@[simp] theorem length_vadd_vv_i16 (a b : List (BitVec 16))
    {h : a.length = b.length} : (vadd_vv_i16 a b h).length = a.length := by
  simp [vadd_vv_i16, List.length_zipWith, h]

@[simp] theorem length_vadd_vv_i32 (a b : List (BitVec 32))
    {h : a.length = b.length} : (vadd_vv_i32 a b h).length = a.length := by
  simp [vadd_vv_i32, List.length_zipWith, h]

@[simp] theorem length_vadd_vx_i8 (a : List (BitVec 8)) (s : BitVec 8) :
    (vadd_vx_i8 a s).length = a.length := by
  simp [vadd_vx_i8, List.length_zipWith, broadcast]

@[simp] theorem length_vadd_vx_i16 (a : List (BitVec 16)) (s : BitVec 16) :
    (vadd_vx_i16 a s).length = a.length := by
  simp [vadd_vx_i16, List.length_zipWith, broadcast]

@[simp] theorem length_vadd_vx_i32 (a : List (BitVec 32)) (s : BitVec 32) :
    (vadd_vx_i32 a s).length = a.length := by
  simp [vadd_vx_i32, List.length_zipWith, broadcast]

@[simp] theorem length_vsub_vv_i8 (a b : List (BitVec 8))
    {h : a.length = b.length} : (vsub_vv_i8 a b h).length = a.length := by
  simp [vsub_vv_i8, List.length_zipWith, h]

@[simp] theorem length_vsub_vv_i16 (a b : List (BitVec 16))
    {h : a.length = b.length} : (vsub_vv_i16 a b h).length = a.length := by
  simp [vsub_vv_i16, List.length_zipWith, h]

@[simp] theorem length_vsub_vv_i32 (a b : List (BitVec 32))
    {h : a.length = b.length} : (vsub_vv_i32 a b h).length = a.length := by
  simp [vsub_vv_i32, List.length_zipWith, h]

@[simp] theorem length_vsub_vx_i8 (a : List (BitVec 8)) (s : BitVec 8) :
    (vsub_vx_i8 a s).length = a.length := by
  simp [vsub_vx_i8, List.length_zipWith, broadcast]

@[simp] theorem length_vsub_vx_i16 (a : List (BitVec 16)) (s : BitVec 16) :
    (vsub_vx_i16 a s).length = a.length := by
  simp [vsub_vx_i16, List.length_zipWith, broadcast]

@[simp] theorem length_vsub_vx_i32 (a : List (BitVec 32)) (s : BitVec 32) :
    (vsub_vx_i32 a s).length = a.length := by
  simp [vsub_vx_i32, List.length_zipWith, broadcast]

@[simp] theorem length_vrsub_vx_i8 (a : List (BitVec 8)) (s : BitVec 8) :
    (vrsub_vx_i8 a s).length = a.length := by simp [vrsub_vx_i8]

@[simp] theorem length_vrsub_vx_i16 (a : List (BitVec 16)) (s : BitVec 16) :
    (vrsub_vx_i16 a s).length = a.length := by simp [vrsub_vx_i16]

@[simp] theorem length_vrsub_vx_i32 (a : List (BitVec 32)) (s : BitVec 32) :
    (vrsub_vx_i32 a s).length = a.length := by simp [vrsub_vx_i32]

@[simp] theorem length_vmul_vv_i32 (a b : List (BitVec 32))
    {h : a.length = b.length} : (vmul_vv_i32 a b h).length = a.length := by
  simp [vmul_vv_i32, List.length_zipWith, h]

-- Section 2: bitwise

@[simp] theorem length_vand_vv_i8 (a b : List (BitVec 8))
    {h : a.length = b.length} : (vand_vv_i8 a b h).length = a.length := by
  simp [vand_vv_i8, List.length_zipWith, h]

@[simp] theorem length_vand_vv_i32 (a b : List (BitVec 32))
    {h : a.length = b.length} : (vand_vv_i32 a b h).length = a.length := by
  simp [vand_vv_i32, List.length_zipWith, h]

@[simp] theorem length_vand_vx_i8 (a : List (BitVec 8)) (s : BitVec 8) :
    (vand_vx_i8 a s).length = a.length := by
  simp [vand_vx_i8, List.length_zipWith, broadcast]

@[simp] theorem length_vand_vx_i16 (a : List (BitVec 16)) (s : BitVec 16) :
    (vand_vx_i16 a s).length = a.length := by
  simp [vand_vx_i16, List.length_zipWith, broadcast]

@[simp] theorem length_vand_vx_i32 (a : List (BitVec 32)) (s : BitVec 32) :
    (vand_vx_i32 a s).length = a.length := by
  simp [vand_vx_i32, List.length_zipWith, broadcast]

@[simp] theorem length_vor_vv_i8 (a b : List (BitVec 8))
    {h : a.length = b.length} : (vor_vv_i8 a b h).length = a.length := by
  simp [vor_vv_i8, List.length_zipWith, h]

@[simp] theorem length_vor_vx_i8 (a : List (BitVec 8)) (s : BitVec 8) :
    (vor_vx_i8 a s).length = a.length := by
  simp [vor_vx_i8, List.length_zipWith, broadcast]

@[simp] theorem length_vxor_vv_i8 (a b : List (BitVec 8))
    {h : a.length = b.length} : (vxor_vv_i8 a b h).length = a.length := by
  simp [vxor_vv_i8, List.length_zipWith, h]

@[simp] theorem length_vxor_vx_i8 (a : List (BitVec 8)) (s : BitVec 8) :
    (vxor_vx_i8 a s).length = a.length := by
  simp [vxor_vx_i8, List.length_zipWith, broadcast]

-- Section 3: shifts

@[simp] theorem length_vsll_vx_i8 (a : List (BitVec 8)) (s : Nat) :
    (vsll_vx_i8 a s).length = a.length := by simp [vsll_vx_i8]

@[simp] theorem length_vsll_vx_i16 (a : List (BitVec 16)) (s : Nat) :
    (vsll_vx_i16 a s).length = a.length := by simp [vsll_vx_i16]

@[simp] theorem length_vsll_vx_i32 (a : List (BitVec 32)) (s : Nat) :
    (vsll_vx_i32 a s).length = a.length := by simp [vsll_vx_i32]

@[simp] theorem length_vsll_vx_i32m8 (a : List (BitVec 32)) (s : Nat) :
    (vsll_vx_i32m8 a s).length = a.length := by simp [vsll_vx_i32m8]

@[simp] theorem length_vsra_vx_i16 (a : List (BitVec 16)) (s : Nat) :
    (vsra_vx_i16 a s).length = a.length := by simp [vsra_vx_i16]

@[simp] theorem length_vsra_vx_i32 (a : List (BitVec 32)) (s : Nat) :
    (vsra_vx_i32 a s).length = a.length := by simp [vsra_vx_i32]

@[simp] theorem length_vsrl_vx_u8 (a : List (BitVec 8)) (s : Nat) :
    (vsrl_vx_u8 a s).length = a.length := by simp [vsrl_vx_u8]

@[simp] theorem length_vsrl_vx_u16 (a : List (BitVec 16)) (s : Nat) :
    (vsrl_vx_u16 a s).length = a.length := by simp [vsrl_vx_u16]

@[simp] theorem length_vsrl_vx_u32 (a : List (BitVec 32)) (s : Nat) :
    (vsrl_vx_u32 a s).length = a.length := by simp [vsrl_vx_u32]

-- Section 4: rounding shift

@[simp] theorem length_vssra_vx_rnu (a : List (BitVec 32)) (s : Nat) :
    (vssra_vx_rnu a s).length = a.length := by simp [vssra_vx_rnu]

@[simp] theorem length_vssra_vx_rnu_i16 (a : List (BitVec 16)) (s : Nat) :
    (vssra_vx_rnu_i16 a s).length = a.length := by simp [vssra_vx_rnu_i16]

@[simp] theorem length_vssra_vx_rnu_i8 (a : List (BitVec 8)) (s : Nat) :
    (vssra_vx_rnu_i8 a s).length = a.length := by simp [vssra_vx_rnu_i8]

-- Section 5: min / max

@[simp] theorem length_vmax_vx (a : List (BitVec 8)) (s : BitVec 8) :
    (vmax_vx a s).length = a.length := by
  simp [vmax_vx, List.length_zipWith, broadcast]

@[simp] theorem length_vmax_vx_i16 (a : List (BitVec 16)) (s : BitVec 16) :
    (vmax_vx_i16 a s).length = a.length := by
  simp [vmax_vx_i16, List.length_zipWith, broadcast]

@[simp] theorem length_vmax_vx_i32 (a : List (BitVec 32)) (s : BitVec 32) :
    (vmax_vx_i32 a s).length = a.length := by
  simp [vmax_vx_i32, List.length_zipWith, broadcast]

@[simp] theorem length_vmin_vx (a : List (BitVec 8)) (s : BitVec 8) :
    (vmin_vx a s).length = a.length := by
  simp [vmin_vx, List.length_zipWith, broadcast]

@[simp] theorem length_vmin_vx_i16 (a : List (BitVec 16)) (s : BitVec 16) :
    (vmin_vx_i16 a s).length = a.length := by
  simp [vmin_vx_i16, List.length_zipWith, broadcast]

@[simp] theorem length_vmin_vx_i32 (a : List (BitVec 32)) (s : BitVec 32) :
    (vmin_vx_i32 a s).length = a.length := by
  simp [vmin_vx_i32, List.length_zipWith, broadcast]

@[simp] theorem length_vmax_vv_i32 (a b : List (BitVec 32))
    {h : a.length = b.length} : (vmax_vv_i32 a b h).length = a.length := by
  simp [vmax_vv_i32, List.length_zipWith, h]

@[simp] theorem length_vmin_vv_i32 (a b : List (BitVec 32))
    {h : a.length = b.length} : (vmin_vv_i32 a b h).length = a.length := by
  simp [vmin_vv_i32, List.length_zipWith, h]

-- Section 6: saturating add

@[simp] theorem length_vsadd_vx (a : List (BitVec 16)) (s : BitVec 16) :
    (vsadd_vx a s).length = a.length := by
  simp [vsadd_vx, List.length_zipWith, broadcast]

@[simp] theorem length_vsadd_vx_i8 (a : List (BitVec 8)) (s : BitVec 8) :
    (vsadd_vx_i8 a s).length = a.length := by
  simp [vsadd_vx_i8, List.length_zipWith, broadcast]

@[simp] theorem length_vsadd_vx_i32 (a : List (BitVec 32)) (s : BitVec 32) :
    (vsadd_vx_i32 a s).length = a.length := by
  simp [vsadd_vx_i32, List.length_zipWith, broadcast]

@[simp] theorem length_vsadd_vv_i8 (a b : List (BitVec 8))
    {h : a.length = b.length} : (vsadd_vv_i8 a b h).length = a.length := by
  simp [vsadd_vv_i8, List.length_zipWith, h]

@[simp] theorem length_vsadd_vv_i16 (a b : List (BitVec 16))
    {h : a.length = b.length} : (vsadd_vv_i16 a b h).length = a.length := by
  simp [vsadd_vv_i16, List.length_zipWith, h]

@[simp] theorem length_vsadd_vv_i32 (a b : List (BitVec 32))
    {h : a.length = b.length} : (vsadd_vv_i32 a b h).length = a.length := by
  simp [vsadd_vv_i32, List.length_zipWith, h]

-- Section 7: widening

@[simp] theorem length_vwsub_vx (a : List (BitVec 8)) (s : BitVec 8) :
    (vwsub_vx a s).length = a.length := by simp [vwsub_vx]

@[simp] theorem length_vwsub_vx_i32 (a : List (BitVec 16)) (s : BitVec 16) :
    (vwsub_vx_i32 a s).length = a.length := by simp [vwsub_vx_i32]

@[simp] theorem length_vwsub_vv_i16 (a b : List (BitVec 8))
    {h : a.length = b.length} : (vwsub_vv_i16 a b h).length = a.length := by
  simp [vwsub_vv_i16, List.length_zipWith, h]

@[simp] theorem length_vwsub_vv_i32 (a b : List (BitVec 16))
    {h : a.length = b.length} : (vwsub_vv_i32 a b h).length = a.length := by
  simp [vwsub_vv_i32, List.length_zipWith, h]

@[simp] theorem length_vwadd_vv_i16 (a b : List (BitVec 8))
    {h : a.length = b.length} : (vwadd_vv_i16 a b h).length = a.length := by
  simp [vwadd_vv_i16, List.length_zipWith, h]

@[simp] theorem length_vwadd_vv_i32 (a b : List (BitVec 16))
    {h : a.length = b.length} : (vwadd_vv_i32 a b h).length = a.length := by
  simp [vwadd_vv_i32, List.length_zipWith, h]

@[simp] theorem length_vwadd_vx_i16 (a : List (BitVec 8)) (s : BitVec 8) :
    (vwadd_vx_i16 a s).length = a.length := by simp [vwadd_vx_i16]

@[simp] theorem length_vwadd_vx_i32 (a : List (BitVec 16)) (s : BitVec 16) :
    (vwadd_vx_i32 a s).length = a.length := by simp [vwadd_vx_i32]

@[simp] theorem length_vwadd_wv_i16 (a : List (BitVec 16)) (b : List (BitVec 8))
    {h : a.length = b.length} : (vwadd_wv_i16 a b h).length = a.length := by
  simp [vwadd_wv_i16, List.length_zipWith, h]

@[simp] theorem length_vwadd_wv_i32 (a : List (BitVec 32)) (b : List (BitVec 16))
    {h : a.length = b.length} : (vwadd_wv_i32 a b h).length = a.length := by
  simp [vwadd_wv_i32, List.length_zipWith, h]

@[simp] theorem length_vwmul_vv_i32 (a b : List (BitVec 16))
    {h : a.length = b.length} : (vwmul_vv_i32 a b h).length = a.length := by
  simp [vwmul_vv_i32, List.length_zipWith, h]

@[simp] theorem length_vwmul_vx_i32 (a : List (BitVec 16)) (s : BitVec 16) :
    (vwmul_vx_i32 a s).length = a.length := by simp [vwmul_vx_i32]

@[simp] theorem length_vwmacc_vv_i32 (acc : List (BitVec 32))
    (a b : List (BitVec 16)) {hab : a.length = b.length}
    {hacc : acc.length = a.length} :
    (vwmacc_vv_i32 acc a b hab hacc).length = acc.length := by
  simp [vwmacc_vv_i32, List.length_zipWith, hacc]

@[simp] theorem length_vwmacc_vx_i32 (acc : List (BitVec 32)) (s : BitVec 16)
    (b : List (BitVec 16)) {hacc : acc.length = b.length} :
    (vwmacc_vx_i32 acc s b hacc).length = acc.length := by
  simp [vwmacc_vx_i32, List.length_zipWith, hacc]

@[simp] theorem length_vwcvt_x_x_v_i16 (a : List (BitVec 8)) :
    (vwcvt_x_x_v_i16 a).length = a.length := by simp [vwcvt_x_x_v_i16]

@[simp] theorem length_vwcvt_x_x_v_i32 (a : List (BitVec 16)) :
    (vwcvt_x_x_v_i32 a).length = a.length := by simp [vwcvt_x_x_v_i32]

-- Section 8: sign extend

@[simp] theorem length_vsext_vf2_i16 (a : List (BitVec 8)) :
    (vsext_vf2_i16 a).length = a.length := by simp [vsext_vf2_i16]

@[simp] theorem length_vsext_vf2 (a : List (BitVec 16)) :
    (vsext_vf2 a).length = a.length := by simp [vsext_vf2]

@[simp] theorem length_vsext_vf4_i32 (a : List (BitVec 8)) :
    (vsext_vf4_i32 a).length = a.length := by simp [vsext_vf4_i32]

-- Section 9: narrowing

@[simp] theorem length_vnclip_wx_i16 (a : List (BitVec 32)) :
    (vnclip_wx_i16 a).length = a.length := by simp [vnclip_wx_i16]

@[simp] theorem length_vnclip_wx_i8 (a : List (BitVec 16)) :
    (vnclip_wx_i8 a).length = a.length := by simp [vnclip_wx_i8]

@[simp] theorem length_vnsra_wx_i16 (a : List (BitVec 32)) (s : Nat) :
    (vnsra_wx_i16 a s).length = a.length := by simp [vnsra_wx_i16]

@[simp] theorem length_vnsra_wx_i8 (a : List (BitVec 16)) (s : Nat) :
    (vnsra_wx_i8 a s).length = a.length := by simp [vnsra_wx_i8]

@[simp] theorem length_vncvt_x_x_w_i16 (a : List (BitVec 32)) :
    (vncvt_x_x_w_i16 a).length = a.length := by simp [vncvt_x_x_w_i16]

@[simp] theorem length_vncvt_x_x_w_i8 (a : List (BitVec 16)) :
    (vncvt_x_x_w_i8 a).length = a.length := by simp [vncvt_x_x_w_i8]

-- Section 10: broadcast

@[simp] theorem length_vmv_v_x_i8 (s : BitVec 8) (vl : Nat) :
    (vmv_v_x_i8 s vl).length = vl := by simp [vmv_v_x_i8, broadcast]

@[simp] theorem length_vmv_v_x_i16 (s : BitVec 16) (vl : Nat) :
    (vmv_v_x_i16 s vl).length = vl := by simp [vmv_v_x_i16, broadcast]

@[simp] theorem length_vmv_v_x (s : BitVec 32) (vl : Nat) :
    (vmv_v_x s vl).length = vl := by simp [vmv_v_x, broadcast]

-- Section 11: multiply

@[simp] theorem length_vmul_vx (a : List (BitVec 32)) (s : BitVec 32) :
    (vmul_vx a s).length = a.length := by
  simp [vmul_vx, List.length_zipWith, broadcast]

@[simp] theorem length_vmacc_vx (dest : List (BitVec 32)) (s : BitVec 32)
    (src : List (BitVec 32)) {h : dest.length = src.length} :
    (vmacc_vx dest s src h).length = dest.length := by
  simp [vmacc_vx, List.length_zipWith, broadcast, h]

-- Section 12: reductions

@[simp] theorem length_vredsum_vs_i32 (src : List (BitVec 32)) (init : BitVec 32) :
    (vredsum_vs_i32 src init).length = 1 := by simp [vredsum_vs_i32]

@[simp] theorem length_vwredsum_vs_i32 (src : List (BitVec 16)) (init : BitVec 32) :
    (vwredsum_vs_i32 src init).length = 1 := by simp [vwredsum_vs_i32]

@[simp] theorem length_vwredsum_vs_i16 (src : List (BitVec 8)) (init : BitVec 16) :
    (vwredsum_vs_i16 src init).length = 1 := by simp [vwredsum_vs_i16]

end Lengths

end SALT.Intrinsics.RVV
