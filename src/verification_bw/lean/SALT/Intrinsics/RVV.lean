import SALT.Basic

namespace SALT.Intrinsics.RVV

open SALT

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
