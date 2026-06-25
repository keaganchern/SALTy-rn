import SALT.Intrinsics.RVV
import SALT.Core.Tactic
import SALT.Kernel.QS8.Params

namespace SALT.Kernel.QS8VAddCEmit.RVV

open SALT
open SALT.Core
open SALT.Intrinsics.RVV
open SALT.Kernel.QS8
def computeBias (p : QS8AddMinmaxParams) (input_b : BitVec 8) : BitVec 32 :=
  let vxb : BitVec 32 := ((sext input_b 32) - (sext p.b_zero_point 32))
  (vxb * p.b_multiplier)
def rvvElemFn (p : QS8AddMinmaxParams) (bias : BitVec 32) (x : BitVec 8) : BitVec 8 :=
  let xa : BitVec 16 := ((sext x 16) - (sext p.a_zero_point 16))
  let xa32 : BitVec 32 := (sext xa 32)
  let acc : BitVec 32 := (bias + (xa32 * p.a_multiplier))
  let acc : BitVec 32 := ((BVShiftOp.roundShr .rvvRnu).eval acc p.shift.toNat)
  let acc16 : BitVec 16 := (signedClamp acc 16)
  let acc16 : BitVec 16 := (signedSatAdd acc16 p.output_zero_point)
  let out8 : BitVec 8 := (signedClamp acc16 8)
  (bvSignedMin (bvSignedMax out8 p.output_min) p.output_max)

def rvvPipelineFromIntrinsics (p : QS8AddMinmaxParams) (bias : BitVec 32) (chunk : List (BitVec 8)) : List (BitVec 8) :=
  let vxa := vwsub_vx chunk p.a_zero_point
  let vxa32 := vsext_vf2 vxa
  let vbias := List.replicate chunk.length bias
  let vacc := vmacc_vx vbias p.a_multiplier vxa32
    (h := by simp [vbias, vxa32, vxa])
  let vacc := vssra_vx_rnu vacc p.shift.toNat
  let vacc16 := vnclip_wx_i16 vacc
  let vacc16 := vsadd_vx vacc16 p.output_zero_point
  let vout := vnclip_wx_i8 vacc16
  let vout := vmax_vx vout p.output_min
  vmin_vx vout p.output_max

set_option maxHeartbeats 800000 in
theorem rvvPipeline_eq_map (p : QS8AddMinmaxParams) (bias : BitVec 32) (chunk : List (BitVec 8)) :
    rvvPipelineFromIntrinsics p bias chunk = chunk.map (rvvElemFn p bias ):= by
  unfold rvvPipelineFromIntrinsics
  simp_core_unfold [vwsub_vx,
    vsext_vf2,
    vmacc_vx,
    vssra_vx_rnu,
    vnclip_wx_i16,
    vnclip_wx_i8,
    vsadd_vx,
    vmax_vx,
    vmin_vx,
    zipWith_replicate_left,
    zipWith_replicate_right,
    List.map_map,
    List.length_map]
  try congr 1; try { ext; rfl }


def rvvIteration (p : QS8AddMinmaxParams) (bias : BitVec 32) (chunk : List (BitVec 8)) : List (BitVec 8) :=
  rvvPipelineFromIntrinsics p bias chunk

theorem rvvIteration_eq_map (p : QS8AddMinmaxParams) (bias : BitVec 32) (chunk : List (BitVec 8)) :
    rvvIteration p bias chunk =
      chunk.map (rvvElemFn p bias ):= rvvPipeline_eq_map p bias chunk

def rvvLoop (p : QS8AddMinmaxParams) (bias : BitVec 32) (input : List (BitVec 8))
    (vlmax : Nat) (h_vlmax : vlmax > 0 := by omega) : List (BitVec 8) :=
  match input with
  | [] => []
  | hd :: tl =>
    let xs := hd :: tl
    let vl := min xs.length vlmax
    rvvIteration p bias (xs.take vl) ++
      rvvLoop p bias (xs.drop vl) vlmax
termination_by input.length
decreasing_by
  simp [List.length_drop]; omega

theorem rvvLoop_eq_map (p : QS8AddMinmaxParams) (bias : BitVec 32) (input : List (BitVec 8))
    (vlmax : Nat) (h_vlmax : vlmax > 0) :
    rvvLoop p bias input vlmax =
      input.map (rvvElemFn p bias ):= by
  suffices ∀ (n : Nat) (xs : List (BitVec 8)), xs.length ≤ n →
      rvvLoop p bias xs vlmax =
        xs.map (rvvElemFn p bias )from
    this input.length input (Nat.le_refl _)
  intro n
  induction n with
  | zero =>
    intro xs h; have : xs = [] := by cases xs <;> simp_all
    subst this; simp [rvvLoop]
  | succ m ih =>
    intro xs h; cases xs with
    | nil => simp [rvvLoop]
    | cons hd tl =>
      unfold rvvLoop
      simp only [rvvIteration_eq_map]
      have h_cons_len : (hd :: tl).length = tl.length + 1 := by simp
      have h_drop_le :
          ((hd :: tl).drop (min (hd :: tl).length vlmax)).length ≤ m := by
        simp [List.length_drop]; omega
      rw [ih _ h_drop_le, ← List.map_append, List.take_append_drop]

end SALT.Kernel.QS8VAddCEmit.RVV
