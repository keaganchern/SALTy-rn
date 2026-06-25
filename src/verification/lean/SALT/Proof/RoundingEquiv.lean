import SALT.Basic
import Std.Tactic.BVDecide

namespace SALT.Proof.RoundingEquiv

open SALT

-- NEON and RVV rounding shifts agree for shift ≤ 31.
theorem rounding_shift_equiv (x : BitVec 32) (shift : Nat)
    (h_bound : shift ≤ 31) :
    neonRoundingShiftRight x shift = rvvRoundingShiftRight x shift := by
  have h_cases : shift = 0 ∨ shift = 1 ∨ shift = 2 ∨ shift = 3 ∨ shift = 4 ∨
    shift = 5 ∨ shift = 6 ∨ shift = 7 ∨ shift = 8 ∨ shift = 9 ∨ shift = 10 ∨
    shift = 11 ∨ shift = 12 ∨ shift = 13 ∨ shift = 14 ∨ shift = 15 ∨ shift = 16 ∨
    shift = 17 ∨ shift = 18 ∨ shift = 19 ∨ shift = 20 ∨ shift = 21 ∨ shift = 22 ∨
    shift = 23 ∨ shift = 24 ∨ shift = 25 ∨ shift = 26 ∨ shift = 27 ∨ shift = 28 ∨
    shift = 29 ∨ shift = 30 ∨ shift = 31 := by omega
  rcases h_cases with h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h
  all_goals (subst h; simp only [neonRoundingShiftRight, rvvRoundingShiftRight]; bv_decide)

end SALT.Proof.RoundingEquiv
