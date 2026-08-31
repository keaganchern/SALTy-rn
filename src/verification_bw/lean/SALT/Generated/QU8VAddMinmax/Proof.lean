import SALT.Generated.QU8VAddMinmax.Models
import SALT.Kernel.QU8VAddMinmax.Contract
import SALT.Proof.NarrowingEquiv
import SALT.Proof.RoundingEquiv

namespace SALT.Generated.QU8VAddMinmax

open SALT.Intrinsics
open SALT.Kernel.QU8VAddMinmax
open SALT.Proof.NarrowingEquiv
open SALT.Proof.RoundingEquiv

private def accumulator (p : QU8AddMinmaxParams)
    (a b : BitVec 8) : BitVec 32 :=
  let xa := (a.zeroExtend 16 - p.a_zero_point.zeroExtend 16).signExtend 32
  let xb := (b.zeroExtend 16 - p.b_zero_point.zeroExtend 16).signExtend 32
  xa * p.a_multiplier + xb * p.b_multiplier

private def neonLane (p : QU8AddMinmaxParams)
    (a b : BitVec 8) : BitVec 8 :=
  let acc := accumulator p a b
  let signedShift := (((-p.shift).truncate 32).truncate 8).toInt
  let shifted :=
    if signedShift < 0 then
      Neon.neonRoundingShiftRight acc (-signedShift).toNat
    else acc.shiftLeft signedShift.toNat
  let narrowed := SALT.signedClamp shifted 16
  let withZeroPoint := SALT.signedSatAdd narrowed p.output_zero_point
  let asUnsigned := BitVec.ofInt 8 (max 0 (min withZeroPoint.toInt 255))
  let aboveMin :=
    if asUnsigned.toNat >= p.output_min.toNat then asUnsigned else p.output_min
  if aboveMin.toNat <= p.output_max.toNat then aboveMin else p.output_max

private def rvvLane (p : QU8AddMinmaxParams)
    (a b : BitVec 8) : BitVec 8 :=
  let acc := accumulator p a b
  let shifted :=
    if p.shift.toInt >= 0 then
      BitVec.ofInt 32 (RVV.roundShiftSigned .rnu acc p.shift.toNat)
    else acc.shiftLeft (-p.shift.toInt).toNat
  let narrowed := RVV.vnclipSigned 16 .rdn 0 shifted
  let withZeroPoint := SALT.signedSatAdd narrowed p.output_zero_point
  let nonnegative := SALT.bvSignedMax withZeroPoint (BitVec.ofNat 16 0)
  let asUnsigned := RVV.vnclipUnsigned 8 .rdn 0 nonnegative
  let aboveMin :=
    if asUnsigned.toNat >= p.output_min.toNat then asUnsigned else p.output_min
  if aboveMin.toNat <= p.output_max.toNat then aboveMin else p.output_max

private theorem small_shift_toInt (shift : BitVec 32)
    (h : shift.toNat <= 31) :
    shift.toInt = (shift.toNat : Int) := by
  rw [BitVec.toInt_eq_toNat_cond]
  split
  · rfl
  · have hUpper := shift.isLt
    simp at hUpper
    omega

private theorem lane_equal (p : QU8AddMinmaxParams)
    (a b : BitVec 8) (hShift : p.shift.toNat <= 31) :
    neonLane p a b = rvvLane p a b := by
  let acc := accumulator p a b
  have hShiftInt := small_shift_toInt p.shift hShift
  have hLower : 0 <= p.shift.toInt := by omega
  have hUpper : p.shift.toInt <= 31 := by omega
  have hShifted :
      (if (((-p.shift).truncate 32).truncate 8).toInt < 0 then
          Neon.neonRoundingShiftRight acc
            (-(((-p.shift).truncate 32).truncate 8).toInt).toNat
        else
          acc.shiftLeft
            ((((-p.shift).truncate 32).truncate 8).toInt.toNat)) =
      (if p.shift.toInt >= 0 then
          BitVec.ofInt 32 (RVV.roundShiftSigned .rnu acc p.shift.toNat)
        else acc.shiftLeft (-p.shift.toInt).toNat) := by
    rw [if_pos hLower]
    simpa using neonSignedShift_eq_rvvRnu acc p.shift hLower hUpper
  simp only [neonLane, rvvLane]
  rw [hShifted]
  rw [signedClamp_eq_vnclip_rdn_zero]
  rw [signedToUnsignedClamp_eq_rvv]
  rfl

private theorem exists_cons_of_length_eq_succ {alpha : Type} (n : Nat)
    (xs : List alpha) (h : xs.length = n + 1) :
    exists x tl, xs = x :: tl ∧ tl.length = n := by
  cases xs with
  | nil => simp at h
  | cons x tl =>
      refine ⟨x, tl, rfl, ?_⟩
      simpa using h

private theorem exists_eight_of_length_eq {alpha : Type}
    (xs : List alpha) (h : xs.length = 8) :
    exists x0 x1 x2 x3 x4 x5 x6 x7,
      xs = [x0, x1, x2, x3, x4, x5, x6, x7] := by
  rcases exists_cons_of_length_eq_succ 7 xs h with ⟨x0, xs, rfl, h7⟩
  rcases exists_cons_of_length_eq_succ 6 xs h7 with ⟨x1, xs, rfl, h6⟩
  rcases exists_cons_of_length_eq_succ 5 xs h6 with ⟨x2, xs, rfl, h5⟩
  rcases exists_cons_of_length_eq_succ 4 xs h5 with ⟨x3, xs, rfl, h4⟩
  rcases exists_cons_of_length_eq_succ 3 xs h4 with ⟨x4, xs, rfl, h3⟩
  rcases exists_cons_of_length_eq_succ 2 xs h3 with ⟨x5, xs, rfl, h2⟩
  rcases exists_cons_of_length_eq_succ 1 xs h2 with ⟨x6, xs, rfl, h1⟩
  rcases exists_cons_of_length_eq_succ 0 xs h1 with ⟨x7, xs, rfl, h0⟩
  have hNil : xs = [] := by simpa using h0
  subst xs
  exact ⟨x0, x1, x2, x3, x4, x5, x6, x7, rfl⟩

/-- Equality of the independently generated local blocks whenever the effective
    right shift fits the reviewed Neon/RVV rounding bridge. -/
theorem generated_block_equal_of_shift_le
    (p : QU8AddMinmaxParams)
    (hShift : p.shift.toNat <= 31)
    (inputA inputB : List (BitVec 8))
    (hA : inputA.length = 8) (hB : inputB.length = 8) :
    neonBlock8FromIntrinsics p inputA inputB =
      rvvChunkFromIntrinsics p inputA inputB := by
  have hShiftInt := small_shift_toInt p.shift hShift
  have hNonnegative : p.shift.toInt >= 0 := by omega
  have hShiftMod : p.shift.toNat % 32 = p.shift.toNat := by
    apply Nat.mod_eq_of_lt
    omega
  rcases exists_eight_of_length_eq inputA hA with
    ⟨a0, a1, a2, a3, a4, a5, a6, a7, rfl⟩
  rcases exists_eight_of_length_eq inputB hB with
    ⟨b0, b1, b2, b3, b4, b5, b6, b7, rfl⟩
  have hNeon :
      neonBlock8FromIntrinsics p
          [a0, a1, a2, a3, a4, a5, a6, a7]
          [b0, b1, b2, b3, b4, b5, b6, b7] =
        [neonLane p a0 b0, neonLane p a1 b1, neonLane p a2 b2,
          neonLane p a3 b3, neonLane p a4 b4, neonLane p a5 b5,
          neonLane p a6 b6, neonLane p a7 b7] := by
    rfl
  have hRvv :
      rvvChunkFromIntrinsics p
          [a0, a1, a2, a3, a4, a5, a6, a7]
          [b0, b1, b2, b3, b4, b5, b6, b7] =
        [rvvLane p a0 b0, rvvLane p a1 b1, rvvLane p a2 b2,
          rvvLane p a3 b3, rvvLane p a4 b4, rvvLane p a5 b5,
          rvvLane p a6 b6, rvvLane p a7 b7] := by
    simp [rvvChunkFromIntrinsics, RVV.vwsubu_vx_u16, RVV.vsext_vf2,
      RVV.vmul_vx, RVV.vmacc_vx, RVV.vssra_vx_i32_mode,
      RVV.vnclip_wx_i16_mode, RVV.vsadd_vx, RVV.vmax_vx_i16,
      RVV.vnclipu_wx_u8_mode, RVV.vmaxu_vx_u8, RVV.vminu_vx_u8,
      rvvLane, accumulator, RVV.VXRoundingMode.decode, SALT.sext,
      hNonnegative, hShiftMod]
  rw [hNeon, hRvv]
  change [neonLane p a0 b0, neonLane p a1 b1, neonLane p a2 b2,
      neonLane p a3 b3, neonLane p a4 b4, neonLane p a5 b5,
      neonLane p a6 b6, neonLane p a7 b7] =
    [rvvLane p a0 b0, rvvLane p a1 b1, rvvLane p a2 b2,
      rvvLane p a3 b3, rvvLane p a4 b4, rvvLane p a5 b5,
      rvvLane p a6 b6, rvvLane p a7 b7]
  simp only [List.cons.injEq]
  exact ⟨lane_equal p a0 b0 hShift, lane_equal p a1 b1 hShift,
    lane_equal p a2 b2 hShift, lane_equal p a3 b3 hShift,
    lane_equal p a4 b4 hShift, lane_equal p a5 b5 hShift,
    lane_equal p a6 b6 hShift, lane_equal p a7 b7 hShift, trivial⟩

/-- Contract-bound entry point for the pinned XNNPACK parameter producer. -/
theorem generated_block_equal
    (p : QU8AddMinmaxParams)
    (hwf : WellFormedParams p)
    (inputA inputB : List (BitVec 8))
    (hA : inputA.length = 8) (hB : inputB.length = 8) :
    neonBlock8FromIntrinsics p inputA inputB =
      rvvChunkFromIntrinsics p inputA inputB := by
  unfold WellFormedParams at hwf
  exact generated_block_equal_of_shift_le p (by omega) inputA inputB hA hB

end SALT.Generated.QU8VAddMinmax
