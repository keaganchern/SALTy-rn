import SALT.Intrinsics.Neon
import SALT.Core.Tactic
import SALT.Kernel.QS8.Params

namespace SALT.Kernel.QS8VAddCParsedFully.Neon

open SALT
open SALT.Core
open SALT.Intrinsics.Neon
open SALT.Kernel.QS8
def computeBias (p : QS8AddMinmaxParams) (input_b : BitVec 8) : BitVec 32 :=
  let vxb : BitVec 32 := ((sext input_b 32) - (sext p.b_zero_point 32))
  (vxb * p.b_multiplier)

def neonElemFn (p : QS8AddMinmaxParams) (bias : BitVec 32) (x : BitVec 8) : BitVec 8 :=
  let vxa01234567 : BitVec 16 := ((sext x 16) - (sext p.a_zero_point 16))
  let vacc01234567 : BitVec 32 := (bias + ((sext vxa01234567 32) * p.a_multiplier))
  let vacc01234567 : BitVec 32 := ((BVShiftOp.roundShr .neon).eval vacc01234567 p.shift.toNat)
  let vacc01234567 : BitVec 16 := (signedSatAdd (signedClamp vacc01234567 16) p.output_zero_point)
  let vout01234567 : BitVec 8 := (signedClamp vacc01234567 8)
  let vout01234567 : BitVec 8 := (bvSignedMax vout01234567 p.output_min)
  (bvSignedMin vout01234567 p.output_max)

def neonPipelineFromIntrinsics (p : QS8AddMinmaxParams) (bias : BitVec 32) (chunk : List (BitVec 8)) : List (BitVec 8) :=
  let vxa01234567 := vsubl_s8 chunk (List.replicate chunk.length p.a_zero_point) (h := by simp)
  let vacc01234567 := vmlaq_s32 (List.replicate chunk.length bias) (vmovl_s16 vxa01234567) p.a_multiplier
    (h := by simp [vxa01234567])
  let vacc01234567 := vrshlq_s32 vacc01234567 p.shift.toNat
  let vacc01234567 := vqaddq_s16 (vqmovn_s32 vacc01234567) p.output_zero_point
  let vout01234567 := vqmovn_s16 vacc01234567
  let vout01234567 := vmax_s8 vout01234567 p.output_min
  vmin_s8 vout01234567 p.output_max

set_option maxHeartbeats 800000 in
theorem neonPipeline_eq_map (p : QS8AddMinmaxParams) (bias : BitVec 32) (chunk : List (BitVec 8)) :
    neonPipelineFromIntrinsics p bias chunk = chunk.map (neonElemFn p bias ):= by
  unfold neonPipelineFromIntrinsics
  simp_core_unfold [vsubl_s8,
    vmovl_s16,
    vmlaq_s32,
    vrshlq_s32,
    vqmovn_s32,
    vqmovn_s16,
    vqaddq_s16,
    vmax_s8,
    vmin_s8,
    zipWith_replicate_left,
    zipWith_replicate_right,
    List.map_map,
    List.length_map]
  try congr 1; try { ext; rfl }


def neonIteration (p : QS8AddMinmaxParams) (bias : BitVec 32) (chunk : List (BitVec 8)) : List (BitVec 8) :=
  neonPipelineFromIntrinsics p bias chunk

theorem neonIteration_eq_map (p : QS8AddMinmaxParams) (bias : BitVec 32) (chunk : List (BitVec 8)) :
    neonIteration p bias chunk =
      chunk.map (neonElemFn p bias ):= neonPipeline_eq_map p bias chunk

def neonLoop (p : QS8AddMinmaxParams) (bias : BitVec 32) (input : List (BitVec 8)) : List (BitVec 8) :=
  if input.length ≥ 8 then
    neonIteration p bias (input.take 8) ++
      neonLoop p bias (input.drop 8)
  else if input.length > 0 then
    let padded := input ++ List.replicate (8 - input.length) (BitVec.ofNat 8 0)
    (neonIteration p bias padded).take input.length
  else []
termination_by input.length
decreasing_by all_goals (simp_all [List.length_drop]; omega)

theorem neonLoop_eq_map (p : QS8AddMinmaxParams) (bias : BitVec 32) (input : List (BitVec 8)) :
    neonLoop p bias input =
      input.map (neonElemFn p bias ):= by
  suffices ∀ (n : Nat) (xs : List (BitVec 8)), xs.length ≤ n →
      neonLoop p bias xs =
        xs.map (neonElemFn p bias )from
    this input.length input (Nat.le_refl _)
  intro n
  induction n with
  | zero =>
    intro xs h; have : xs = [] := by cases xs <;> simp_all
    subst this; simp [neonLoop]
  | succ m ih =>
    intro xs h; cases xs with
    | nil => simp [neonLoop]
    | cons hd tl =>
      unfold neonLoop
      simp only [neonIteration_eq_map]
      have h_cons_len : (hd :: tl).length = tl.length + 1 := by simp
      split
      · have h_drop_le : ((hd :: tl).drop 8).length ≤ m := by
          simp [List.length_drop]; omega
        rw [ih _ h_drop_le, ← List.map_append, List.take_append_drop]
      · split
        · exact map_append_take _ (hd :: tl) _
        · omega

end SALT.Kernel.QS8VAddCParsedFully.Neon
