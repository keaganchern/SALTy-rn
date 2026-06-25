import SALT.Intrinsics.RVV
import SALT.Core.Tactic
import SALT.Kernel.QS8.Params

namespace SALT.Kernel.QS8ClampEmit.RVV

open SALT
open SALT.Core
open SALT.Intrinsics.RVV
open SALT.Kernel.QS8
def rvvElemFn (p : QS8AddMinmaxParams) (x : BitVec 8) : BitVec 8 :=
  (bvSignedMin (bvSignedMax x p.output_min) p.output_max)


def rvvIteration (p : QS8AddMinmaxParams) (chunk : List (BitVec 8)) : List (BitVec 8) :=
  chunk.map (rvvElemFn p )

theorem rvvIteration_eq_map (p : QS8AddMinmaxParams) (chunk : List (BitVec 8)) :
    rvvIteration p chunk =
      chunk.map (rvvElemFn p ):= rfl

def rvvLoop (p : QS8AddMinmaxParams) (input : List (BitVec 8))
    (vlmax : Nat) (h_vlmax : vlmax > 0 := by omega) : List (BitVec 8) :=
  match input with
  | [] => []
  | hd :: tl =>
    let xs := hd :: tl
    let vl := min xs.length vlmax
    rvvIteration p (xs.take vl) ++
      rvvLoop p (xs.drop vl) vlmax
termination_by input.length
decreasing_by
  simp [List.length_drop]; omega

theorem rvvLoop_eq_map (p : QS8AddMinmaxParams) (input : List (BitVec 8))
    (vlmax : Nat) (h_vlmax : vlmax > 0) :
    rvvLoop p input vlmax =
      input.map (rvvElemFn p ):= by
  suffices ∀ (n : Nat) (xs : List (BitVec 8)), xs.length ≤ n →
      rvvLoop p xs vlmax =
        xs.map (rvvElemFn p )from
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

end SALT.Kernel.QS8ClampEmit.RVV
