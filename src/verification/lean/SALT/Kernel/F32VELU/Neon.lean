import SALT.FP.Basic
import SALT.Core.CoreOp
import SALT.Kernel.F32VELU.Params
import SALT.Kernel.F32VELU.Core

namespace SALT.Kernel.F32VELU.Neon

open SALT.FP
open SALT.Core
open SALT.Kernel.F32VELU
open SALT.Kernel.F32VELU.Core

-- Per-element function (mirrors source/f32-velu.c lines 143-173). Each step
-- maps to one or more NEON intrinsic calls (shown inline).

def neonElemFn (params : F32ELUParams) (x : Float32) : Float32 :=
  let z := fmax (x * params.prescale) satCutoff       -- vmaxq_f32(vmulq_f32(...), ...)
  let n := z * log2e + magicBias                       -- vmlaq_f32 (non-fused)
  let n_bits : BitVec 32 := f32ToBits n                       -- vreinterpretq_s32_f32
  let idx : BitVec 32 := BVBinOp.bvAnd.eval n_bits 0xF#32     -- vandq_s32
  let en  : BitVec 32 := BVShiftOp.shl.eval n_bits 19          -- vshlq_n_s32
  let l : BitVec 32 := tableLookup idx                        -- lane-gather from LUT
  let n := n - magicBias                                       -- vsubq_f32
  let t := z + n * minusLn2Hi                                  -- vmlaq_f32 (non-fused)
  let t := t + n * minusLn2Lo                                  -- vmlaq_f32 (non-fused)
  let s : Float32 := bitsToF32 (BVBinOp.add.eval l en)         -- vreinterpretq_f32_s32(vaddq_s32)
  let p := t * c3 + c2                                        -- vmlaq_f32 (non-fused)
  let p := p * t                                              -- vmulq_f32
  let t := t * s                                              -- vmulq_f32
  let s := s - one                                            -- vsubq_f32
  let p := t + p * t                                          -- vmlaq_f32 (non-fused)
  let ve := (p + s) * params.alpha                            -- vmulq_f32(vaddq_f32(...))
  if x < zero then ve else x * params.beta                    -- vbslq_f32(vcltq_f32(...))

-- NEON element function = shared core
theorem neonElem_eq_core (params : F32ELUParams) (x : Float32) :
    neonElemFn params x = coreElem params x := by
  rfl

-- Intrinsic-composed pipeline (list-level model). Each step is the list-level
-- analogue of one NEON intrinsic call; table lookup and selection are
-- abstracted as per-element operations.

def neonPipelineFromIntrinsics (params : F32ELUParams)
    (chunk : List Float32) : List Float32 :=
  let vz := chunk.map (fun x => fmax (x * params.prescale) satCutoff)
  let vn := vz.map (fun z => z * log2e + magicBias)
  let vn_bits := vn.map f32ToBits
  let vidx := vn_bits.map (fun b => BVBinOp.bvAnd.eval b 0xF#32)
  let ven := vn_bits.map (fun b => BVShiftOp.shl.eval b 19)
  let vl := vidx.map tableLookup
  let vn := vn.map (· - magicBias)
  let vt := List.zipWith (fun z n => z + n * minusLn2Hi) vz vn
  let vt := List.zipWith (fun t n => t + n * minusLn2Lo) vt vn
  let vs := List.zipWith
    (fun l en => bitsToF32 (BVBinOp.add.eval l en)) vl ven
  let vp := vt.map (fun t => t * c3 + c2)
  let vp := List.zipWith (· * ·) vp vt
  let vt := List.zipWith (· * ·) vt vs
  let vs := vs.map (· - one)
  let vp := List.zipWith (fun t p => t + p * t) vt vp
  let ve := List.zipWith (fun p s => (p + s) * params.alpha) vp vs
  List.zipWith (fun x ve => if x < zero then ve else x * params.beta) chunk ve

-- intrinsic pipeline = List.map neonElemFn
set_option maxHeartbeats 4000000 in
theorem neonPipeline_eq_map (params : F32ELUParams) (chunk : List Float32) :
    neonPipelineFromIntrinsics params chunk = chunk.map (neonElemFn params) := by
  simp only [neonPipelineFromIntrinsics,
             List.map_map, zipWith_map_map, zipWith_map_right, Function.comp]
  congr 1

-- Loop model
def neonLoop (params : F32ELUParams)
    (input : List Float32) : List Float32 :=
  if input.length ≥ 12 then
    (input.take 12).map (neonElemFn params) ++
    neonLoop params (input.drop 12)
  else if input.length ≥ 4 then
    (input.take 4).map (neonElemFn params) ++
    neonLoop params (input.drop 4)
  else if input.length > 0 then
    let padded := input ++ List.replicate (4 - input.length) zero
    (padded.map (neonElemFn params)).take input.length
  else
    []
termination_by input.length
decreasing_by all_goals (simp_all [List.length_drop]; omega)

-- Loop = flat map
theorem neonLoop_eq_map (params : F32ELUParams)
    (input : List Float32) :
    neonLoop params input = input.map (neonElemFn params) := by
  suffices ∀ (n : Nat) (xs : List Float32), xs.length ≤ n →
      neonLoop params xs = xs.map (neonElemFn params) from
    this input.length input (Nat.le_refl _)
  intro n
  induction n with
  | zero =>
    intro xs h_len
    have : xs = [] := by cases xs <;> simp_all
    subst this; simp [neonLoop]
  | succ m ih =>
    intro xs h_len
    cases xs with
    | nil => simp [neonLoop]
    | cons hd tl =>
      unfold neonLoop
      simp only [List.length_cons]
      split
      · have h_drop : ((hd :: tl).drop 12).length ≤ m := by
          rw [List.length_drop]; omega
        rw [ih _ h_drop, ← List.map_append, List.take_append_drop]
      · split
        · have h_drop : ((hd :: tl).drop 4).length ≤ m := by
            rw [List.length_drop]; omega
          rw [ih _ h_drop, ← List.map_append, List.take_append_drop]
        · split
          · exact map_append_take_f32 (neonElemFn params) (hd :: tl) _
          · omega

end SALT.Kernel.F32VELU.Neon
