namespace Neon2LeanDemo.Production

/-- Signedness is part of the type of an integer scalar, not an operation hint. -/
inductive Signedness where
  | signed
  | unsigned
  deriving BEq, DecidableEq, Repr

/-- Float formats remain representable while the integer-only stage has no FP denotation. -/
inductive FloatFormat where
  | binary16
  | bfloat16
  | binary32
  | binary64
  deriving BEq, DecidableEq, Repr

/-- Scalar tags preserve the distinction between integers, floating point, and masks. -/
inductive ScalarTag where
  | int (bits : Nat) (signedness : Signedness)
  | fp (format : FloatFormat)
  | mask
  deriving BEq, DecidableEq, Repr

/-- RISC-V vector register grouping. Fractional LMUL remains distinct in the IR. -/
inductive LMUL where
  | mf8
  | mf4
  | mf2
  | m1
  | m2
  | m4
  | m8
  deriving BEq, DecidableEq, Repr

/-- Neon vectors are fixed-lane; RVV values are scalable and carry LMUL separately. -/
inductive VectorShape where
  | fixed (lanes : Nat)
  | scalable (lmul : LMUL)
  deriving BEq, DecidableEq, Repr

/-- Typed values include scalars, fixed/scalable vectors, and byte-addressed pointers. -/
inductive ValueTag where
  | scalar (element : ScalarTag)
  | vector (shape : VectorShape) (element : ScalarTag)
  | pointer
  deriving BEq, DecidableEq, Repr

def ScalarTag.isFloating : ScalarTag → Bool
  | .fp _ => true
  | _ => false

def ValueTag.isFloating : ValueTag → Bool
  | .scalar element | .vector _ element => element.isFloating
  | .pointer => false

def ValueTag.isScalableVector : ValueTag → Bool
  | .vector (.scalable _) _ => true
  | _ => false

/-- Zero-bit integers and zero-lane vectors are rejected at the schema boundary. -/
def ScalarTag.WellFormed : ScalarTag → Prop
  | .int bits _ => 0 < bits
  | .fp _ | .mask => True

def ScalarTag.isWellFormed : ScalarTag → Bool
  | .int bits _ => bits > 0
  | .fp _ | .mask => true

def ValueTag.WellFormed : ValueTag → Prop
  | .scalar element => element.WellFormed
  | .vector (.fixed lanes) element => 0 < lanes ∧ element.WellFormed
  | .vector (.scalable _) element => element.WellFormed
  | .pointer => True

def ValueTag.isWellFormed : ValueTag → Bool
  | .scalar element => element.isWellFormed
  | .vector (.fixed lanes) element => lanes > 0 && element.isWellFormed
  | .vector (.scalable _) element => element.isWellFormed
  | .pointer => true

/-- Per-operation RVV shape state; `activeVLNode` names the SSA value supplying `vl`. -/
structure RVVVectorConfig where
  sew : Nat
  lmul : LMUL
  activeVLNode : Nat
  deriving BEq, DecidableEq, Repr

def RVVVectorConfig.WellFormed (config : RVVVectorConfig) : Prop :=
  0 < config.sew

def RVVVectorConfig.isWellFormed (config : RVVVectorConfig) : Bool :=
  config.sew > 0

inductive Architecture where
  | neutral
  | c
  | neon
  | rvv
  deriving BEq, DecidableEq, Repr

/-- Families are deliberately coarse; `spelling` retains the exact source operation. -/
inductive OperationFamily where
  | integer
  | mask
  | memory
  | control
  | conversion
  | floatingPoint
  | unsupported
  deriving BEq, DecidableEq, Repr

structure OperationTag where
  architecture : Architecture
  family : OperationFamily
  spelling : String
  deriving BEq, DecidableEq, Repr

end Neon2LeanDemo.Production
