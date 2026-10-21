import Neon2LeanDemo.Production.All

namespace Neon2LeanDemo.S8VClamp

open Neon2LeanDemo.Production

/-- Source-side readable extent: the Neon tail performs one physical 8-byte load. -/
def roundUpTo8 (bytes : Nat) : Nat :=
  ((bytes + 7) / 8) * 8

def parametersValid (args : KernelArgs) : Prop :=
  0 < args.batch ∧
    ∃ lo hi : Int,
      args.scalar? "min" = some lo ∧
      args.scalar? "max" = some hi ∧
      -128 ≤ lo ∧ lo ≤ hi ∧ hi ≤ 127

/-- Initial C-level contract proposed for the paired `s8-vclamp` slice. -/
def contract : Contract :=
  { inputReadableBytes := fun args => roundUpTo8 args.batch
    outputWritableBytes := fun args => args.batch
    aliasPolicy := .disjointOrExactInPlace
    parametersValid := parametersValid }

/-- Compare exactly the logical output prefix; frame obligations are stated separately. -/
def observe : Observe Unit Unit :=
  Observe.outputPrefix (fun args => args.batch)

end Neon2LeanDemo.S8VClamp
