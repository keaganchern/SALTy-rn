import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV

namespace SALT.Proof.QrdmulhEquiv

open SALT.Intrinsics.Neon
open SALT.Intrinsics.RVV

private theorem rnu_round_shift_16 (x : BitVec 32) :
    ((x.toInt + 32768) >>> 16) = roundShiftSigned .rnu x 16 := by
  simp only [roundShiftSigned, vxrmIncrement, OfNat.ofNat, Nat.reduceSub]
  split
  all_goals
    simp [BitVec.getLsbD, Nat.testBit_eq_decide_div_mod_eq,
      BitVec.toInt_eq_toNat_cond, Int.shiftRight_eq_div_pow] at *
  all_goals split <;> omega

private theorem doubled_product_no_wrap (a b : BitVec 16)
    (haLower : -32767 <= a.toInt) (haUpper : a.toInt <= 32767) :
    ((BitVec.ofInt 32 (a.toInt * b.toInt)).shiftLeft 1).toInt =
      2 * a.toInt * b.toInt := by
  have hbLower := @BitVec.le_toInt 16 b
  have hbUpper := @BitVec.toInt_lt 16 b
  simp at hbLower hbUpper
  have haAbs : a.toInt.natAbs <= 32767 := by
    apply Int.ofNat_le.mp
    by_cases ha : 0 <= a.toInt
    · rw [Int.ofNat_natAbs_of_nonneg ha]
      omega
    · rw [Int.ofNat_natAbs_of_nonpos (by omega)]
      omega
  have hbAbs : b.toInt.natAbs <= 32768 := by
    apply Int.ofNat_le.mp
    by_cases hb : 0 <= b.toInt
    · rw [Int.ofNat_natAbs_of_nonneg hb]
      omega
    · rw [Int.ofNat_natAbs_of_nonpos (by omega)]
      omega
  have productUpper : a.toInt * b.toInt <= 32767 * 32768 :=
    Int.mul_le_mul_of_natAbs_le haAbs hbAbs
  have productLower : -(32767 * 32768 : Int) <= a.toInt * b.toInt := by
    have hNeg := Int.mul_le_mul_of_natAbs_le haAbs
      (show (-b.toInt).natAbs <= 32768 by simpa using hbAbs)
    simp only [Int.mul_neg] at hNeg
    omega
  change ((BitVec.ofInt 32 (a.toInt * b.toInt)) <<< 1).toInt = _
  rw [BitVec.shiftLeft_eq_mul_twoPow]
  change
    (BitVec.ofInt 32 (a.toInt * b.toInt) * BitVec.ofInt 32 2).toInt = _
  rw [← BitVec.ofInt_mul]
  rw [BitVec.toInt_ofInt_eq_self (by omega) (by omega) (by omega)]
  simp [Int.mul_comm, Int.mul_left_comm]

/-- Away from the unique `(-32768) * (-32768)` saturating corner, the RVV
    widening-multiply, wrapping double, and RNU narrow sequence has the same
    lane value as Neon signed qrdmulh. This statement does not model QC/vxsat. -/
theorem sqrdmulh_eq_rvv_of_left_ne_min (a b : BitVec 16)
    (ha : a.toInt ≠ -32768) :
    sqrdmulh_s16 a b =
      vnclipSigned 16 .rnu 16
        ((BitVec.ofInt 32 (a.toInt * b.toInt)).shiftLeft 1) := by
  have haLower := @BitVec.le_toInt 16 a
  have haUpper := @BitVec.toInt_lt 16 a
  simp at haLower haUpper
  have hdoubled := doubled_product_no_wrap a b (by omega) (by omega)
  simp only [sqrdmulh_s16, vnclipSigned, saturateSignedInt]
  rw [← rnu_round_shift_16]
  rw [hdoubled]
  rfl

/-- RDN with a zero shift is the RVV value-level counterpart of a signed
    saturating narrow. -/
theorem signedClamp_eq_vnclip_rdn_zero (x : BitVec 16) :
    SALT.signedClamp x 8 = vnclipSigned 8 .rdn 0 x := by
  simp [SALT.signedClamp, vnclipSigned, saturateSignedInt,
    roundShiftSigned, vxrmIncrement]

end SALT.Proof.QrdmulhEquiv
