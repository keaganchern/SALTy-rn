import SALT.Intrinsics.Neon
import SALT.Core.Tactic
import SALT.Kernel.QS8.Params

namespace SALT.Kernel.QS8VAddParsed.Neon

open SALT
open SALT.Core
open SALT.Intrinsics.Neon
open SALT.Kernel.QS8
def neonElemFn (p : QS8AddMinmaxParams) (a b : BitVec 8) : BitVec 8 :=
  let xa : BitVec 16 := ((sext a 16) - (sext p.a_zero_point 16))
  let xb : BitVec 16 := ((sext b 16) - (sext p.b_zero_point 16))
  let xa32 : BitVec 32 := (sext xa 32)
  let xb32 : BitVec 32 := (sext xb 32)
  let acc : BitVec 32 := (xa32 * p.a_multiplier)
  let acc : BitVec 32 := (acc + (xb32 * p.b_multiplier))
  let acc : BitVec 32 := ((BVShiftOp.roundShr .neon).eval acc p.shift.toNat)
  let acc16 : BitVec 16 := (signedClamp acc 16)
  let acc16 : BitVec 16 := (signedSatAdd acc16 p.output_zero_point)
  let out8 : BitVec 8 := (signedClamp acc16 8)
  (bvSignedMin (bvSignedMax out8 p.output_min) p.output_max)

def neonPipelineFromIntrinsics (p : QS8AddMinmaxParams) (chunk_a chunk_b : List (BitVec 8))
    (h_len : chunk_a.length = chunk_b.length := by simp) : List (BitVec 8) :=
  let va_zp := List.replicate chunk_a.length p.a_zero_point
  let vb_zp := List.replicate chunk_b.length p.b_zero_point
  let vxa := vsubl_s8 chunk_a va_zp (h := by simp [va_zp])
  let vxb := vsubl_s8 chunk_b vb_zp (h := by simp [vb_zp])
  let vxa32 := vmovl_s16 vxa
  let vxb32 := vmovl_s16 vxb
  let vacc := vmulq_s32 vxa32 p.a_multiplier
  let vacc := vmlaq_s32 vacc vxb32 p.b_multiplier
    (h := by simp [vacc, vxa32, vxa, va_zp, vxb32, vxb, vb_zp, h_len])
  let vacc := vrshlq_s32 vacc p.shift.toNat
  let vacc16 := vqmovn_s32 vacc
  let vacc16 := vqaddq_s16 vacc16 p.output_zero_point
  let vout := vqmovn_s16 vacc16
  let vout := vmax_s8 vout p.output_min
  vmin_s8 vout p.output_max

set_option maxHeartbeats 1600000 in
theorem neonPipeline_eq_zipWith (p : QS8AddMinmaxParams) (chunk_a chunk_b : List (BitVec 8))
    (h_len : chunk_a.length = chunk_b.length) :
    neonPipelineFromIntrinsics p chunk_a chunk_b (h_len := h_len) =
    List.zipWith (neonElemFn p ) chunk_a chunk_b := by
  unfold neonPipelineFromIntrinsics
  simp_core_unfold [vsubl_s8,
    vmovl_s16,
    vmulq_s32,
    vmlaq_s32,
    vrshlq_s32,
    vqmovn_s32,
    vqmovn_s16,
    vqaddq_s16,
    vmax_s8,
    vmin_s8,
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


def neonIteration (p : QS8AddMinmaxParams) (chunk_a chunk_b : List (BitVec 8))
    (h_len : chunk_a.length = chunk_b.length := by simp) : List (BitVec 8) :=
  neonPipelineFromIntrinsics p chunk_a chunk_b (h_len := h_len)

theorem neonIteration_eq_zipWith (p : QS8AddMinmaxParams) (chunk_a chunk_b : List (BitVec 8))
    (h_len : chunk_a.length = chunk_b.length) :
    neonIteration p chunk_a chunk_b h_len =
      List.zipWith (neonElemFn p) chunk_a chunk_b := neonPipeline_eq_zipWith p chunk_a chunk_b h_len

def neonLoop (p : QS8AddMinmaxParams) (input_a input_b : List (BitVec 8))
    (h_len : input_a.length = input_b.length := by simp) : List (BitVec 8) :=
  if input_a.length ≥ 8 then
    neonIteration p (input_a.take 8) (input_b.take 8)
      (h_len := by simp [List.length_take, h_len]) ++
    neonLoop p (input_a.drop 8) (input_b.drop 8)
      (h_len := by simp [List.length_drop, h_len])
  else if input_a.length > 0 then
    let pad_a := input_a ++ List.replicate (8 - input_a.length) (BitVec.ofNat 8 0)
    let pad_b := input_b ++ List.replicate (8 - input_b.length) (BitVec.ofNat 8 0)
    (neonIteration p pad_a pad_b
      (h_len := by simp [pad_a, pad_b, h_len])).take input_a.length
  else []
termination_by input_a.length
decreasing_by
  simp_all
  omega

theorem neonLoop_eq_zipWith (p : QS8AddMinmaxParams) (input_a input_b : List (BitVec 8))
    (h_len : input_a.length = input_b.length) :
    neonLoop p input_a input_b h_len =
      List.zipWith (neonElemFn p) input_a input_b := by
  suffices ∀ (n : Nat) (xs ys : List (BitVec 8))
      (h : xs.length = ys.length), xs.length ≤ n →
      neonLoop p xs ys h = List.zipWith (neonElemFn p) xs ys from
    this input_a.length input_a input_b h_len (Nat.le_refl _)
  intro n
  induction n with
  | zero =>
    intro xs ys h_eq h_len
    have : xs = [] := by cases xs <;> simp_all
    subst this
    have : ys = [] := by cases ys <;> simp_all
    subst this; simp [neonLoop]
  | succ m ih =>
    intro xs ys h_eq h_len
    cases xs with
    | nil =>
      have : ys = [] := by cases ys <;> simp_all
      subst this; simp [neonLoop]
    | cons hd tl =>
      unfold neonLoop
      simp only [List.length_cons]
      split
      · simp only [neonIteration_eq_zipWith]
        have h_drop_eq : ((hd :: tl).drop 8).length = (ys.drop 8).length := by
          simp only [List.length_drop, h_eq]
        have h_drop_le : ((hd :: tl).drop 8).length ≤ m := by
          simp only [List.length_drop, List.length_cons]
          have := h_len; simp only [List.length_cons] at this; omega
        rw [ih _ _ h_drop_eq h_drop_le]
        exact zipWith_take_append_drop (neonElemFn p) (hd :: tl) ys 8 h_eq
      · split
        · simp only [neonIteration_eq_zipWith]
          have : (tl.length + 1) = (hd :: tl).length := by simp
          rw [this]
          exact zipWith_append_take (neonElemFn p) (hd :: tl) _ ys _ h_eq
        · omega

end SALT.Kernel.QS8VAddParsed.Neon
