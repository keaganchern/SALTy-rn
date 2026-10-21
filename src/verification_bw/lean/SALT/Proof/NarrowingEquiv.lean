import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV

namespace SALT.Proof.NarrowingEquiv

open SALT.Intrinsics.RVV

/-- RDN with a zero shift is a signed saturating narrow for arbitrary source
    and destination widths. -/
theorem signedClamp_eq_vnclip_rdn_zero
    {sourceWidth : Nat} (destinationWidth : Nat) (x : BitVec sourceWidth) :
    SALT.signedClamp x destinationWidth =
      vnclipSigned destinationWidth .rdn 0 x := by
  simp [SALT.signedClamp, vnclipSigned, saturateSignedInt,
    roundShiftSigned, vxrmIncrement]

/-- Neon signed-to-unsigned saturation equals RVV signed max with zero followed
    by an unsigned RDN narrow with a zero shift. -/
theorem signedToUnsignedClamp_eq_rvv (x : BitVec 16) :
    BitVec.ofInt 8 (max 0 (min x.toInt 255)) =
      vnclipUnsigned 8 .rdn 0 (SALT.bvSignedMax x 0) := by
  by_cases h : 0 <= x.toInt
  · have hMax : SALT.bvSignedMax x 0 = x := by
      have hGe : x.toInt >= (0 : BitVec 16).toInt := by simp; omega
      unfold SALT.bvSignedMax
      rw [if_pos hGe]
    rw [hMax]
    have hMsb : x.msb = false := by
      rw [BitVec.msb_eq_toInt]
      simp only [decide_eq_false_iff_not]
      omega
    have hToNat : (x.toNat : Int) = x.toInt := by
      symm
      exact BitVec.toInt_eq_toNat_of_msb hMsb
    simp only [vnclipUnsigned, saturateUnsignedNat, roundShiftUnsigned,
      vxrmIncrement, Bool.false_eq_true, reduceIte,
      Nat.div_one, Nat.add_zero, Nat.reducePow, Nat.reduceSub]
    have hClamp : max 0 (min x.toInt 255) = min x.toInt 255 := by omega
    rw [hClamp]
    by_cases hUpper : x.toInt <= 255
    · rw [Int.min_eq_left hUpper]
      rw [Nat.min_eq_left (by omega)]
      apply BitVec.eq_of_toNat_eq
      simp only [BitVec.toNat_ofInt, BitVec.toNat_ofNat]
      omega
    · rw [Int.min_eq_right (by omega)]
      rw [Nat.min_eq_right (by omega)]
      rfl
  · have hNegative : x.toInt < 0 := by omega
    have hMax : SALT.bvSignedMax x 0 = 0 := by
      have hNot : Not (x.toInt >= (0 : BitVec 16).toInt) := by simp; omega
      unfold SALT.bvSignedMax
      rw [if_neg hNot]
    have hClamp : max 0 (min x.toInt 255) = 0 := by omega
    rw [hMax, hClamp]
    rfl

end SALT.Proof.NarrowingEquiv
