import SALT.Core.Tactic
import SALT.Kernel.F32VELU.Params
import SALT.FP.Basic
import SALT.Kernel.F32VELU.Core

namespace SALT.Kernel.F32VELUEmit.Neon

open SALT
open SALT.Core
open SALT.FP
open SALT.Kernel.F32VELU
open SALT.Kernel.F32VELU.Core
def neonElemFn (params : F32ELUParams) (x : Float32) : Float32 :=
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

def neonPipelineFromIntrinsics (params : F32ELUParams) (chunk : List (Float32)) : List (Float32) :=
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
theorem neonPipeline_eq_map (params : F32ELUParams) (chunk : List (Float32)) :
    neonPipelineFromIntrinsics params chunk = chunk.map (neonElemFn params ):= by
  simp only [neonPipelineFromIntrinsics,
             List.map_map,
    zipWith_map_map,
    zipWith_map_right,
    Function.comp]
  congr 1


def neonIteration (params : F32ELUParams) (chunk : List (Float32)) : List (Float32) :=
  neonPipelineFromIntrinsics params chunk

theorem neonIteration_eq_map (params : F32ELUParams) (chunk : List (Float32)) :
    neonIteration params chunk =
      chunk.map (neonElemFn params ):= neonPipeline_eq_map params chunk

def neonLoop (params : F32ELUParams) (input : List (Float32)) : List (Float32) :=
  if input.length ≥ 12 then
    neonIteration params (input.take 12) ++
      neonLoop params (input.drop 12)
  else if input.length ≥ 4 then
    neonIteration params (input.take 4) ++
      neonLoop params (input.drop 4)
  else if input.length > 0 then
    let padded := input ++ List.replicate (4 - input.length) (0 : Float32)
    (neonIteration params padded).take input.length
  else []
termination_by input.length
decreasing_by all_goals (simp_all [List.length_drop]; omega)

theorem neonLoop_eq_map (params : F32ELUParams) (input : List (Float32)) :
    neonLoop params input =
      input.map (neonElemFn params ):= by
  suffices ∀ (n : Nat) (xs : List (Float32)), xs.length ≤ n →
      neonLoop params xs =
        xs.map (neonElemFn params )from
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
      · have h_drop_le : ((hd :: tl).drop 12).length ≤ m := by
          simp [List.length_drop]; omega
        rw [ih _ h_drop_le, ← List.map_append, List.take_append_drop]
      · split
        · have h_drop_le : ((hd :: tl).drop 4).length ≤ m := by
            simp [List.length_drop]; omega
          rw [ih _ h_drop_le, ← List.map_append, List.take_append_drop]
        · split
          · exact map_append_take _ (hd :: tl) _
          · omega

end SALT.Kernel.F32VELUEmit.Neon
