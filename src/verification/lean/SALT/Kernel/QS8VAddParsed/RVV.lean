import SALT.Intrinsics.RVV
import SALT.Core.Tactic
import SALT.Kernel.QS8.Params

namespace SALT.Kernel.QS8VAddParsed.RVV

open SALT
open SALT.Core
open SALT.Intrinsics.RVV
open SALT.Kernel.QS8
def rvvElemFn (p : QS8AddMinmaxParams) (a b : BitVec 8) : BitVec 8 :=
  let xa : BitVec 16 := ((sext a 16) - (sext p.a_zero_point 16))
  let xb : BitVec 16 := ((sext b 16) - (sext p.b_zero_point 16))
  let xa32 : BitVec 32 := (sext xa 32)
  let xb32 : BitVec 32 := (sext xb 32)
  let acc : BitVec 32 := (xa32 * p.a_multiplier)
  let acc : BitVec 32 := (acc + (xb32 * p.b_multiplier))
  let acc : BitVec 32 := ((BVShiftOp.roundShr .rvvRnu).eval acc p.shift.toNat)
  let acc16 : BitVec 16 := (signedClamp acc 16)
  let acc16 : BitVec 16 := (signedSatAdd acc16 p.output_zero_point)
  let out8 : BitVec 8 := (signedClamp acc16 8)
  (bvSignedMin (bvSignedMax out8 p.output_min) p.output_max)

def rvvPipelineFromIntrinsics (p : QS8AddMinmaxParams) (chunk_a chunk_b : List (BitVec 8))
    (h_len : chunk_a.length = chunk_b.length := by simp) : List (BitVec 8) :=
  let vxa := vwsub_vx chunk_a p.a_zero_point
  let vxb := vwsub_vx chunk_b p.b_zero_point
  let vxa32 := vsext_vf2 vxa
  let vxb32 := vsext_vf2 vxb
  let vacc := vmul_vx vxa32 p.a_multiplier
  let vacc := vmacc_vx vacc p.b_multiplier vxb32
    (h := by simp [vacc, vxa32, vxa, vxb32, vxb, h_len])
  let vacc := vssra_vx_rnu vacc p.shift.toNat
  let vacc16 := vnclip_wx_i16 vacc
  let vacc16 := vsadd_vx vacc16 p.output_zero_point
  let vout := vnclip_wx_i8 vacc16
  let vout := vmax_vx vout p.output_min
  vmin_vx vout p.output_max

set_option maxHeartbeats 1600000 in
theorem rvvPipeline_eq_zipWith (p : QS8AddMinmaxParams) (chunk_a chunk_b : List (BitVec 8))
    (h_len : chunk_a.length = chunk_b.length) :
    rvvPipelineFromIntrinsics p chunk_a chunk_b (h_len := h_len) =
    List.zipWith (rvvElemFn p ) chunk_a chunk_b := by
  unfold rvvPipelineFromIntrinsics
  simp_core_unfold [vwsub_vx,
    vsext_vf2,
    vmul_vx,
    vmacc_vx,
    vssra_vx_rnu,
    vnclip_wx_i16,
    vnclip_wx_i8,
    vsadd_vx,
    vmax_vx,
    vmin_vx,
    zipWith_replicate_right,
    List.map_map]
  induction chunk_a generalizing chunk_b with
  | nil => simp [List.zipWith]
  | cons ha ta ih =>
    cases chunk_b with
    | nil => simp at h_len
    | cons hb tb =>
      simp only [List.zipWith, List.map, List.cons.injEq]
      exact ⟨rfl, ih tb (by simpa using h_len)⟩


def rvvIteration (p : QS8AddMinmaxParams) (chunk_a chunk_b : List (BitVec 8))
    (h_len : chunk_a.length = chunk_b.length := by simp) : List (BitVec 8) :=
  rvvPipelineFromIntrinsics p chunk_a chunk_b (h_len := h_len)

theorem rvvIteration_eq_zipWith (p : QS8AddMinmaxParams) (chunk_a chunk_b : List (BitVec 8))
    (h_len : chunk_a.length = chunk_b.length) :
    rvvIteration p chunk_a chunk_b h_len =
      List.zipWith (rvvElemFn p) chunk_a chunk_b := rvvPipeline_eq_zipWith p chunk_a chunk_b h_len

def rvvLoop (p : QS8AddMinmaxParams) (input_a input_b : List (BitVec 8))
    (vlmax : Nat) (h_vlmax : vlmax > 0 := by omega)
    (h_len : input_a.length = input_b.length := by assumption) : List (BitVec 8) :=
  match h_a : input_a with
  | [] => []
  | ha :: ta =>
    match h_b : input_b with
    | [] => []
    | hb :: tb =>
      let xs := ha :: ta
      let ys := hb :: tb
      let vl := min xs.length vlmax
      have h_xs_eq : xs.length = ys.length := h_len
      rvvIteration p (xs.take vl) (ys.take vl)
        (h_len := by simp [List.length_take, h_xs_eq]) ++
      rvvLoop p (xs.drop vl) (ys.drop vl) vlmax h_vlmax
        (h_len := by simp [List.length_drop, h_xs_eq])
termination_by input_a.length
decreasing_by
  simp [List.length_drop]; omega

theorem rvvLoop_eq_zipWith (p : QS8AddMinmaxParams) (input_a input_b : List (BitVec 8))
    (h_len : input_a.length = input_b.length)
    (vlmax : Nat) (h_vlmax : vlmax > 0) :
    rvvLoop p input_a input_b vlmax h_vlmax h_len =
      List.zipWith (rvvElemFn p) input_a input_b := by
  suffices ∀ (n : Nat) (xs ys : List (BitVec 8))
      (h : xs.length = ys.length), xs.length ≤ n →
      rvvLoop p xs ys vlmax h_vlmax h = List.zipWith (rvvElemFn p) xs ys from
    this input_a.length input_a input_b h_len (Nat.le_refl _)
  intro n
  induction n with
  | zero =>
    intro xs ys h_eq h_bound
    have : xs = [] := by cases xs <;> simp_all
    subst this
    have : ys = [] := by cases ys <;> simp_all
    subst this; simp [rvvLoop]
  | succ m ih =>
    intro xs ys h_eq h_bound
    cases xs with
    | nil =>
      have : ys = [] := by cases ys <;> simp_all
      subst this; simp [rvvLoop]
    | cons hd tl =>
      cases ys with
      | nil => simp at h_eq
      | cons hd' tl' =>
        unfold rvvLoop
        simp only [rvvIteration_eq_zipWith]
        have h_drop_eq : ((hd :: tl).drop (min (hd :: tl).length vlmax)).length =
            ((hd' :: tl').drop (min (hd :: tl).length vlmax)).length := by
          simp only [List.length_drop, h_eq]
        have h_drop_le : ((hd :: tl).drop (min (hd :: tl).length vlmax)).length ≤ m := by
          simp only [List.length_drop, List.length_cons]
          have := h_bound; simp only [List.length_cons] at this; omega
        rw [ih _ _ h_drop_eq h_drop_le]
        exact zipWith_take_append_drop (rvvElemFn p) (hd :: tl) (hd' :: tl')
          (min (hd :: tl).length vlmax) h_eq

end SALT.Kernel.QS8VAddParsed.RVV
