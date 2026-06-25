import SALT.FP.Basic
import SALT.Core.CoreOp
import SALT.Kernel.F32VELU.Params
import SALT.Kernel.F32VELU.Core

namespace SALT.Kernel.F32VELU.RVV

open SALT.FP
open SALT.Core
open SALT.Kernel.F32VELU
open SALT.Kernel.F32VELU.Core

-- Per-element function (mirrors target/f32-velu.c lines 24-68). Each step maps
-- to one or more RVV intrinsic calls (shown inline).

def rvvElemFn (params : F32ELUParams) (x : Float32) : Float32 :=
  let z := fmax (x * params.prescale) satCutoff       -- vfmul then vfmax
  let n := z * log2e + magicBias                       -- vfmul then vfadd (non-fused)
  let n_bits : BitVec 32 := f32ToBits n                       -- vreinterpret
  let idx : BitVec 32 := BVBinOp.bvAnd.eval n_bits 0xF#32     -- vand
  let en  : BitVec 32 := BVShiftOp.shl.eval n_bits 19          -- vsll
  let l : BitVec 32 := tableLookup idx                        -- vluxei32 indexed load
  let n := n - magicBias                                       -- vfsub
  let t := z + n * minusLn2Hi                                  -- vfmul then vfadd (non-fused)
  let t := t + n * minusLn2Lo                                  -- vfmul then vfadd (non-fused)
  let s : Float32 := bitsToF32 (BVBinOp.add.eval l en)         -- vadd then vreinterpret
  let p := t * c3 + c2                                         -- vfmul then vfadd (non-fused)
  let p := p * t                                               -- vfmul
  let t := t * s                                               -- vfmul
  let s := s - one                                             -- vfsub
  let p := t + p * t                                           -- vfmul then vfadd (non-fused)
  let ve := (p + s) * params.alpha                             -- vfadd then vfmul
  if x < zero then ve else x * params.beta                     -- vmflt + vmerge

-- RVV element function = shared core
theorem rvvElem_eq_core (params : F32ELUParams) (x : Float32) :
    rvvElemFn params x = coreElem params x := by
  rfl

-- Intrinsic-composed pipeline (list-level model). Table lookup abstracts
-- vluxei32 and selection abstracts vmflt_vf + vmerge_vvm as per-element ops.

def rvvPipelineFromIntrinsics (params : F32ELUParams)
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

-- intrinsic pipeline = List.map rvvElemFn
set_option maxHeartbeats 4000000 in
theorem rvvPipeline_eq_map (params : F32ELUParams) (chunk : List Float32) :
    rvvPipelineFromIntrinsics params chunk = chunk.map (rvvElemFn params) := by
  simp only [rvvPipelineFromIntrinsics,
             List.map_map, zipWith_map_map, zipWith_map_right, Function.comp]
  congr 1

-- Loop model (strip-mined, dynamic vl)
def rvvLoop (params : F32ELUParams)
    (input : List Float32) (vlmax : Nat) (h_vlmax : vlmax > 0 := by omega) : List Float32 :=
  match input with
  | [] => []
  | hd :: tl =>
    let xs := hd :: tl
    let vl := min xs.length vlmax
    (xs.take vl).map (rvvElemFn params) ++ rvvLoop params (xs.drop vl) vlmax
termination_by input.length
decreasing_by
  simp [List.length_drop]
  omega

-- Loop = flat map
theorem rvvLoop_eq_map (params : F32ELUParams)
    (input : List Float32) (vlmax : Nat) (h_vlmax : vlmax > 0) :
    rvvLoop params input vlmax = input.map (rvvElemFn params) := by
  suffices ∀ (n : Nat) (xs : List Float32), xs.length ≤ n →
      rvvLoop params xs vlmax = xs.map (rvvElemFn params) from
    this input.length input (Nat.le_refl _)
  intro n
  induction n with
  | zero =>
    intro xs h_len
    have : xs = [] := by cases xs <;> simp_all
    subst this; simp [rvvLoop]
  | succ m ih =>
    intro xs h_len
    cases xs with
    | nil => simp [rvvLoop]
    | cons hd tl =>
      unfold rvvLoop
      dsimp only []
      have h_drop : ((hd :: tl).drop (min (hd :: tl).length vlmax)).length ≤ m := by
        rw [List.length_drop]; omega
      rw [ih _ h_drop, ← List.map_append, List.take_append_drop]

end SALT.Kernel.F32VELU.RVV
