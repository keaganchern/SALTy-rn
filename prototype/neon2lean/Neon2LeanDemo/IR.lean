namespace Neon2LeanDemo

/-- Comparison interpretation for integer lanes. -/
inductive CompareMode where
  | signed
  | unsigned
  deriving DecidableEq, Repr

/-- The lane-level binary operations needed by the demo. -/
inductive VecBinOp where
  | min (mode : CompareMode)
  | max (mode : CompareMode)
  deriving DecidableEq, Repr

def intMin {bits : Nat} (mode : CompareMode) (a b : BitVec bits) : BitVec bits :=
  match mode with
  | .signed => if a.toInt ≤ b.toInt then a else b
  | .unsigned => if a.toNat ≤ b.toNat then a else b

def intMax {bits : Nat} (mode : CompareMode) (a b : BitVec bits) : BitVec bits :=
  match mode with
  | .signed => if b.toInt ≤ a.toInt then a else b
  | .unsigned => if b.toNat ≤ a.toNat then a else b

def VecBinOp.denote {bits : Nat} (op : VecBinOp) (a b : BitVec bits) : BitVec bits :=
  match op with
  | .min mode => intMin mode a b
  | .max mode => intMax mode a b

/-- A scalar node. `paramU32Trunc` makes the C integer conversion at a vector splat explicit. -/
inductive ScalarExpr (bits : Nat) where
  | paramU32Trunc (name : String)
  | literal (value : BitVec bits)
  deriving Repr

def ScalarExpr.denote {bits : Nat} (params : String → BitVec 32) :
    ScalarExpr bits → BitVec bits
  | .paramU32Trunc name => BitVec.ofNat bits (params name).toNat
  | .literal value => value

/--
A typed vector expression. Both the lane count and element width are indices, so a generated
term cannot connect an 8-lane value to a 16-lane operation or mix element widths.
-/
inductive VecExpr (lanes bits : Nat) where
  | load (inputOffset : Nat)
  | splat (value : ScalarExpr bits)
  | bin (op : VecBinOp) (lhs rhs : VecExpr lanes bits)
  deriving Repr

abbrev Vec (lanes bits : Nat) := Fin lanes → BitVec bits

def VecExpr.denote {lanes bits : Nat} (input : Nat → BitVec bits)
    (params : String → BitVec 32) : VecExpr lanes bits → Vec lanes bits
  | .load inputOffset => fun lane => input (inputOffset + lane.val)
  | .splat value => fun _ => value.denote params
  | .bin op lhs rhs => fun lane =>
      op.denote (lhs.denote input params lane) (rhs.denote input params lane)

structure SourceInfo where
  path : String
  sha256 : String
  beginOffset : Nat
  endOffset : Nat
  deriving DecidableEq, Repr

/-- One fixed-width write in a loop body. -/
structure Store (lanes bits : Nat) where
  outputOffset : Nat
  value : VecExpr lanes bits
  deriving Repr

/-- Metadata and dataflow for one fixed-width C loop body. -/
structure FixedLoop (lanes bits : Nat) where
  source : SourceInfo
  batchGuard : Nat
  batchDecrement : Nat
  inputAdvance : Nat
  outputAdvance : Nat
  stores : List (Store lanes bits)
  deriving Repr

def Store.addresses {lanes bits : Nat} (store : Store lanes bits) : List Nat :=
  List.ofFn fun lane : Fin lanes => store.outputOffset + lane.val

def FixedLoop.writeAddresses {lanes bits : Nat} (loop : FixedLoop lanes bits) : List Nat :=
  loop.stores.flatMap Store.addresses

def unsignedClamp {bits : Nat} (lo hi x : BitVec bits) : BitVec bits :=
  intMin .unsigned (intMax .unsigned x lo) hi

end Neon2LeanDemo
