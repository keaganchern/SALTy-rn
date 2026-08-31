import SALT.Corpus.s8vclamp.Spec

namespace SALT.Corpus.s8vclamp

def counterexampleParams : s8vclampParams := { max := (0 : BitVec 32), min := (5 : BitVec 32) }
def counterexampleInput0 : BitVec 8 := 0

example : (fNeon counterexampleParams counterexampleInput0).toNat = 0 := by native_decide
example : (fNeonSecondary counterexampleParams counterexampleInput0).toNat = 5 := by native_decide
theorem neonPhaseFunctionsCounterexample : Not neonPhaseFunctionsEqualClaim := by
  intro claim
  exact (by native_decide : fNeon counterexampleParams counterexampleInput0 ≠
    fNeonSecondary counterexampleParams counterexampleInput0)
    (claim counterexampleParams counterexampleInput0)

end SALT.Corpus.s8vclamp
