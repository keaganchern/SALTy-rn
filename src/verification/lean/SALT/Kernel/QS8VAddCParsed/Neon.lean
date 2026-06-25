import SALT.Intrinsics.Neon
import SALT.Core.Tactic
import SALT.Kernel.QS8.Params

namespace SALT.Kernel.QS8VAddCParsed.Neon

open SALT
open SALT.Core
open SALT.Intrinsics.Neon
open SALT.Kernel.QS8
def computeBias (p : QS8AddMinmaxParams) (input_b : BitVec 8) : BitVec 32 :=
  let vxb : BitVec 32 := ((sext input_b 32) - (sext p.b_zero_point 32))
  (vxb * p.b_multiplier)
def neonElemFn (p : QS8AddMinmaxParams) (bias : BitVec 32) (x : BitVec 8) : BitVec 8 :=
  let xa : BitVec 16 := ((sext x 16) - (sext p.a_zero_point 16))
  let xa32 : BitVec 32 := (sext xa 32)
  let acc : BitVec 32 := (bias + (xa32 * p.a_multiplier))
  let acc : BitVec 32 := ((BVShiftOp.roundShr .neon).eval acc p.shift.toNat)
  let acc16 : BitVec 16 := (signedClamp acc 16)
  let acc16 : BitVec 16 := (signedSatAdd acc16 p.output_zero_point)
  let out8 : BitVec 8 := (signedClamp acc16 8)
  (bvSignedMin (bvSignedMax out8 p.output_min) p.output_max)

def neonPipelineFromIntrinsics (p : QS8AddMinmaxParams) (bias : BitVec 32) (chunk : List (BitVec 8)) : List (BitVec 8) :=
  let va_zero_point := List.replicate chunk.length p.a_zero_point
  let vxa := vsubl_s8 chunk va_zero_point (h := by simp [va_zero_point])
  let vxa32 := vmovl_s16 vxa
  let vbias := List.replicate chunk.length bias
  let vacc := vmlaq_s32 vbias vxa32 p.a_multiplier
    (h := by simp [vbias, vxa32, vxa, va_zero_point])
  let vacc := vrshlq_s32 vacc p.shift.toNat
  let vacc16 := vqmovn_s32 vacc
  let vacc16 := vqaddq_s16 vacc16 p.output_zero_point
  let vout := vqmovn_s16 vacc16
  let vout := vmax_s8 vout p.output_min
  vmin_s8 vout p.output_max

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
    zipWith_replicate_right,
    zipWith_replicate_left,
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

end SALT.Kernel.QS8VAddCParsed.Neon
