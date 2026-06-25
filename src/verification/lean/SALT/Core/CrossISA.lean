/-
  Cross-ISA CoreOp lemma library: one-time lemmas proving that NEON and
  RVV parameter choices over the shared CoreOp vocabulary coincide on a
  constrained domain (e.g. the two rounding-shift modes for shifts ≤ 31).
-/
import SALT.Core.CoreOp
import SALT.Intrinsics.RVV
import SALT.Proof.RoundingEquiv

namespace SALT.Core.CrossISA

open SALT.Core

-- Rounding-mode equivalence: NEON's VRSHL.S32 and RVV's VSSRA.VX (vxrm=RNU)
-- are bit-identical for shifts in [0, 31].

/-- CoreOp statement of NEON / RVV-RNU rounding-shift equivalence, lifting
    `SALT.Proof.RoundingEquiv.rounding_shift_equiv` to the CoreOp layer. -/
theorem roundShr_modes_equiv (x : BitVec 32) (shift : Nat) (h_bound : shift ≤ 31) :
    (BVShiftOp.roundShr .neon).eval x shift =
    (BVShiftOp.roundShr .rvvRnu).eval x shift := by
  simp only [BVShiftOp.eval, RoundingMode.apply]
  exact SALT.Proof.RoundingEquiv.rounding_shift_equiv x shift h_bound

-- Shift-sign dead-branch collapse: under `shift.toNat ≤ 31` the qs8-vadd RVV
-- source's `if (shift < 0) ... else ...` has a dead then-branch.

theorem toInt_nonneg_of_toNat_le_31 (x : BitVec 32) (h : x.toNat ≤ 31) :
    0 ≤ x.toInt := by
  have h2 : x.toNat < 2 ^ 31 := by omega
  rw [BitVec.toInt_eq_toNat_cond]
  split
  · exact Int.natCast_nonneg _
  · omega

theorem shift_sign_collapse (shift : BitVec 32) (h : shift.toNat ≤ 31)
    (v : List (BitVec 32)) :
    (if shift.toInt < 0 then
       SALT.Intrinsics.RVV.vsll_vx_i32m8 v (-shift).toNat
     else
       SALT.Intrinsics.RVV.vssra_vx_rnu v shift.toNat) =
    SALT.Intrinsics.RVV.vssra_vx_rnu v shift.toNat := by
  have h_nonneg : ¬ (shift.toInt < 0) := by
    have := toInt_nonneg_of_toNat_le_31 shift h
    omega
  rw [if_neg h_nonneg]

end SALT.Core.CrossISA
