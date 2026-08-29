import SALT.Basic
import SALT.Intrinsics.FP32

namespace SALT.Intrinsics.RVV

open SALT

/-- RVV wrappers deliberately remain distinct from the Neon wrappers while both
    refer to the same binary32 value operation at claim layer 1. -/
def vfadd_vv_f32 (a b : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith FP32.add a b

def vfsub_vv_f32 (a b : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith FP32.sub a b

def vfmul_vv_f32 (a b : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith FP32.mul a b

def vfmul_vf_f32 (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  a.map (fun value => FP32.mul value scalar)

def vfdiv_vv_f32 (a b : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith FP32.div a b

def vfsqrt_v_f32 (a : List (BitVec 32)) : List (BitVec 32) :=
  a.map FP32.sqrt

def vfabs_v_f32 (a : List (BitVec 32)) : List (BitVec 32) :=
  a.map FP32.abs

def vmslt_vx_i32 (a : List (BitVec 32)) (scalar : BitVec 32) : List Bool :=
  a.map (fun value => decide (value.toInt < scalar.toInt))

def vmerge_vvm_f32 (base replacement : List (BitVec 32))
    (mask : List Bool) : List (BitVec 32) :=
  List.zipWith (fun values selected => if selected then values.2 else values.1)
    (List.zip base replacement) mask

def vfadd_vf_f32 (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  a.map (fun value => FP32.add value scalar)

def vfsub_vf_f32 (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  a.map (fun value => FP32.sub value scalar)

def vmfgt_vf_f32 (a : List (BitVec 32)) (scalar : BitVec 32) : List Bool :=
  a.map (fun value => FP32.gt value scalar)

def vmfne_vv_f32 (a b : List (BitVec 32)) : List Bool :=
  List.zipWith FP32.ne a b

def vfsgnj_vv_f32 (magnitude signSource : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith
    (fun value sign => (value &&& 0x7FFFFFFF) ||| (sign &&& 0x80000000))
    magnitude signSource

def vor_vx_u32 (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  a.map (fun value => value ||| scalar)

def vsub_vx_i16 (value : List (BitVec 16))
    (scalar : BitVec 16) : List (BitVec 16) :=
  value.map (fun lane => lane - scalar)

def vadd_vx_u16 (value : List (BitVec 16))
    (scalar : BitVec 16) : List (BitVec 16) :=
  value.map (fun lane => lane + scalar)

def vzext_vf2_u16 (value : List (BitVec 8)) : List (BitVec 16) :=
  value.map (fun lane => lane.zeroExtend 16)

def vfcvt_f_x_v_f32 (value : List (BitVec 32)) : List (BitVec 32) :=
  value.map FP32.ofInt32

def vadd_vx_u32 (value : List (BitVec 32))
    (scalar : BitVec 32) : List (BitVec 32) :=
  value.map (fun lane => lane + scalar)

def vand_vx_u32 (value : List (BitVec 32))
    (scalar : BitVec 32) : List (BitVec 32) :=
  value.map (fun lane => lane &&& scalar)

def vmsgtu_vx_u32 (value : List (BitVec 32)) (scalar : BitVec 32) : List Bool :=
  value.map (fun lane => decide (lane.toNat > scalar.toNat))

def vmaxu_vx_u32 (value : List (BitVec 32))
    (scalar : BitVec 32) : List (BitVec 32) :=
  value.map (fun lane => if lane.toNat >= scalar.toNat then lane else scalar)

def vnsrl_wx_u16 (value : List (BitVec 32)) (shift : Nat) : List (BitVec 16) :=
  value.map (fun lane => (lane.ushiftRight shift).truncate 16)

def vand_vx_u16 (value : List (BitVec 16))
    (scalar : BitVec 16) : List (BitVec 16) :=
  value.map (fun lane => lane &&& scalar)

def vadd_vv_u16 (left right : List (BitVec 16)) : List (BitVec 16) :=
  List.zipWith (· + ·) left right

def vmerge_vxm_u16 (base : List (BitVec 16)) (replacement : BitVec 16)
    (mask : List Bool) : List (BitVec 16) :=
  List.zipWith (fun lane selected => if selected then replacement else lane) base mask

def vor_vv_u16 (left right : List (BitVec 16)) : List (BitVec 16) :=
  List.zipWith (· ||| ·) left right

def vfmax_vv_f32 (left right : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith FP32.maxNumber left right

def vfmin_vv_f32 (left right : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith FP32.minNumber left right

/-- Wrapping vector-scalar addition for signed 32-bit lanes. -/
def vadd_vx_i32 (value : List (BitVec 32))
    (scalar : BitVec 32) : List (BitVec 32) :=
  value.map (fun lane => lane + scalar)

/-- Binary32-to-signed-i32 conversion under the explicit RNE value model. -/
def vfcvt_x_f_v_i32_rne (value : List (BitVec 32)) : List (BitVec 32) :=
  value.map FP32.toInt32RNE

-- ============================================================================
-- vwsub_vx: Widening subtract (8→16 bit)
-- result[i] = sext16(a[i]) - sext16(scalar)
-- ============================================================================
def vwsub_vx (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 16) :=
  a.map (fun x => (sext x 16) - (sext scalar 16))

-- ============================================================================
-- vsext_vf2: Sign extension (16→32 bit)
-- result[i] = sext32(a[i])
-- ============================================================================
def vsext_vf2 (a : List (BitVec 16)) : List (BitVec 32) :=
  a.map (fun x => sext x 32)

-- ============================================================================
-- vmv_v_x: Broadcast scalar to vector
-- result[i] = scalar  (for i in 0..vl-1)
-- ============================================================================
def vmv_v_x (scalar : BitVec 32) (vl : Nat) : List (BitVec 32) :=
  List.replicate vl scalar

-- ============================================================================
-- vmul_vx: Multiply by scalar (32-bit)
-- result[i] = a[i] * scalar
-- ============================================================================
def vmul_vx (a : List (BitVec 32)) (scalar : BitVec 32) : List (BitVec 32) :=
  a.map (fun x => x * scalar)

-- ============================================================================
-- vmacc_vx: Multiply-accumulate (32-bit)
-- result[i] = dest[i] + scalar * src[i]
-- ============================================================================
def vmacc_vx (dest : List (BitVec 32)) (scalar : BitVec 32) (src : List (BitVec 32)) : List (BitVec 32) :=
  List.zipWith (fun d s => d + s * scalar) dest src

-- ============================================================================
-- vssra_vx (vxrm=RNU): Rounding arithmetic shift right (RVV-specific)
-- ============================================================================

def rvvRoundingShiftRight (x : BitVec 32) (shift : Nat) : BitVec 32 :=
  if shift = 0 then x
  else
    let shifted : BitVec 32 := x.sshiftRight shift
    let round_bit : Bool := x.getLsbD (shift - 1)
    if round_bit then shifted + 1 else shifted

def vssra_vx_rnu (a : List (BitVec 32)) (shift : Nat) : List (BitVec 32) :=
  a.map (fun x => rvvRoundingShiftRight x shift)

-- ============================================================================
-- vnclip_wx (vxrm=RNU): Signed narrowing clip (32→16 or 16→8)
-- ============================================================================
def vnclip_wx_i16 (a : List (BitVec 32)) : List (BitVec 16) :=
  a.map (fun x => signedClamp x 16)

def vnclip_wx_i8 (a : List (BitVec 16)) : List (BitVec 8) :=
  a.map (fun x => signedClamp x 8)

-- ============================================================================
-- vsadd_vx: Signed saturating add with scalar (16-bit)
-- result[i] = signedSatAdd(a[i], scalar)
-- ============================================================================
def vsadd_vx (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 16) :=
  a.map (fun x => signedSatAdd x scalar)

-- ============================================================================
-- vmax_vx / vmin_vx: Signed element-wise max/min with scalar
-- ============================================================================
def vmax_vx (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  a.map (fun x => bvSignedMax x scalar)

def vmin_vx (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  a.map (fun x => bvSignedMin x scalar)

-- ============================================================================
-- Explicit fixed-point rounding and narrowing
-- ============================================================================

/-- RISC-V fixed-point rounding modes, matching the architectural `vxrm` encoding. -/
inductive VXRoundingMode where
  | rnu
  | rne
  | rdn
  | rod
  deriving Repr, DecidableEq

/-- Decode the architectural two-bit `vxrm` field from a natural number. -/
def VXRoundingMode.decode (mode : Nat) : VXRoundingMode :=
  match mode % 4 with
  | 0 => .rnu
  | 1 => .rne
  | 2 => .rdn
  | _ => .rod

/-- Whether any of the low `count` source bits are set. -/
def discardedBitsNonzero {width : Nat} (x : BitVec width) (count : Nat) : Bool :=
  x.toNat % (2 ^ count) != 0

/-- Architectural fixed-point rounding increment for an effective shift amount.
    Callers that model a vector instruction are responsible for applying the
    instruction's shift-amount mask before calling this function. -/
def vxrmIncrement {width : Nat} (mode : VXRoundingMode)
    (x : BitVec width) (shift : Nat) : Bool :=
  if shift = 0 then false
  else
    match mode with
    | .rnu => x.getLsbD (shift - 1)
    | .rne =>
        x.getLsbD (shift - 1) &&
          (discardedBitsNonzero x (shift - 1) || x.getLsbD shift)
    | .rdn => false
    | .rod => !x.getLsbD shift && discardedBitsNonzero x shift

/-- Signed arithmetic shift followed by the selected fixed-point rounding increment. -/
def roundShiftSigned {width : Nat} (mode : VXRoundingMode)
    (x : BitVec width) (shift : Nat) : Int :=
  let increment : Int := if vxrmIncrement mode x shift then 1 else 0
  (x.toInt >>> shift) + increment

/-- Unsigned logical shift followed by the selected fixed-point rounding increment. -/
def roundShiftUnsigned {width : Nat} (mode : VXRoundingMode)
    (x : BitVec width) (shift : Nat) : Nat :=
  let increment : Nat := if vxrmIncrement mode x shift then 1 else 0
  x.toNat / (2 ^ shift) + increment

/-- Saturate an unbounded signed integer into a signed bit-vector lane. -/
def saturateSignedInt (width : Nat) (value : Int) : BitVec width :=
  let lo := -(2 ^ (width - 1) : Int)
  let hi := (2 ^ (width - 1) - 1 : Int)
  BitVec.ofInt width (max lo (min value hi))

/-- Saturate an unbounded natural number into an unsigned bit-vector lane. -/
def saturateUnsignedNat (width : Nat) (value : Nat) : BitVec width :=
  BitVec.ofNat width (min value (2 ^ width - 1))

/-- Scalar signed `vnclip`: round first, then saturate into the destination width. -/
def vnclipSigned {sourceWidth : Nat} (destinationWidth : Nat)
    (mode : VXRoundingMode) (shift : Nat) (x : BitVec sourceWidth) :
    BitVec destinationWidth :=
  saturateSignedInt destinationWidth (roundShiftSigned mode x shift)

/-- Scalar unsigned `vnclipu`: round first, then saturate into the destination width. -/
def vnclipUnsigned {sourceWidth : Nat} (destinationWidth : Nat)
    (mode : VXRoundingMode) (shift : Nat) (x : BitVec sourceWidth) :
    BitVec destinationWidth :=
  saturateUnsignedNat destinationWidth (roundShiftUnsigned mode x shift)

/-- Signed 32-to-16 narrowing with explicit shift and numeric `vxrm` operands. -/
def vnclip_wx_i16_mode (a : List (BitVec 32)) (shift mode : Nat) : List (BitVec 16) :=
  a.map (vnclipSigned 16 (VXRoundingMode.decode mode) shift)

/-- Signed 16-to-8 narrowing with explicit shift and numeric `vxrm` operands. -/
def vnclip_wx_i8_mode (a : List (BitVec 16)) (shift mode : Nat) : List (BitVec 8) :=
  a.map (vnclipSigned 8 (VXRoundingMode.decode mode) shift)

/-- Unsigned 16-to-8 narrowing with explicit shift and numeric `vxrm` operands. -/
def vnclipu_wx_u8_mode (a : List (BitVec 16)) (shift mode : Nat) : List (BitVec 8) :=
  a.map (vnclipUnsigned 8 (VXRoundingMode.decode mode) shift)

def vnclip_wx_i16_rnu (a : List (BitVec 32)) (shift : Nat) : List (BitVec 16) :=
  vnclip_wx_i16_mode a shift 0

def vnclip_wx_i16_rdn (a : List (BitVec 32)) (shift : Nat) : List (BitVec 16) :=
  vnclip_wx_i16_mode a shift 2

def vnclip_wx_i8_rnu (a : List (BitVec 16)) (shift : Nat) : List (BitVec 8) :=
  vnclip_wx_i8_mode a shift 0

def vnclip_wx_i8_rdn (a : List (BitVec 16)) (shift : Nat) : List (BitVec 8) :=
  vnclip_wx_i8_mode a shift 2

def vnclipu_wx_u8_rnu (a : List (BitVec 16)) (shift : Nat) : List (BitVec 8) :=
  vnclipu_wx_u8_mode a shift 0

def vnclipu_wx_u8_rdn (a : List (BitVec 16)) (shift : Nat) : List (BitVec 8) :=
  vnclipu_wx_u8_mode a shift 2

-- ============================================================================
-- Additional integer intrinsics used by the current element-wise kernels
-- ============================================================================

/-- Sign extend signed bytes to signed 16-bit lanes. -/
def vsext_vf2_i16 (a : List (BitVec 8)) : List (BitVec 16) :=
  a.map (fun x => sext x 16)

/-- Width-specific alias for the existing signed 16-to-32 extension. -/
def vsext_vf2_i32 (a : List (BitVec 16)) : List (BitVec 32) :=
  vsext_vf2 a

/-- Reverse subtract: `scalar - lane`. -/
def vrsub_vx_i16 (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 16) :=
  a.map (fun x => scalar - x)

/-- Non-saturating vector-scalar left shifts. -/
def vsll_vx_i16 (a : List (BitVec 16)) (shift : Nat) : List (BitVec 16) :=
  a.map (fun x => x.shiftLeft shift)

def vsll_vx_i32 (a : List (BitVec 32)) (shift : Nat) : List (BitVec 32) :=
  a.map (fun x => x.shiftLeft shift)

/-- Signed arithmetic right shift with explicit numeric `vxrm` mode. -/
def vssra_vx_i32_mode (a : List (BitVec 32)) (shift mode : Nat) : List (BitVec 32) :=
  a.map (fun x => BitVec.ofInt 32 (roundShiftSigned (VXRoundingMode.decode mode) x shift))

/-- Signed widening 16-by-16 multiplication into exact 32-bit products. -/
def vwmul_vx_i32 (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 32) :=
  a.map (fun x => BitVec.ofInt 32 (x.toInt * scalar.toInt))

def vwmul_vv_i32 (a b : List (BitVec 16)) : List (BitVec 32) :=
  List.zipWith (fun x y => BitVec.ofInt 32 (x.toInt * y.toInt)) a b

/-- Signed lane comparison against a scalar, represented as a logical predicate vector. -/
def vmslt_vx_i16 (a : List (BitVec 16)) (scalar : BitVec 16) : List Bool :=
  a.map (fun x => decide (x.toInt < scalar.toInt))

def vmv_v_x_i16 (scalar : BitVec 16) (vl : Nat) : List (BitVec 16) :=
  List.replicate vl scalar

/-- `vmerge.vxm`: a true predicate lane selects the scalar, otherwise the base lane. -/
def vmerge_vxm_i16 (base : List (BitVec 16)) (scalar : BitVec 16)
    (mask : List Bool) : List (BitVec 16) :=
  List.zipWith (fun x selected => if selected then scalar else x) base mask

/-- Unsigned widening subtraction from 8-bit lanes into 16-bit lanes. -/
def vwsubu_vx_u16 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 16) :=
  a.map (fun x => x.zeroExtend 16 - scalar.zeroExtend 16)

/-- Reinterpretations preserve lane bits. -/
def vreinterpret_u16_i16 (a : List (BitVec 16)) : List (BitVec 16) :=
  a

def vreinterpret_i16_u16 (a : List (BitVec 16)) : List (BitVec 16) :=
  a

def vmax_vx_i16 (a : List (BitVec 16)) (scalar : BitVec 16) : List (BitVec 16) :=
  a.map (fun x => bvSignedMax x scalar)

def vmaxu_vx_u8 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  a.map (fun x => if x.toNat >= scalar.toNat then x else scalar)

def vminu_vx_u8 (a : List (BitVec 8)) (scalar : BitVec 8) : List (BitVec 8) :=
  a.map (fun x => if x.toNat <= scalar.toNat then x else scalar)

/-- Current QU8 kernels encode a positive value as a right shift and a
    non-positive value as a left shift by its negation. Shift counts are
    expected to be in the instruction's effective range. -/
def vshift_signed_i32_rnu (a : List (BitVec 32))
    (signedShift : BitVec 32) : List (BitVec 32) :=
  if signedShift.toInt > 0 then vssra_vx_i32_mode a signedShift.toNat 0
  else vsll_vx_i32 a (-signedShift).toNat

end SALT.Intrinsics.RVV
