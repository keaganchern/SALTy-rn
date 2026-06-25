import SALT.FP.Basic
import SALT.Core.CoreOp
import SALT.Kernel.F32VELU.Params

namespace SALT.Kernel.F32VELU.Core

open SALT.FP
open SALT.Core
open SALT.Kernel.F32VELU

-- Kernel constants (bit patterns from XNNPACK f32-velu source)

def satCutoff  : Float32 := Float32.ofBits 0xC18AA123  -- -0x1.154246p+4
def magicBias  : Float32 := Float32.ofBits 0x49400000  -- 0x1.800000p19
def log2e      : Float32 := Float32.ofBits 0x3FB8AA3B  -- 0x1.715476p+0
def c3         : Float32 := Float32.ofBits 0x3E2AAB0E  -- 0x1.55561Cp-3
def c2         : Float32 := Float32.ofBits 0x3F0000F6  -- 0x1.0001ECp-1
def one        : Float32 := Float32.ofBits 0x3F800000  -- 1.0
def minusLn2Hi : Float32 := Float32.ofBits 0xBF317200  -- -0x1.62E400p-1
def minusLn2Lo : Float32 := Float32.ofBits 0xB5BFBE8E  -- -0x1.7F7D1Cp-20
def zero       : Float32 := Float32.ofBits 0x00000000  -- 0.0

-- Reducible aliases giving the bit-reinterpretation CoreOps a concrete
-- `Float32` / `BitVec 32` return type while still unfolding definitionally.

@[inline] abbrev f32ToBits (x : Float32) : BitVec 32 :=
  ReinterpretOp.f32ToBits.eval x

@[inline] abbrev bitsToF32 (b : BitVec 32) : Float32 :=
  ReinterpretOp.bitsToF32.eval b

-- Shared per-element function. The bit path routes through `BitVec 32` via
-- `ReinterpretOp` / `BVBinOp` / `BVShiftOp`; Float32 arithmetic uses native
-- operators.

def coreElem (params : F32ELUParams) (x : Float32) : Float32 :=
  let z := fmax (x * params.prescale) satCutoff
  let n := z * log2e + magicBias
  let n_bits : BitVec 32 := f32ToBits n
  let idx : BitVec 32 := BVBinOp.bvAnd.eval n_bits 0xF#32
  let en  : BitVec 32 := BVShiftOp.shl.eval n_bits 19
  let l : BitVec 32 := tableLookup idx
  let n := n - magicBias                          -- recover fractional part
  -- Cody-Waite range reduction
  let t := z + n * minusLn2Hi
  let t := t + n * minusLn2Lo
  -- reconstruct 2^(n/16) from table entry and exponent bits
  let s : Float32 := bitsToF32 (BVBinOp.add.eval l en)
  let p := t * c3 + c2
  let p := p * t
  let t := t * s
  let s := s - one
  let p := t + p * t
  let ve := (p + s) * params.alpha
  -- negative branch uses exp approximation, positive uses linear
  if x < zero then ve else x * params.beta

end SALT.Kernel.F32VELU.Core
