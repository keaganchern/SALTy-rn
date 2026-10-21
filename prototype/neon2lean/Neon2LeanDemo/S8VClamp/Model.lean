import Neon2LeanDemo.IR

namespace Neon2LeanDemo.S8VClamp

abbrev Byte := BitVec 8

/-- Signed maximum on an 8-bit lane. -/
def signedMax (a b : Byte) : Byte :=
  if b.toInt ≤ a.toInt then a else b

/-- Signed minimum on an 8-bit lane. -/
def signedMin (a b : Byte) : Byte :=
  if a.toInt ≤ b.toInt then a else b

/-- The pointwise specification used by the Neon main loop and the RVV loop. -/
def clamp (lo hi x : Byte) : Byte :=
  signedMin (signedMax x lo) hi

/-- The 8-byte Neon loop and its tail apply the bounds in the opposite order. -/
def tailClamp (lo hi x : Byte) : Byte :=
  signedMax (signedMin x hi) lo

/--
`PositivePartition remaining chunks` means that each chunk is positive, fits in the
current remainder, and the chunks consume the input exactly. This is deliberately
weaker than RVV ISA legality; a later bridge must prove that `vsetvl` execution
produces such a partition while also satisfying VLEN/VLMAX constraints.
-/
def PositivePartition : Nat → List Nat → Prop
  | remaining, [] => remaining = 0
  | remaining, chunk :: chunks =>
      0 < chunk ∧ chunk ≤ remaining ∧ PositivePartition (remaining - chunk) chunks

/--
Progress interface needed by the value model. A separate ISA bridge must show that
the concrete `vsetvl_e8m8` result obeys these constraints.
-/
structure RVVProgressPolicy where
  vlmax : Nat
  choose : Nat → Nat
  vlmaxPositive : 0 < vlmax
  legal : ∀ remaining, 0 < remaining →
    0 < choose remaining ∧ choose remaining ≤ remaining ∧ choose remaining ≤ vlmax

def RVVProgressPolicy.schedule (policy : RVVProgressPolicy) (remaining : Nat) : List Nat :=
  if _hzero : remaining = 0 then
    []
  else
    let vl := policy.choose remaining
    vl :: policy.schedule (remaining - vl)
termination_by remaining
decreasing_by
  have hlegal := policy.legal remaining (Nat.pos_of_ne_zero _hzero)
  omega

/-- Apply a chunk-sensitive lane operation to each scheduled input prefix. -/
def processChunks (step : Nat → Byte → Byte) : List Nat → List Byte → List Byte
  | [], _ => []
  | chunk :: chunks, input =>
      (input.take chunk).map (step chunk) ++
        processChunks step chunks (input.drop chunk)

/--
The output schedule of the Neon C kernel: 64-byte iterations, then 8-byte
iterations, followed by one 1--7-byte write tail when necessary.
-/
def neonSchedule (remaining : Nat) : List Nat :=
  if h64 : 64 ≤ remaining then
    64 :: neonSchedule (remaining - 64)
  else if h8 : 8 ≤ remaining then
    8 :: neonSchedule (remaining - 8)
  else if remaining = 0 then
    []
  else
    [remaining]
termination_by remaining
decreasing_by all_goals omega

/-- Main chunks use `max` then `min`; 8-byte and tail chunks use `min` then `max`. -/
def neonStep (lo hi : Byte) (chunk : Nat) (x : Byte) : Byte :=
  if chunk = 64 then clamp lo hi x else tailClamp lo hi x

/-- Value-level Neon execution. The physical 8-byte tail read belongs in the memory model. -/
def runNeon (lo hi : Byte) (input : List Byte) : List Byte :=
  processChunks (neonStep lo hi) (neonSchedule input.length) input

/-- Value-level chunk execution; the RVV policy-to-partition bridge is separate. -/
def runPartitioned (lo hi : Byte) (chunks : List Nat) (input : List Byte) : List Byte :=
  processChunks (fun _ => clamp lo hi) chunks input

/-- Execute the value model using a progress policy rather than a prebuilt partition. -/
def runRVVPolicy (policy : RVVProgressPolicy) (lo hi : Byte)
    (input : List Byte) : List Byte :=
  runPartitioned lo hi (policy.schedule input.length) input

end Neon2LeanDemo.S8VClamp
