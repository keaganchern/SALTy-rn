import SALT.Basic

namespace SALT.Intrinsics.FP32

/-- Interpret one logical 32-bit lane through Lean's IEEE-754 binary32 primitive. -/
def ofBits (value : BitVec 32) : Float32 :=
  Float32.ofBits (UInt32.ofNat value.toNat)

/-- Return the exact binary32 result bits produced by Lean's primitive. -/
def toBits (value : Float32) : BitVec 32 :=
  value.toBits.toBitVec

def add (left right : BitVec 32) : BitVec 32 :=
  toBits (Float32.add (ofBits left) (ofBits right))

def sub (left right : BitVec 32) : BitVec 32 :=
  toBits (Float32.sub (ofBits left) (ofBits right))

def mul (left right : BitVec 32) : BitVec 32 :=
  toBits (Float32.mul (ofBits left) (ofBits right))

def div (left right : BitVec 32) : BitVec 32 :=
  toBits (Float32.div (ofBits left) (ofBits right))

def sqrt (value : BitVec 32) : BitVec 32 :=
  toBits (Float32.sqrt (ofBits value))

def abs (value : BitVec 32) : BitVec 32 :=
  value &&& 0x7FFFFFFF

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

def lt (left right : BitVec 32) : Bool :=
  decide (ofBits left < ofBits right)

def gt (left right : BitVec 32) : Bool :=
  lt right left

def ne (left right : BitVec 32) : Bool :=
  !(Float32.beq (ofBits left) (ofBits right))

def isNaN (value : BitVec 32) : Bool :=
  (value &&& 0x7F800000) == 0x7F800000 && (value &&& 0x007FFFFF) != 0

def quietNaN (value : BitVec 32) : BitVec 32 :=
  value ||| 0x00400000

def isZero (value : BitVec 32) : Bool :=
  (value &&& 0x7FFFFFFF) == 0

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
  if isNaN left then quietNaN left
  else if isNaN right then quietNaN right
  else orderedMax left right

def minPropagatingNaN (left right : BitVec 32) : BitVec 32 :=
  if isNaN left then quietNaN left
  else if isNaN right then quietNaN right
  else orderedMin left right

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
