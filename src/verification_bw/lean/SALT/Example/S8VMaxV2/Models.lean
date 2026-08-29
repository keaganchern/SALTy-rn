-- Target shape for generated code. The block expressions below come from the
-- current C frontend/emitter; the loop assembly is the missing family layer.
import SALT.Example.S8VMax.Models
import SALT.Kernel.ElementwiseFamily

namespace SALT.Example.S8VMaxV2

open SALT.Example.S8VMax

/-- Scalar action extracted independently from the Neon intrinsic expression. -/
def fNeon (p : S8VMaxParams) (x : BitVec 8) : BitVec 8 :=
  (SALT.Intrinsics.Neon.vmaxq_s8 [x] [p.threshold.truncate 8]).headD x

/-- Scalar action extracted independently from the RVV intrinsic expression. -/
def fRvv (p : S8VMaxParams) (x : BitVec 8) : BitVec 8 :=
  (SALT.Intrinsics.RVV.vmax_vx [x] (p.threshold.truncate 8)).headD x

/-- Direct translation of the value-relevant Neon assertions. Pointer
    non-null assertions are represented by using values rather than nullable
    pointers in this value-level model. -/
def neonSourceAsserts (batch : Nat) : Prop :=
  batch ≠ 0 ∧ batch % 16 = 0

/-- Direct translation of the value-relevant RVV assertion. -/
def rvvSourceAsserts (batch : Nat) : Prop :=
  batch ≠ 0

/-- Generated assembly of the fixed-width Neon loop. The empty tail is safe
    only under `batch % 16 = 0`, which remains explicit in `Spec.lean`. -/
def neonLoopFromC (p : S8VMaxParams) (input : List (BitVec 8)) : List (BitVec 8) :=
  SALT.Kernel.ElementwiseFamily.runFixedNoTail 16 (by omega)
    (neonBlock16FromIntrinsics p) input

/-- Generated assembly of the RVV loop. A legal `vsetvl` trace is represented
    at this layer by a complete positive partition of the input length. -/
def rvvLoopFromC (p : S8VMaxParams) (input : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length) : List (BitVec 8) :=
  SALT.Kernel.Schedule.processBlocks (rvvChunkFromIntrinsics p) input schedule

end SALT.Example.S8VMaxV2
