import SALT.Corpus.s8vclamp.Spec

namespace SALT.Corpus.s8vclamp

def counterexampleParams : s8vclampParams := { max := (0 : BitVec 32), min := (5 : BitVec 32) }
def counterexampleInput0 : BitVec 8 := 0

example : (fNeon counterexampleParams counterexampleInput0).toNat = 0 := by native_decide
example : (fNeonSecondary counterexampleParams counterexampleInput0).toNat = 5 := by native_decide
example : fNeon counterexampleParams counterexampleInput0 ≠
    fNeonSecondary counterexampleParams counterexampleInput0 := by native_decide

end SALT.Corpus.s8vclamp
