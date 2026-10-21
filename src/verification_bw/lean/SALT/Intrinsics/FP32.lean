import SALT.Basic

namespace SALT.Intrinsics.FP32

/-- Interpret one logical 32-bit lane through Lean's IEEE-754 binary32 primitive. -/
def ofBits (value : BitVec 32) : Float32 :=
  Float32.ofBits (UInt32.ofNat value.toNat)

/-- Return the exact binary32 result bits produced by Lean's primitive. -/
def toBits (value : Float32) : BitVec 32 :=
  value.toBits.toBitVec

/-- True exactly for binary32 NaN encodings. -/
def isNaN (value : BitVec 32) : Bool :=
  (value &&& 0x7F800000) == 0x7F800000 && (value &&& 0x007FFFFF) != 0

/-- True exactly for signaling binary32 NaNs. -/
def isSignalingNaN (value : BitVec 32) : Bool :=
  isNaN value && (value &&& 0x00400000) == 0

def quietNaN (value : BitVec 32) : BitVec 32 :=
  value ||| 0x00400000

def canonicalNaN : BitVec 32 :=
  0x7FC00000

def isInf (value : BitVec 32) : Bool :=
  (value &&& 0x7FFFFFFF) == 0x7F800000

def isZero (value : BitVec 32) : Bool :=
  (value &&& 0x7FFFFFFF) == 0

def signBit (value : BitVec 32) : Bool :=
  value.getLsbD 31

def invalidAdd (left right : BitVec 32) : Bool :=
  isInf left && isInf right && signBit left != signBit right

def invalidSub (left right : BitVec 32) : Bool :=
  isInf left && isInf right && signBit left == signBit right

def invalidMul (left right : BitVec 32) : Bool :=
  (isZero left && isInf right) || (isInf left && isZero right)

def invalidDiv (left right : BitVec 32) : Bool :=
  (isZero left && isZero right) || (isInf left && isInf right)

def invalidSqrt (value : BitVec 32) : Bool :=
  signBit value && !isZero value

/-- Host arithmetic is used only after architecture-specific exceptional cases. -/
private def hostAdd (left right : BitVec 32) : BitVec 32 :=
  toBits (Float32.add (ofBits left) (ofBits right))

private def hostSub (left right : BitVec 32) : BitVec 32 :=
  toBits (Float32.sub (ofBits left) (ofBits right))

private def hostMul (left right : BitVec 32) : BitVec 32 :=
  toBits (Float32.mul (ofBits left) (ofBits right))

private def hostDiv (left right : BitVec 32) : BitVec 32 :=
  toBits (Float32.div (ofBits left) (ofBits right))

private def hostSqrt (value : BitVec 32) : BitVec 32 :=
  toBits (Float32.sqrt (ofBits value))

def canonicalizeNaNResult (value : BitVec 32) : BitVec 32 :=
  if isNaN value then canonicalNaN else value

/-- RISC-V binary32 addition value under RNE. Every NaN result is canonical. -/
def add (left right : BitVec 32) : BitVec 32 :=
  if isNaN left || isNaN right || invalidAdd left right then canonicalNaN
  else canonicalizeNaNResult (hostAdd left right)

/-- RISC-V binary32 subtraction value under RNE. Every NaN result is canonical. -/
def sub (left right : BitVec 32) : BitVec 32 :=
  if isNaN left || isNaN right || invalidSub left right then canonicalNaN
  else canonicalizeNaNResult (hostSub left right)

/-- Arm `FPProcessNaNs` selection for two operands under `DN=0` and `AH=0`.
    Signaling NaNs precede quiet NaNs; operand order breaks ties. -/
def armNaNResultDN0AH0 (left right : BitVec 32) : Option (BitVec 32) :=
  if isSignalingNaN left then some (quietNaN left)
  else if isSignalingNaN right then some (quietNaN right)
  else if isNaN left then some (quietNaN left)
  else if isNaN right then some (quietNaN right)
  else none

/-- Arm FADD value under `DN=0`, `AH=0`, `FZ=0`, and RNE.
    Invalid-operation flags and traps are outside this nontrapping value function. -/
def armAddDN0AH0 (left right : BitVec 32) : BitVec 32 :=
  match armNaNResultDN0AH0 left right with
  | some result => result
  | none => add left right

/-- Arm FSUB value under `DN=0`, `AH=0`, `FZ=0`, and RNE.
    Invalid-operation flags and traps are outside this nontrapping value function. -/
def armSubDN0AH0 (left right : BitVec 32) : BitVec 32 :=
  match armNaNResultDN0AH0 left right with
  | some result => result
  | none => sub left right

/-- RISC-V binary32 multiplication value under RNE. Every NaN result is canonical. -/
def mul (left right : BitVec 32) : BitVec 32 :=
  if isNaN left || isNaN right || invalidMul left right then canonicalNaN
  else canonicalizeNaNResult (hostMul left right)

/-- RISC-V binary32 division value under RNE. Every NaN result is canonical. -/
def div (left right : BitVec 32) : BitVec 32 :=
  if isNaN left || isNaN right || invalidDiv left right then canonicalNaN
  else canonicalizeNaNResult (hostDiv left right)

/-- RISC-V binary32 square-root value under RNE. Every NaN result is canonical. -/
def sqrt (value : BitVec 32) : BitVec 32 :=
  if isNaN value || invalidSqrt value then canonicalNaN
  else canonicalizeNaNResult (hostSqrt value)

/-- Arm FMUL value under `DN=0`, `AH=0`, `FZ=0`, and RNE. -/
def armMulDN0AH0 (left right : BitVec 32) : BitVec 32 :=
  match armNaNResultDN0AH0 left right with
  | some result => result
  | none => mul left right

/-- Arm FDIV value under `DN=0`, `AH=0`, `FZ=0`, and RNE. -/
def armDivDN0AH0 (left right : BitVec 32) : BitVec 32 :=
  match armNaNResultDN0AH0 left right with
  | some result => result
  | none => div left right

/-- Arm FSQRT value under `DN=0`, `AH=0`, `FZ=0`, and RNE. -/
def armSqrtDN0AH0 (value : BitVec 32) : BitVec 32 :=
  if isNaN value then quietNaN value
  else sqrt value

theorem armAdd_eq_add_of_not_nan (left right : BitVec 32)
    (hLeft : isNaN left = false) (hRight : isNaN right = false) :
    armAddDN0AH0 left right = add left right := by
  simp [armAddDN0AH0, armNaNResultDN0AH0, isSignalingNaN, hLeft, hRight]

theorem armSub_eq_sub_of_not_nan (left right : BitVec 32)
    (hLeft : isNaN left = false) (hRight : isNaN right = false) :
    armSubDN0AH0 left right = sub left right := by
  simp [armSubDN0AH0, armNaNResultDN0AH0, isSignalingNaN, hLeft, hRight]

theorem quietNaN_idem (value : BitVec 32) :
    quietNaN (quietNaN value) = quietNaN value := by
  ext i
  simp [quietNaN]

theorem isNaN_quietNaN_of_isNaN (value : BitVec 32)
    (hValue : isNaN value = true) :
    isNaN (quietNaN value) = true := by
  have hQuietExp : (4194304 : BitVec 32) &&& 2139095040 = 0 := by decide
  have hQuietFrac : (4194304 : BitVec 32) &&& 8388607 = 4194304 := by decide
  have hQuietNonzero : (4194304 : BitVec 32) ≠ 0 := by decide
  have hExpResult : ((value ||| 4194304) &&& 2139095040 : BitVec 32) =
      value &&& 2139095040 := by
    rw [BitVec.and_or_distrib_right, hQuietExp]
    exact BitVec.or_zero
  have hFracResult : ((value ||| 4194304) &&& 8388607 : BitVec 32) =
      (value &&& 8388607) ||| 4194304 := by
    rw [BitVec.and_or_distrib_right, hQuietFrac]
  simp only [isNaN, quietNaN]
  rw [hExpResult, hFracResult]
  simp only [isNaN, Bool.and_eq_true, beq_iff_eq, bne_iff_ne] at hValue
  simp only [Bool.and_eq_true, beq_iff_eq, bne_iff_ne]
  constructor
  · exact hValue.1
  · intro hZero
    exact hQuietNonzero (BitVec.or_eq_zero_iff.mp hZero).2

theorem armAdd_nan_left (left right : BitVec 32)
    (hLeft : isNaN left = true) (hRight : isNaN right = false) :
    armAddDN0AH0 left right = quietNaN left := by
  unfold armAddDN0AH0 armNaNResultDN0AH0
  by_cases hSignal : isSignalingNaN left <;>
    simp [hSignal, isSignalingNaN, hLeft, hRight]

theorem armSub_nan_left (left right : BitVec 32)
    (hLeft : isNaN left = true) (hRight : isNaN right = false) :
    armSubDN0AH0 left right = quietNaN left := by
  unfold armSubDN0AH0 armNaNResultDN0AH0
  by_cases hSignal : isSignalingNaN left <;>
    simp [hSignal, isSignalingNaN, hLeft, hRight]

theorem armMul_eq_mul_of_not_nan (left right : BitVec 32)
    (hLeft : isNaN left = false) (hRight : isNaN right = false) :
    armMulDN0AH0 left right = mul left right := by
  simp [armMulDN0AH0, armNaNResultDN0AH0, isSignalingNaN, hLeft, hRight]

theorem mul_canonicalNaN_left (right : BitVec 32) :
    mul canonicalNaN right = canonicalNaN := by
  simp [mul, canonicalNaN, isNaN]

theorem add_canonicalNaN_left (right : BitVec 32) :
    add canonicalNaN right = canonicalNaN := by
  simp [add, canonicalNaN, isNaN]

theorem sub_canonicalNaN_left (right : BitVec 32) :
    sub canonicalNaN right = canonicalNaN := by
  simp [sub, canonicalNaN, isNaN]

theorem armMul_canonicalNaN_left (right : BitVec 32)
  (hRight : isNaN right = false) :
    armMulDN0AH0 canonicalNaN right = canonicalNaN := by
  have hCanonical : isNaN canonicalNaN = true := by decide
  have hQuiet : quietNaN canonicalNaN = canonicalNaN := by decide
  simp [armMulDN0AH0, armNaNResultDN0AH0, isSignalingNaN,
    hCanonical, hQuiet, hRight]

theorem armAdd_canonicalNaN_left (right : BitVec 32)
  (hRight : isNaN right = false) :
    armAddDN0AH0 canonicalNaN right = canonicalNaN := by
  have hCanonical : isNaN canonicalNaN = true := by decide
  have hQuiet : quietNaN canonicalNaN = canonicalNaN := by decide
  simp [armAddDN0AH0, armNaNResultDN0AH0, isSignalingNaN,
    hCanonical, hQuiet, hRight]

theorem armSub_canonicalNaN_left (right : BitVec 32)
    (hRight : isNaN right = false) :
    armSubDN0AH0 canonicalNaN right = canonicalNaN := by
  have hCanonical : isNaN canonicalNaN = true := by decide
  have hQuiet : quietNaN canonicalNaN = canonicalNaN := by decide
  simp [armSubDN0AH0, armNaNResultDN0AH0, isSignalingNaN,
    hCanonical, hQuiet, hRight]

theorem add_eq_canonicalNaN_of_isNaN (left right : BitVec 32)
    (hResult : isNaN (add left right) = true) :
    add left right = canonicalNaN := by
  unfold add at hResult ⊢
  split
  · rfl
  · unfold canonicalizeNaNResult at hResult ⊢
    split <;> simp_all

theorem mul_eq_canonicalNaN_of_isNaN (left right : BitVec 32)
    (hResult : isNaN (mul left right) = true) :
    mul left right = canonicalNaN := by
  unfold mul at hResult ⊢
  split
  · rfl
  · unfold canonicalizeNaNResult at hResult ⊢
    split <;> simp_all

def abs (value : BitVec 32) : BitVec 32 :=
  value &&& 0x7FFFFFFF

theorem isNaN_abs (value : BitVec 32) :
    isNaN (abs value) = isNaN value := by
  have hExpMask : (2147483647 : BitVec 32) &&& 2139095040 = 2139095040 := by decide
  have hFracMask : (2147483647 : BitVec 32) &&& 8388607 = 8388607 := by decide
  simp only [isNaN, abs]
  rw [BitVec.and_assoc, hExpMask, BitVec.and_assoc, hFracMask]

theorem exponentMask_lt_abs_of_isNaN (value : BitVec 32)
    (hValue : isNaN (abs value) = true) :
    (2139095040 : BitVec 32) < abs value := by
  let absolute := abs value
  let fraction := absolute &&& (8388607 : BitVec 32)
  simp only [isNaN, Bool.and_eq_true, beq_iff_eq, bne_iff_ne] at hValue
  have hMasks : (2139095040 : BitVec 32) ||| 8388607 = 2147483647 := by decide
  have hAbsoluteMask : absolute &&& (2147483647 : BitVec 32) = absolute := by
    dsimp [absolute, abs]
    rw [BitVec.and_assoc, BitVec.and_self]
  have hDecompose : absolute = (2139095040 : BitVec 32) ||| fraction := by
    calc
      absolute = absolute &&& (2147483647 : BitVec 32) := hAbsoluteMask.symm
      _ = absolute &&& ((2139095040 : BitVec 32) ||| 8388607) := by rw [hMasks]
      _ = (absolute &&& (2139095040 : BitVec 32)) ||| fraction := by
        rw [BitVec.and_or_distrib_left]
      _ = (2139095040 : BitVec 32) ||| fraction := by rw [hValue.1]
  have hFractionNatBound : fraction.toNat < 2 ^ 23 := by
    dsimp [fraction]
    change absolute.toNat &&& 8388607 < 2 ^ 23
    exact Nat.and_lt_two_pow absolute.toNat (by decide)
  have hFractionNatPositive : 0 < fraction.toNat := by
    apply Nat.pos_of_ne_zero
    intro hZero
    apply hValue.2
    apply BitVec.eq_of_toNat_eq
    simpa using hZero
  rw [← BitVec.ult_iff_lt, BitVec.ult_iff_toNat_lt]
  change (2139095040 : BitVec 32).toNat < absolute.toNat
  rw [hDecompose, BitVec.toNat_or]
  have hExponentNat : (2139095040 : BitVec 32).toNat = 255 <<< 23 := by decide
  rw [hExponentNat]
  rw [← Nat.shiftLeft_add_eq_or_of_lt hFractionNatBound 255]
  omega

def ofInt32 (value : BitVec 32) : BitVec 32 :=
  toBits (Float32.ofInt value.toInt)

/-- Round a nonnegative binary32 significand to an integer using RNE. -/
def roundMagnitudeRNE (mantissa : Nat) (unbiasedExponent : Int) : Nat :=
  if unbiasedExponent < 0 then
    if unbiasedExponent = -1 && mantissa > 2 ^ 23 then 1 else 0
  else if unbiasedExponent < 23 then
    let discarded := (23 - unbiasedExponent).toNat
    let integral := mantissa / 2 ^ discarded
    let remainder := mantissa % 2 ^ discarded
    let half := 2 ^ (discarded - 1)
    if remainder > half || (remainder = half && integral % 2 = 1) then
      integral + 1
    else integral
  else
    mantissa * 2 ^ (unbiasedExponent - 23).toNat

/-- RISC-V `vfcvt.x.f.v` binary32-to-i32 value result under `frm = RNE`.
    The architectural invalid/inexact flags are intentionally outside this value
    function. Invalid finite values and infinities saturate as required by the
    scalar FCVT table; every NaN maps to INT32_MAX. -/
def toInt32RNE (value : BitVec 32) : BitVec 32 :=
  let exponent := ((value.ushiftRight 23).truncate 8).toNat
  let fraction := (value &&& 0x007FFFFF).toNat
  let negative := value.getLsbD 31
  if exponent = 255 then
    if fraction != 0 then BitVec.ofInt 32 2147483647
    else if negative then BitVec.ofInt 32 (-2147483648)
    else BitVec.ofInt 32 2147483647
  else if exponent = 0 then
    BitVec.ofInt 32 0
  else
    let magnitude := roundMagnitudeRNE (2 ^ 23 + fraction) (Int.ofNat exponent - 127)
    if negative then
      BitVec.ofInt 32 (max (-2147483648) (-(Int.ofNat magnitude)))
    else
      BitVec.ofInt 32 (min 2147483647 (Int.ofNat magnitude))

/-- IEEE binary32 ordered less-than as a reducible value predicate. -/
def lt (left right : BitVec 32) : Bool :=
  if isNaN left || isNaN right then false
  else if isZero left && isZero right then false
  else if signBit left != signBit right then signBit left
  else if signBit left then decide (right.toNat < left.toNat)
  else decide (left.toNat < right.toNat)

def gt (left right : BitVec 32) : Bool :=
  lt right left

def valueEq (left right : BitVec 32) : Bool :=
  if isNaN left || isNaN right then false
  else if isZero left && isZero right then true
  else left == right

def ne (left right : BitVec 32) : Bool :=
  !(valueEq left right)

theorem ne_self (value : BitVec 32) : ne value value = isNaN value := by
  simp [ne, valueEq]

def orderedMax (left right : BitVec 32) : BitVec 32 :=
  if lt left right then right
  else if lt right left then left
  else if isZero left && isZero right then left &&& right
  else left

def orderedMin (left right : BitVec 32) : BitVec 32 :=
  if lt left right then left
  else if lt right left then right
  else if isZero left && isZero right then left ||| right
  else left

/-- Arm FMAX/FMIN value result with NaN propagation; FP exception state is separate. -/
def maxPropagatingNaN (left right : BitVec 32) : BitVec 32 :=
  match armNaNResultDN0AH0 left right with
  | some result => result
  | none => orderedMax left right

def minPropagatingNaN (left right : BitVec 32) : BitVec 32 :=
  match armNaNResultDN0AH0 left right with
  | some result => result
  | none => orderedMin left right

/-- RISC-V VFMAX/VFMIN IEEE maximumNumber/minimumNumber value result. -/
def maxNumber (left right : BitVec 32) : BitVec 32 :=
  if isNaN left then if isNaN right then 0x7FC00000 else right
  else if isNaN right then left
  else orderedMax left right

def minNumber (left right : BitVec 32) : BitVec 32 :=
  if isNaN left then if isNaN right then 0x7FC00000 else right
  else if isNaN right then left
  else orderedMin left right

end SALT.Intrinsics.FP32
