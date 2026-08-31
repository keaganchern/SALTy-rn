import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV

namespace SALT.Proof.RoundingEquiv

open SALT.Intrinsics.Neon
open SALT.Intrinsics.RVV

-- ============================================================================
-- Rounding shift equivalence
-- ============================================================================

private theorem setWidth_ofInt_of_le {v w : Nat} (h : v ≤ w) (i : Int) :
    (BitVec.ofInt w i).setWidth v = BitVec.ofInt v i := by
  apply BitVec.eq_of_toNat_eq
  simp only [BitVec.toNat_setWidth, BitVec.toNat_ofInt]
  apply Int.ofNat_inj.mp
  have hw : (2 ^ w : Int) ≠ 0 :=
    Int.ofNat_ne_zero.mpr (Nat.ne_of_gt (Nat.two_pow_pos w))
  have hv : (2 ^ v : Int) ≠ 0 :=
    Int.ofNat_ne_zero.mpr (Nat.ne_of_gt (Nat.two_pow_pos v))
  calc
    ↑((i % (2 ^ w : Nat)).toNat % 2 ^ v) =
        (↑(i % (2 ^ w : Nat)).toNat : Int) % (2 ^ v : Nat) := Int.natCast_emod _ _
    _ = (i % (2 ^ w : Nat)) % (2 ^ v : Nat) := by
      congr 1
      exact Int.toNat_of_nonneg (Int.emod_nonneg i hw)
    _ = i % (2 ^ v : Nat) :=
      Int.emod_emod_of_dvd i (Int.ofNat_dvd.mpr (Nat.pow_dvd_pow 2 h))
    _ = ↑(i % (2 ^ v : Nat)).toNat :=
      (Int.toNat_of_nonneg (Int.emod_nonneg i hv)).symm

private theorem neon_rounding_as_ofInt (x : BitVec 32) (shift : Nat)
    (h_pos : 0 < shift) (h_bound : shift ≤ 31) :
    neonRoundingShiftRight x shift =
      BitVec.ofInt 32 ((x.toInt + (1 <<< (shift - 1) : Nat)) >>> shift) := by
  simp [neonRoundingShiftRight, Nat.ne_of_gt h_pos, show ¬32 ≤ shift by omega]

theorem rounding_shift_equiv (x : BitVec 32) (shift : Nat)
    (h_bound : shift ≤ 31) :
    neonRoundingShiftRight x shift = rvvRoundingShiftRight x shift := by
  by_cases h_zero : shift = 0
  · subst h_zero
    simp [neonRoundingShiftRight, rvvRoundingShiftRight]
  have h_pos : 0 < shift := Nat.pos_of_ne_zero h_zero
  rw [neon_rounding_as_ofInt x shift h_pos h_bound]
  have h_effective : shift % 32 = shift := Nat.mod_eq_of_lt (by omega)
  simp only [rvvRoundingShiftRight, h_effective, if_neg h_zero]
  have h_cases : shift = 1 ∨ shift = 2 ∨ shift = 3 ∨ shift = 4 ∨ shift = 5 ∨
    shift = 6 ∨ shift = 7 ∨ shift = 8 ∨ shift = 9 ∨ shift = 10 ∨ shift = 11 ∨
    shift = 12 ∨ shift = 13 ∨ shift = 14 ∨ shift = 15 ∨ shift = 16 ∨ shift = 17 ∨
    shift = 18 ∨ shift = 19 ∨ shift = 20 ∨ shift = 21 ∨ shift = 22 ∨ shift = 23 ∨
    shift = 24 ∨ shift = 25 ∨ shift = 26 ∨ shift = 27 ∨ shift = 28 ∨ shift = 29 ∨
    shift = 30 ∨ shift = 31 := by omega
  rcases h_cases with h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h|h
  all_goals subst h
  all_goals split
  all_goals first
    | (change BitVec.ofInt 32 _ = BitVec.ofInt 32 _ + BitVec.ofInt 32 1
       rw [← BitVec.ofInt_add]
       congr 1)
    | congr 1
  all_goals
    simp [BitVec.getLsbD, Nat.testBit_eq_decide_div_mod_eq,
      BitVec.toInt_eq_toNat_cond, Int.shiftRight_eq_div_pow, Nat.shiftLeft_eq] at *
  all_goals split <;> omega

/-- The RVV bit-vector helper is the bit-vector encoding of the architectural
    signed RNU shift result. -/
theorem rvvRoundingShiftRight_eq_roundShiftSigned (x : BitVec 32) (shift : Nat) :
    rvvRoundingShiftRight x shift =
      BitVec.ofInt 32 (roundShiftSigned .rnu x (shift % 32)) := by
  by_cases h : shift % 32 = 0
  · simp [rvvRoundingShiftRight, h, roundShiftSigned, vxrmIncrement]
  · simp only [rvvRoundingShiftRight, h, if_false, roundShiftSigned,
      vxrmIncrement]
    split
    all_goals simp [BitVec.sshiftRight, BitVec.ofInt_add]

private theorem neg_shift_truncate8 (shift : BitVec 32)
    (hLower : 0 <= shift.toInt) (hUpper : shift.toInt <= 31) :
    ((-shift).truncate 8).toInt = -shift.toInt := by
  have hMsb : shift.msb = false := by
    rw [BitVec.msb_eq_toInt]
    simp only [decide_eq_false_iff_not]
    omega
  have hToNat : (shift.toNat : Int) = shift.toInt := by
    symm
    exact BitVec.toInt_eq_toNat_of_msb hMsb
  have hTruncate : (shift.truncate 8).toInt = shift.toInt := by
    rw [BitVec.truncate_eq_setWidth, BitVec.toInt_setWidth]
    rw [Int.bmod_eq_of_le]
    · exact hToNat
    · omega
    · change (shift.toNat : Int) < 128
      rw [hToNat]
      omega
  change ((-shift).setWidth 8).toInt = -shift.toInt
  rw [BitVec.setWidth_neg_of_le (x := shift) (w := 8) (v := 32) (by omega)]
  rw [BitVec.toInt_neg_eq_of_msb]
  exact congrArg Neg.neg hTruncate
  rw [BitVec.msb_eq_toInt, hTruncate]
  simp only [decide_eq_false_iff_not]
  omega

/-- A nonnegative effective count up to 31 has the same lane value when Neon
    receives its negated signed vector count and RVV receives the positive RNU
    shift count. -/
theorem neonSignedShift_eq_rvvRnu (x shift : BitVec 32)
    (hLower : 0 <= shift.toInt) (hUpper : shift.toInt <= 31) :
    (let count := ((-shift).truncate 8).toInt
      if count < 0 then neonRoundingShiftRight x (-count).toNat
      else x.shiftLeft count.toNat) =
      BitVec.ofInt 32 (roundShiftSigned .rnu x shift.toNat) := by
  by_cases hZero : shift.toInt = 0
  · have hShift : shift = 0 := by
      apply BitVec.eq_of_toInt_eq
      simpa using hZero
    subst shift
    simp [roundShiftSigned, vxrmIncrement]
  · have hRaw := neg_shift_truncate8 shift hLower hUpper
    have hMsb : shift.msb = false := by
      rw [BitVec.msb_eq_toInt]
      simp only [decide_eq_false_iff_not]
      omega
    have hNat : shift.toNat = shift.toInt.toNat :=
      (BitVec.toNat_toInt_of_msb shift hMsb).symm
    simp only [hRaw]
    rw [if_pos (by omega)]
    rw [Int.neg_neg, ← hNat]
    rw [rounding_shift_equiv x shift.toNat (by omega)]
    simpa [Nat.mod_eq_of_lt (by omega : shift.toNat < 32)] using
      rvvRoundingShiftRight_eq_roundShiftSigned x shift.toNat

/-- When a nonnegative 32-bit shift is in the architectural right-shift range,
    Neon's signed vector-count lane is the same value as the scalar helper used
    by the per-element kernel model. -/
theorem neonSignedShift_eq_neonRounding (x shift : BitVec 32)
    (hBound : shift.toNat ≤ 31) :
    (let count := ((-shift).truncate 8).toInt
      if count < 0 then neonRoundingShiftRight x (-count).toNat
      else x.shiftLeft count.toNat) =
      neonRoundingShiftRight x shift.toNat := by
  have hShiftInt : shift.toInt = (shift.toNat : Int) := by
    rw [BitVec.toInt_eq_toNat_cond]
    split
    · rfl
    · have hUpper := shift.isLt
      simp at hUpper
      omega
  have hLower : 0 ≤ shift.toInt := by omega
  have hUpper : shift.toInt ≤ 31 := by omega
  calc
    _ = BitVec.ofInt 32 (roundShiftSigned .rnu x shift.toNat) :=
      neonSignedShift_eq_rvvRnu x shift hLower hUpper
    _ = rvvRoundingShiftRight x shift.toNat := by
      rw [rvvRoundingShiftRight_eq_roundShiftSigned]
      rw [Nat.mod_eq_of_lt (by omega : shift.toNat < 32)]
    _ = neonRoundingShiftRight x shift.toNat :=
      (rounding_shift_equiv x shift.toNat hBound).symm

/-- A vector-count `vrshlq_s32` fed by a broadcast negated right shift agrees
    with the scalar right-shift helper on every lane in the reviewed range. -/
theorem vrshlq_s32_vec_replicate_neg_eq_scalar
    (values : List (BitVec 32)) (shift : BitVec 32) (n : Nat)
    (hLength : values.length = n) (hBound : shift.toNat ≤ 31) :
    vrshlq_s32_vec values (List.replicate n (-shift)) =
      vrshlq_s32 values shift.toNat := by
  subst n
  induction values with
  | nil => simp [vrshlq_s32_vec, vrshlq_s32]
  | cons value values ih =>
      simp only [List.length_cons, List.replicate_succ,
        vrshlq_s32_vec, vrshlq_s32, List.zipWith, List.map]
      rw [neonSignedShift_eq_neonRounding value shift hBound]
      congr 1

end SALT.Proof.RoundingEquiv
