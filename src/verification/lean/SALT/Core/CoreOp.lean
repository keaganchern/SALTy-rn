/-
  The closed CoreOp vocabulary: the scalar semantic core that every
  intrinsic lifts over, split into families by signature shape. The
  cast families carry width-comparison proofs so ill-formed casts are
  unrepresentable.
-/
import SALT.Basic
import SALT.FP.Basic

namespace SALT.Core

open SALT
open SALT.FP

-- Family: same-width BitVec binary  (BitVec w × BitVec w → BitVec w)

/-- Same-width integer/bitvector binary operations. -/
inductive BVBinOp where
  /-- Two's-complement add, mod 2^w. -/
  | add
  /-- Two's-complement subtract, mod 2^w. -/
  | sub
  /-- Two's-complement multiply, mod 2^w. -/
  | mul
  /-- Bitwise AND. -/
  | bvAnd
  /-- Bitwise OR. -/
  | bvOr
  /-- Bitwise XOR. -/
  | bvXor
  /-- Signed minimum. -/
  | sMin
  /-- Signed maximum. -/
  | sMax
  /-- Signed saturating add (clamps to [-2^(w-1), 2^(w-1)-1]). -/
  | sSatAdd
  deriving DecidableEq, Repr

/-- Scalar denotation of a same-width binary BitVec op. -/
def BVBinOp.eval {w : Nat} : BVBinOp → BitVec w → BitVec w → BitVec w
  | .add,      a, b => a + b
  | .sub,      a, b => a - b
  | .mul,      a, b => a * b
  | .bvAnd,    a, b => a &&& b
  | .bvOr,     a, b => a ||| b
  | .bvXor,    a, b => a ^^^ b
  | .sMin,     a, b => bvSignedMin a b
  | .sMax,     a, b => bvSignedMax a b
  | .sSatAdd,  a, b => signedSatAdd a b

-- Family: shift with runtime amount  (BitVec w × Nat → BitVec w).
-- Rounding shifts share one constructor carrying a `RoundingMode`.

/-- Rounding direction / mode for rounding shifts. -/
inductive RoundingMode where
  /-- ARM NEON's VRSHL.S<w>: widen, add 1<<(shift-1), sshift, truncate. -/
  | neon
  /-- RVV's VSSRA.VX with vxrm=RNU: sshift, conditional +1 on shifted-out LSB. -/
  | rvvRnu
  deriving DecidableEq, Repr

/-- Scalar denotation of a rounding mode at a given width. -/
def RoundingMode.apply {w : Nat} : RoundingMode → BitVec w → Nat → BitVec w
  | .neon,   x, n => neonRoundingShiftRight x n
  | .rvvRnu, x, n => rvvRoundingShiftRight x n

/-- Shifts whose amount is a runtime Nat parameter (not encoded in the op). -/
inductive BVShiftOp where
  /-- Logical shift left. -/
  | shl
  /-- Logical shift right. -/
  | lshr
  /-- Arithmetic (sign-preserving) shift right. -/
  | ashr
  /-- Rounding shift right with ISA-specific rounding mode. -/
  | roundShr (mode : RoundingMode)
  deriving DecidableEq, Repr

/-- Scalar denotation of a shift op. -/
def BVShiftOp.eval {w : Nat} : BVShiftOp → BitVec w → Nat → BitVec w
  | .shl,           x, n => x <<< n
  | .lshr,          x, n => x >>> n
  | .ashr,          x, n => x.sshiftRight n
  | .roundShr mode, x, n => mode.apply x n

-- Family: widening cast  (BitVec w → BitVec w', with proof w < w')

/-- Width-increasing integer casts. -/
inductive BVExtOp where
  /-- Sign extend. -/
  | sExt
  deriving DecidableEq, Repr

/-- Scalar denotation of a widening cast, indexed by the target width `w'`
    together with a proof that the source width `w` is strictly smaller. -/
def BVExtOp.eval (op : BVExtOp) (w' : Nat) {w : Nat} (x : BitVec w)
    (_h : w < w' := by decide) : BitVec w' :=
  match op with
  | .sExt => sext x w'

-- Family: narrowing cast  (BitVec w → BitVec w', with proof w' < w)

/-- Width-decreasing integer casts. -/
inductive BVNarrowOp where
  /-- Signed saturating narrow: clamp to [-2^(w'-1), 2^(w'-1)-1] then truncate. -/
  | sSatNarrow
  deriving DecidableEq, Repr

/-- Scalar denotation of a narrowing cast, indexed by the target width `w'`
    together with a proof that the source width `w` is strictly larger. -/
def BVNarrowOp.eval (op : BVNarrowOp) (w' : Nat) {w : Nat} (x : BitVec w)
    (_h : w' < w := by decide) : BitVec w' :=
  match op with
  | .sSatNarrow => signedClamp x w'

-- Family: Float32 binary arithmetic

/-- Float32 binary arithmetic operations. -/
inductive FPBinOp where
  | fAdd
  | fSub
  | fMul
  /-- NaN-suppressing max (matches SALT.FP.fmax). -/
  | fMax
  deriving DecidableEq, Repr

def FPBinOp.eval : FPBinOp → Float32 → Float32 → Float32
  | .fAdd, a, b => a + b
  | .fSub, a, b => a - b
  | .fMul, a, b => a * b
  | .fMax, a, b => fmax a b

-- Family: Float32 comparison  (Float32 × Float32 → Bool)

/-- Float32 comparison predicates. -/
inductive FPCmpOp where
  | fLt
  deriving DecidableEq, Repr

def FPCmpOp.eval : FPCmpOp → Float32 → Float32 → Bool
  | .fLt, a, b => a < b

-- Family: bit reinterpretation between Float32 and BitVec 32.
-- One `.eval` whose input/output types are given by `.In` and `.Out`.

/-- Bit-level reinterpretation between Float32 and BitVec 32. -/
inductive ReinterpretOp where
  | f32ToBits
  | bitsToF32
  deriving DecidableEq, Repr

/-- The input type of a reinterpretation operator. -/
def ReinterpretOp.In : ReinterpretOp → Type
  | .f32ToBits => Float32
  | .bitsToF32 => BitVec 32

/-- The output type of a reinterpretation operator. -/
def ReinterpretOp.Out : ReinterpretOp → Type
  | .f32ToBits => BitVec 32
  | .bitsToF32 => Float32

/-- Uniform denotation: each operator maps `op.In → op.Out`. -/
def ReinterpretOp.eval : (op : ReinterpretOp) → op.In → op.Out
  | .f32ToBits, x => BitVec.ofNat 32 x.toBits.toNat
  | .bitsToF32, x => Float32.ofBits (UInt32.ofNat x.toNat)

-- Unified CoreOp sum, used for IR emission / kernel pair descriptions.
-- Lean code consumes the family-specific types above directly.

inductive CoreOp where
  | BVBin        (op : BVBinOp)
  | BVShift      (op : BVShiftOp)
  | BVExt        (op : BVExtOp)
  | BVNarrow     (op : BVNarrowOp)
  | FPBin        (op : FPBinOp)
  | FPCmp        (op : FPCmpOp)
  | Reinterpret  (op : ReinterpretOp)
  deriving DecidableEq, Repr

end SALT.Core
