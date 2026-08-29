import SALT.Basic
import SALT.Intrinsics.FP32

namespace SALT.Intrinsics.Neon

open SALT

/-- Binary32 lane operations used by the FP elementwise compiler. The separate
    architecture wrapper is retained so generated Neon and RVV models do not
    share an intrinsic symbol. -/
def vaddq_f32 (a b : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith FP32.add a b

def vsubq_f32 (a b : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith FP32.sub a b

def vmulq_f32 (a b : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith FP32.mul a b

def vdivq_f32 (a b : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith FP32.div a b

def vsqrtq_f32 (a : List (BitVec 32)) : List (BitVec 32) :=
  a.map FP32.sqrt

def vabsq_f32 (a : List (BitVec 32)) : List (BitVec 32) :=
  a.map FP32.abs

def vcltq_s32 (a b : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith
    (fun left right =>
      if left.toInt < right.toInt then BitVec.allOnes 32 else BitVec.ofNat 32 0)
    a b

def vbslq_f32 (mask onTrue onFalse : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith
    (fun select values => (select &&& values.1) ||| ((~~~select) &&& values.2))
    mask (List.zip onTrue onFalse)

def vcaltq_f32 (left right : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith
    (fun x y =>
      if FP32.lt (FP32.abs x) (FP32.abs y) then
        BitVec.allOnes 32
      else BitVec.ofNat 32 0)
    left right

def vorrq_u32 (left right : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith (· ||| ·) left right

def vaddw_s8 (wide : List (BitVec 16))
    (narrow : List (BitVec 8)) : List (BitVec 16) :=
  List.zipWith (fun left right => left + sext right 16) wide narrow

def vaddw_u8 (wide : List (BitVec 16))
    (narrow : List (BitVec 8)) : List (BitVec 16) :=
  List.zipWith (fun left right => left + right.zeroExtend 16) wide narrow

def vcvtq_f32_s32 (value : List (BitVec 32)) : List (BitVec 32) :=
  value.map FP32.ofInt32

def vreinterpretq_u16_s16 (value : List (BitVec 16)) : List (BitVec 16) :=
  value

def vadd_u32 (left right : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith (· + ·) left right

def vand_u32 (left right : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith (· &&& ·) left right

def vcgt_u32 (left right : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith
    (fun x y => if x.toNat > y.toNat then BitVec.allOnes 32 else 0)
    left right

def vmax_u32 (left right : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith (fun x y => if x.toNat >= y.toNat then x else y) left right

def vmovn_u32 (value : List (BitVec 32)) : List (BitVec 16) :=
  value.map (·.truncate 16)

def vshrn_n_u32 (value : List (BitVec 32)) (shift : Nat) : List (BitVec 16) :=
  value.map (fun lane => (lane.ushiftRight shift).truncate 16)

def vadd_u16 (left right : List (BitVec 16)) : List (BitVec 16) :=
  List.zipWith (· + ·) left right

def vand_u16 (left right : List (BitVec 16)) : List (BitVec 16) :=
  List.zipWith (· &&& ·) left right

def vbsl_u16 (mask onTrue onFalse : List (BitVec 16)) : List (BitVec 16) :=
  List.zipWith
    (fun select values => (select &&& values.1) ||| ((~~~select) &&& values.2))
    mask (List.zip onTrue onFalse)

def vorr_u16 (left right : List (BitVec 16)) : List (BitVec 16) :=
  List.zipWith (· ||| ·) left right

def vmaxq_f32 (left right : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith FP32.maxPropagatingNaN left right

def vminq_f32 (left right : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith FP32.minPropagatingNaN left right

/-- Signed 16-bit lane multiplication widened to a signed 32-bit result. -/
def vmull_s16 (left right : List (BitVec 16)) : List (BitVec 32) :=
  List.zipWith (fun x y => BitVec.ofInt 32 (x.toInt * y.toInt)) left right

/-- Insert a saturated 32-to-16 high half after an existing 16-bit low half. -/
def vqmovn_high_s32 (low : List (BitVec 16))
    (high : List (BitVec 32)) : List (BitVec 16) :=
  low ++ high.map (fun lane => signedClamp lane 16)

/-- Signed saturating subtraction on 32-bit lanes. -/
def vqsubq_s32 (left right : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith signedSatSub left right

-- ============================================================================
-- vsubl_s8: Signed subtract long (8→16 bit)
-- result[i] = sext16(a[i]) - sext16(b[i])
-- ============================================================================
def vsubl_s8 (a b : List (BitVec 8)) : List (BitVec 16) :=
  List.zipWith (fun x y => (sext x 16) - (sext y 16)) a b

-- ============================================================================
-- vmovl_s16: Signed move long (16→32 bit)
-- result[i] = sext32(a[i])
-- ============================================================================
def vmovl_s16 (a : List (BitVec 16)) : List (BitVec 32) :=
  a.map (fun x => sext x 32)

-- ============================================================================
-- vmulq_s32: Multiply by scalar (32-bit)
-- result[i] = a[i] * scalar
-- ============================================================================
def vmulq_s32 (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  a.map (fun x => x * scalar)

-- ============================================================================
-- vmlaq_s32: Multiply-accumulate (32-bit)
-- result[i] = acc[i] + b[i] * c
-- ============================================================================
def vmlaq_s32 (acc b : List (BitVec 32)) (c : BitVec 32) : List (BitVec 32) :=
  List.zipWith (fun a x => a + x * c) acc b

-- ============================================================================
-- vrshlq_s32: Rounding shift right (NEON-specific)
-- ============================================================================

def neonRoundingShiftRight (x : BitVec 32) (shift : Nat) : BitVec 32 :=
  if shift = 0 then x
  else
    let wide : BitVec 64 := x.signExtend 64
    let round_const : BitVec 64 := BitVec.ofNat 64 (1 <<< (shift - 1))
    let rounded : BitVec 64 := wide + round_const
    (rounded.sshiftRight shift).truncate 32

def vrshlq_s32 (a : List (BitVec 32)) (shift : Nat) : List (BitVec 32) :=
  a.map (fun x => neonRoundingShiftRight x shift)

-- ============================================================================
-- vqmovn_s32: Signed saturating extract narrow (32→16 bit)
-- result[i] = signedClamp(a[i], 16)
-- ============================================================================
def vqmovn_s32 (a : List (BitVec 32)) : List (BitVec 16) :=
  a.map (fun x => signedClamp x 16)

-- ============================================================================
-- vqmovn_s16: Signed saturating extract narrow (16→8 bit)
-- result[i] = signedClamp(a[i], 8)
-- ============================================================================
def vqmovn_s16 (a : List (BitVec 16)) : List (BitVec 8) :=
  a.map (fun x => signedClamp x 8)

-- ============================================================================
-- vqaddq_s16: Signed saturating add (16-bit)
-- result[i] = signedSatAdd(a[i], scalar)
-- ============================================================================
def vqaddq_s16 (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 16) :=
  a.map (fun x => signedSatAdd x scalar)

-- ============================================================================
-- vmax_s8 / vmin_s8: Signed element-wise max/min (8-bit)
-- ============================================================================
def vmax_s8 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  a.map (fun x => bvSignedMax x scalar)

def vmin_s8 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  a.map (fun x => bvSignedMin x scalar)

-- ============================================================================
-- Additional integer intrinsics used by the current element-wise kernels
-- ============================================================================

/-- Signed vector-vector maximum. Unlike the legacy scalar-normalized `vmax_s8`,
    this preserves both vector operands from `vmaxq_s8`. -/
def vmaxq_s8 (a b : List (BitVec 8)) : List (BitVec 8) :=
  List.zipWith bvSignedMax a b

/-- Signed vector-vector minimum for `vminq_s8`. -/
def vminq_s8 (a b : List (BitVec 8)) : List (BitVec 8) :=
  List.zipWith bvSignedMin a b

/-- Signed vector-vector maximum for the 64-bit `vmax_s8` register form. -/
def vmax_s8_vec (a b : List (BitVec 8)) : List (BitVec 8) :=
  List.zipWith bvSignedMax a b

/-- Signed vector-vector minimum for the 64-bit `vmin_s8` register form. -/
def vmin_s8_vec (a b : List (BitVec 8)) : List (BitVec 8) :=
  List.zipWith bvSignedMin a b

/-- Widen the signed byte operand and subtract it from a signed 16-bit lane. -/
def vsubw_s8 (a : List (BitVec 16)) (b : List (BitVec 8)) : List (BitVec 16) :=
  List.zipWith (fun x y => x - sext y 16) a b

/-- Non-saturating immediate left shift of signed 16-bit lanes. -/
def vshlq_n_s16 (a : List (BitVec 16)) (shift : Nat) : List (BitVec 16) :=
  a.map (fun x => x.shiftLeft shift)

/-- Scalar semantics of signed saturating rounding doubling multiply-high on
    16-bit lanes. The doubled product is computed in `Int`, so the unique
    saturating case `(-32768) * (-32768)` is not lost to a 32-bit wraparound. -/
def sqrdmulh_s16 (a b : BitVec 16) : BitVec 16 :=
  let doubled : Int := 2 * a.toInt * b.toInt
  let roundedHigh : Int := (doubled + (2 ^ 15 : Int)) >>> 16
  BitVec.ofInt 16 (max (-32768) (min roundedHigh 32767))

/-- Lane-wise `vqrdmulhq_s16`. -/
def vqrdmulhq_s16 (a b : List (BitVec 16)) : List (BitVec 16) :=
  List.zipWith sqrdmulh_s16 a b

/-- Signed less-than comparison. True lanes use the architectural all-ones
    mask representation and false lanes use zero. -/
def vcltq_s16 (a b : List (BitVec 16)) : List (BitVec 16) :=
  List.zipWith
    (fun x y => if x.toInt < y.toInt then BitVec.allOnes 16 else BitVec.ofNat 16 0)
    a b

/-- Bitwise select: a set mask bit selects the corresponding bit from `onTrue`. -/
def vbslq_s16 (mask onTrue onFalse : List (BitVec 16)) : List (BitVec 16) :=
  List.zipWith
    (fun m values => (m &&& values.1) ||| ((~~~m) &&& values.2))
    mask (List.zip onTrue onFalse)

/-- Unsigned widening subtraction. The 16-bit result wraps exactly as the
    destination lane of `vsubl_u8`; a later reinterpretation may view it as signed. -/
def vsubl_u8 (a b : List (BitVec 8)) : List (BitVec 16) :=
  List.zipWith (fun x y => x.zeroExtend 16 - y.zeroExtend 16) a b

/-- Signed-to-unsigned saturating narrow from 16 to 8 bits. -/
def vqmovun_s16 (a : List (BitVec 16)) : List (BitVec 8) :=
  a.map (fun x => BitVec.ofInt 8 (max 0 (min x.toInt 255)))

/-- Unsigned vector-vector maximum. -/
def vmax_u8 (a b : List (BitVec 8)) : List (BitVec 8) :=
  List.zipWith (fun x y => if x.toNat >= y.toNat then x else y) a b

/-- Unsigned vector-vector minimum. -/
def vmin_u8 (a b : List (BitVec 8)) : List (BitVec 8) :=
  List.zipWith (fun x y => if x.toNat <= y.toNat then x else y) a b

/-- Unsigned 128-bit register aliases have the same lane semantics. -/
def vmaxq_u8 (a b : List (BitVec 8)) : List (BitVec 8) :=
  vmax_u8 a b

def vminq_u8 (a b : List (BitVec 8)) : List (BitVec 8) :=
  vmin_u8 a b

/-- Reinterpretation changes only the signed view, not the stored bits. -/
def vreinterpretq_s16_u16 (a : List (BitVec 16)) : List (BitVec 16) :=
  a

/-- Per-lane signed shift for the vector-count form of `vrshlq_s32`.
    Current kernels supply normalized counts in the signed low byte. -/
def vrshlq_s32_vec (a shifts : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith
    (fun x rawShift =>
      let shift : Int := (rawShift.truncate 8).toInt
      if shift < 0 then neonRoundingShiftRight x (-shift).toNat
      else x.shiftLeft shift.toNat)
    a shifts

end SALT.Intrinsics.Neon
