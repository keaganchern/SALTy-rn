import SALT.Generated.QS8VCvt.Models
import SALT.Kernel.QS8VCvt.Contract
import SALT.Proof.QrdmulhEquiv

namespace SALT.Generated.QS8VCvt

open SALT.Kernel.QS8VCvt
open SALT.Proof.QrdmulhEquiv

private theorem shifted_difference_range (z : BitVec 16) (x : BitVec 8)
    (hzLower : -128 <= z.toInt) (hzUpper : z.toInt <= 127) :
    let a := (z - SALT.sext x 16).shiftLeft 7
    a.toInt = (z.toInt - x.toInt) * 128
      ∧ -32640 <= a.toInt ∧ a.toInt <= 32640 := by
  have hxLower := @BitVec.le_toInt 8 x
  have hxUpper := @BitVec.toInt_lt 8 x
  simp at hxLower hxUpper
  have hsext : (SALT.sext x 16).toInt = x.toInt := by
    exact BitVec.toInt_signExtend_of_le (by omega)
  have hsub : (z - SALT.sext x 16).toInt = z.toInt - x.toInt := by
    rw [BitVec.toInt_sub, hsext]
    rw [Int.bmod_eq_of_le]
    all_goals simp
    all_goals omega
  have hsubBv : z - SALT.sext x 16 = BitVec.ofInt 16 (z.toInt - x.toInt) := by
    apply BitVec.eq_of_toInt_eq
    rw [hsub, BitVec.toInt_ofInt_eq_self (by omega)]
    all_goals omega
  have hshiftBv :
      (z - SALT.sext x 16) <<< 7 =
        BitVec.ofInt 16 ((z.toInt - x.toInt) * 128) := by
    rw [hsubBv, BitVec.shiftLeft_eq_mul_twoPow]
    change
      BitVec.ofInt 16 (z.toInt - x.toInt) * BitVec.ofInt 16 128 = _
    rw [← BitVec.ofInt_mul]
  dsimp
  rw [hshiftBv, BitVec.toInt_ofInt_eq_self (by omega)]
  all_goals omega

private theorem truncate_neg (m : BitVec 32) :
    -(m.truncate 16) = (-m).truncate 16 := by
  apply BitVec.eq_of_toNat_eq
  simp [BitVec.toNat_neg]

def neonLane (p : QS8CvtParams) (x : BitVec 8) : BitVec 8 :=
  let a := (p.input_zero_point - SALT.sext x 16).shiftLeft 7
  SALT.signedClamp
    (SALT.signedSatAdd
      (SALT.Intrinsics.Neon.sqrdmulh_s16 a (-(p.multiplier.truncate 16)))
      p.output_zero_point) 8

def rvvLane (p : QS8CvtParams) (x : BitVec 8) : BitVec 8 :=
  let a := (p.input_zero_point - SALT.sext x 16).shiftLeft 7
  let b := (-p.multiplier).truncate 16
  let product := BitVec.ofInt 32 (a.toInt * b.toInt)
  SALT.Intrinsics.RVV.vnclipSigned 8 .rdn 0
    (SALT.signedSatAdd
      (SALT.Intrinsics.RVV.vnclipSigned 16 .rnu 16 (product.shiftLeft 1))
      p.output_zero_point)

theorem lane_equal (p : QS8CvtParams) (x : BitVec 8)
    (hzLower : -128 <= p.input_zero_point.toInt)
    (hzUpper : p.input_zero_point.toInt <= 127) :
    neonLane p x = rvvLane p x := by
  have hRange :=
    shifted_difference_range p.input_zero_point x hzLower hzUpper
  dsimp only at hRange
  simp only [neonLane, rvvLane]
  rw [truncate_neg]
  rw [sqrdmulh_eq_rvv_of_left_ne_min _ _ (by omega)]
  exact signedClamp_eq_vnclip_rdn_zero _

private theorem exists_cons_of_length_eq_succ {α : Type} (n : Nat)
    (xs : List α) (h : xs.length = n + 1) :
    ∃ x tl, xs = x :: tl ∧ tl.length = n := by
  cases xs with
  | nil => simp at h
  | cons x tl =>
      refine ⟨x, tl, rfl, ?_⟩
      simpa using h

private theorem exists_eight_of_length_eq {α : Type}
    (xs : List α) (h : xs.length = 8) :
    ∃ x0 x1 x2 x3 x4 x5 x6 x7,
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

/-- Equality of the independently generated local blocks under the XNNPACK
    parameter contract. This theorem is about lane values, not saturation flags. -/
theorem generated_block_equal
    (p : QS8CvtParams)
    (hwf : WellFormedParams p)
    (input : List (BitVec 8))
    (hLength : input.length = 8) :
    neonBlock8FromIntrinsics p input = rvvChunkFromIntrinsics p input := by
  have hzLower : -128 <= p.input_zero_point.toInt := hwf.1
  have hzUpper : p.input_zero_point.toInt <= 127 := hwf.2.1
  rcases exists_eight_of_length_eq input hLength with
    ⟨x0, x1, x2, x3, x4, x5, x6, x7, rfl⟩
  change [neonLane p x0, neonLane p x1, neonLane p x2, neonLane p x3,
    neonLane p x4, neonLane p x5, neonLane p x6, neonLane p x7] =
    [rvvLane p x0, rvvLane p x1, rvvLane p x2, rvvLane p x3,
      rvvLane p x4, rvvLane p x5, rvvLane p x6, rvvLane p x7]
  simp only [List.cons.injEq]
  exact ⟨lane_equal p x0 hzLower hzUpper,
    lane_equal p x1 hzLower hzUpper,
    lane_equal p x2 hzLower hzUpper,
    lane_equal p x3 hzLower hzUpper,
    lane_equal p x4 hzLower hzUpper,
    lane_equal p x5 hzLower hzUpper,
    lane_equal p x6 hzLower hzUpper,
    lane_equal p x7 hzLower hzUpper, trivial⟩

theorem neonBlock8FromIntrinsics_eq_map (p : QS8CvtParams)
    (input : List (BitVec 8)) (hLength : input.length = 8) :
    neonBlock8FromIntrinsics p input = input.map (neonLane p) := by
  rcases exists_eight_of_length_eq input hLength with
    ⟨x0, x1, x2, x3, x4, x5, x6, x7, rfl⟩
  rfl

theorem rvvChunkFromIntrinsics_eq_map (p : QS8CvtParams)
    (input : List (BitVec 8)) :
    rvvChunkFromIntrinsics p input = input.map (rvvLane p) := by
  simp [rvvChunkFromIntrinsics, rvvLane, SALT.Intrinsics.RVV.vsext_vf2_i16,
    SALT.Intrinsics.RVV.vrsub_vx_i16, SALT.Intrinsics.RVV.vsll_vx_i16,
    SALT.Intrinsics.RVV.vwmul_vx_i32, SALT.Intrinsics.RVV.vsll_vx_i32,
    SALT.Intrinsics.RVV.vnclip_wx_i16_mode, SALT.Intrinsics.RVV.vsadd_vx,
    SALT.Intrinsics.RVV.vnclip_wx_i8_mode, List.map_map, Function.comp_def,
    SALT.Intrinsics.RVV.VXRoundingMode.decode]

theorem neonPartialTailLivePrefixFromIntrinsics_eq_take_map
    (p : QS8CvtParams) (loaded : List (BitVec 8)) (hLength : loaded.length = 8)
    (live : Nat) (hLive : live < 8) :
    neonPartialTailLivePrefixFromIntrinsics p loaded live =
      (loaded.map (neonLane p)).take live := by
  change SALT.Kernel.Schedule.littleEndianPrefixStore8
    (neonBlock8FromIntrinsics p loaded) live = _
  rw [SALT.Kernel.Schedule.littleEndianPrefixStore8_eq_take _
    (by simp [neonBlock8FromIntrinsics_eq_map, hLength]) _ hLive]
  rw [neonBlock8FromIntrinsics_eq_map p loaded hLength]

theorem neonPartialTailWithOverread_eq_map (p : QS8CvtParams)
    (input overread : List (BitVec 8)) (hLength : input.length < 8)
    (hOverread : 8 - input.length <= overread.length) :
    let loaded := (input ++ overread).take 8
    neonPartialTailLivePrefixFromIntrinsics p loaded input.length =
      input.map (neonLane p) := by
  dsimp only
  let loaded := (input ++ overread).take 8
  have hLoaded : loaded.length = 8 := by
    simp [loaded, List.length_take]
    omega
  rw [neonPartialTailLivePrefixFromIntrinsics_eq_take_map
    p loaded hLoaded input.length hLength]
  have hLoadedPrefix : loaded.take input.length = input := by
    simp only [loaded, List.take_take]
    rw [show min input.length 8 = input.length by omega]
    simp
  rw [<- List.map_take, hLoadedPrefix]

theorem neonValueLoopWithOverreadFromIntrinsics_eq_map (p : QS8CvtParams)
    (input overread : List (BitVec 8)) (hOverread : 7 <= overread.length) :
    neonValueLoopWithOverreadFromIntrinsics p input overread =
      input.map (neonLane p) := by
  unfold neonValueLoopWithOverreadFromIntrinsics
  apply SALT.Kernel.Schedule.runFixedChunkTail_eq_map 8 (by decide)
      (neonBlock8FromIntrinsics p) _ (neonLane p)
  · exact neonBlock8FromIntrinsics_eq_map p
  · intro tail _ hTail
    exact neonPartialTailWithOverread_eq_map p tail overread hTail (by omega)

theorem neonValueLoopFromIntrinsics_eq_map (p : QS8CvtParams)
    (input : List (BitVec 8)) :
    neonValueLoopFromIntrinsics p input = input.map (neonLane p) := by
  unfold neonValueLoopFromIntrinsics
  exact neonValueLoopWithOverreadFromIntrinsics_eq_map p input _ (by simp)

theorem rvvValueLoopFromIntrinsics_eq_map (p : QS8CvtParams)
    (input : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length) :
    rvvValueLoopFromIntrinsics p input schedule = input.map (rvvLane p) :=
  SALT.Kernel.Schedule.processBlocks_eq_map _ _
    (rvvChunkFromIntrinsics_eq_map p) input schedule

/-- Arbitrary-length output-value equality for every complete positive RVV
    partition. This does not establish C-memory, tail-overread, or ISA adequacy. -/
theorem allLengthsValueEqualWithOverread (p : QS8CvtParams)
    (hwf : WellFormedParams p) (input overread : List (BitVec 8))
    (hOverread : 7 <= overread.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length) :
    neonValueLoopWithOverreadFromIntrinsics p input overread =
      rvvValueLoopFromIntrinsics p input schedule := by
  rw [neonValueLoopWithOverreadFromIntrinsics_eq_map p input overread hOverread]
  rw [rvvValueLoopFromIntrinsics_eq_map p input schedule]
  apply List.map_congr_left
  intro x _
  exact lane_equal p x hwf.1 hwf.2.1

end SALT.Generated.QS8VCvt
