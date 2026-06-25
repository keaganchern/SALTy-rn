import SALT.Core.Tactic
import SALT.Kernel.F32VELU.Params
import SALT.FP.Basic
import SALT.Kernel.F32VELU.Core

namespace SALT.Kernel.F32VELUEmit.RVV

open SALT
open SALT.Core
open SALT.FP
open SALT.Kernel.F32VELU
open SALT.Kernel.F32VELU.Core
def rvvElemFn (params : F32ELUParams) (x : Float32) : Float32 :=
  let z : Float32 := (fmax (x * params.prescale) satCutoff)
  let n : Float32 := ((z * log2e) + magicBias)
  let n_bits : BitVec 32 := (ReinterpretOp.f32ToBits.eval n)
  let idx : BitVec 32 := (n_bits &&& (BitVec.ofNat 32 15))
  let en : BitVec 32 := (n_bits <<< (BitVec.ofNat 32 19))
  let l : BitVec 32 := (tableLookup idx)
  let n : Float32 := (n - magicBias)
  let t : Float32 := (z + (n * minusLn2Hi))
  let t : Float32 := (t + (n * minusLn2Lo))
  let s : Float32 := (ReinterpretOp.bitsToF32.eval (l + en))
  let p : Float32 := ((t * c3) + c2)
  let p : Float32 := (p * t)
  let t : Float32 := (t * s)
  let s : Float32 := (s - one)
  let p : Float32 := (t + (p * t))
  let ve : Float32 := ((p + s) * params.alpha)
  (if (x < zero) then ve else (x * params.beta))

def rvvPipelineFromIntrinsics (params : F32ELUParams) (chunk : List (Float32)) : List (Float32) :=
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

set_option maxHeartbeats 4000000 in
theorem rvvPipeline_eq_map (params : F32ELUParams) (chunk : List (Float32)) :
    rvvPipelineFromIntrinsics params chunk = chunk.map (rvvElemFn params ):= by
  simp only [rvvPipelineFromIntrinsics,
             List.map_map,
    zipWith_map_map,
    zipWith_map_right,
    Function.comp]
  congr 1


def rvvIteration (params : F32ELUParams) (chunk : List (Float32)) : List (Float32) :=
  rvvPipelineFromIntrinsics params chunk

theorem rvvIteration_eq_map (params : F32ELUParams) (chunk : List (Float32)) :
    rvvIteration params chunk =
      chunk.map (rvvElemFn params ):= rvvPipeline_eq_map params chunk

def rvvLoop (params : F32ELUParams) (input : List (Float32))
    (vlmax : Nat) (h_vlmax : vlmax > 0 := by omega) : List (Float32) :=
  match input with
  | [] => []
  | hd :: tl =>
    let xs := hd :: tl
    let vl := min xs.length vlmax
    rvvIteration params (xs.take vl) ++
      rvvLoop params (xs.drop vl) vlmax
termination_by input.length
decreasing_by
  simp [List.length_drop]; omega

theorem rvvLoop_eq_map (params : F32ELUParams) (input : List (Float32))
    (vlmax : Nat) (h_vlmax : vlmax > 0) :
    rvvLoop params input vlmax =
      input.map (rvvElemFn params ):= by
  suffices ∀ (n : Nat) (xs : List (Float32)), xs.length ≤ n →
      rvvLoop params xs vlmax =
        xs.map (rvvElemFn params )from
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

end SALT.Kernel.F32VELUEmit.RVV
