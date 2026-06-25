import SALT.Intrinsics.Neon
import SALT.Core.Tactic
import SALT.Kernel.QS8.Params

namespace SALT.Kernel.QS8ClampEmit.Neon

open SALT
open SALT.Core
open SALT.Intrinsics.Neon
open SALT.Kernel.QS8
def neonElemFn (p : QS8AddMinmaxParams) (x : BitVec 8) : BitVec 8 :=
  (bvSignedMin (bvSignedMax x p.output_min) p.output_max)


def neonIteration (p : QS8AddMinmaxParams) (chunk : List (BitVec 8)) : List (BitVec 8) :=
  chunk.map (neonElemFn p )

theorem neonIteration_eq_map (p : QS8AddMinmaxParams) (chunk : List (BitVec 8)) :
    neonIteration p chunk =
      chunk.map (neonElemFn p ):= rfl

def neonLoop (p : QS8AddMinmaxParams) (input : List (BitVec 8)) : List (BitVec 8) :=
  if input.length ≥ 8 then
    neonIteration p (input.take 8) ++
      neonLoop p (input.drop 8)
  else if input.length > 0 then
    let padded := input ++ List.replicate (8 - input.length) (BitVec.ofNat 8 0)
    (neonIteration p padded).take input.length
  else []
termination_by input.length
decreasing_by all_goals (simp_all [List.length_drop]; omega)

theorem neonLoop_eq_map (p : QS8AddMinmaxParams) (input : List (BitVec 8)) :
    neonLoop p input =
      input.map (neonElemFn p ):= by
  suffices ∀ (n : Nat) (xs : List (BitVec 8)), xs.length ≤ n →
      neonLoop p xs =
        xs.map (neonElemFn p )from
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

end SALT.Kernel.QS8ClampEmit.Neon
