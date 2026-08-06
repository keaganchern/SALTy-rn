import Neon2LeanDemo.Production.All

namespace Neon2LeanDemo.S8Clamp16

open Neon2LeanDemo.Production

def parametersValid (args : KernelArgs) : Prop :=
  args.batch = 16 ∧
    ∃ lo hi : Int,
      args.scalar? "lo" = some lo ∧
      args.scalar? "hi" = some hi ∧
      -128 <= lo ∧ lo <= hi ∧ hi <= 127

/-- Final-state contract for the fixed-size pipeline microcase. -/
def contract : Contract :=
  { inputReadableBytes := fun _ => 16
    outputWritableBytes := fun _ => 16
    aliasPolicy := .disjointOrExactInPlace
    parametersValid := parametersValid }

def observe : Observe Unit Unit :=
  Observe.outputPrefix fun _ => 16

end Neon2LeanDemo.S8Clamp16
