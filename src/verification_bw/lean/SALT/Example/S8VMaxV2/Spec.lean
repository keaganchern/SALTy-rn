-- This file is intended to be generated and then frozen before proof search.
-- It contains propositions only: no axioms, no `sorry`, and no proof script.
import SALT.Example.S8VMaxV2.Models

namespace SALT.Example.S8VMaxV2

open SALT.Example.S8VMax

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : S8VMaxParams) (batch : Nat) (input : List (BitVec 8)),
    input.length = batch → neonSourceAsserts batch →
    neonLoopFromC p input = input.map (fNeon p)

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : S8VMaxParams) (batch : Nat) (input : List (BitVec 8))
      (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    input.length = batch → rvvSourceAsserts batch →
    rvvLoopFromC p input schedule = input.map (fRvv p)

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : S8VMaxParams) (x : BitVec 8), fNeon p x = fRvv p x

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : S8VMaxParams) (batch : Nat) (input : List (BitVec 8))
      (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    input.length = batch → neonSourceAsserts batch → rvvSourceAsserts batch →
    neonLoopFromC p input = rvvLoopFromC p input schedule

end SALT.Example.S8VMaxV2
