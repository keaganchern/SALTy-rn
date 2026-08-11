import SALT.Generated.QS8VAddMinmax.Models
import SALT.Kernel.QS8VAdd.Equivalence

namespace SALT.Generated.QS8VAddMinmax

open SALT.Kernel.QS8

private theorem exists_cons_of_length_eq_succ {α : Type} (n : Nat)
    (xs : List α) (h : xs.length = n + 1) :
    ∃ x tl, xs = x :: tl ∧ tl.length = n := by
  cases xs with
  | nil => simp at h
  | cons x tl =>
      refine ⟨x, tl, rfl, ?_⟩
      simpa using h

private theorem exists_sixteen_of_length_eq {α : Type}
    (xs : List α) (h : xs.length = 16) :
    ∃ x0 x1 x2 x3 x4 x5 x6 x7 x8 x9 xA xB xC xD xE xF,
      xs = [x0, x1, x2, x3, x4, x5, x6, x7,
        x8, x9, xA, xB, xC, xD, xE, xF] := by
  rcases exists_cons_of_length_eq_succ 15 xs h with ⟨x0, xs, rfl, h15⟩
  rcases exists_cons_of_length_eq_succ 14 xs h15 with ⟨x1, xs, rfl, h14⟩
  rcases exists_cons_of_length_eq_succ 13 xs h14 with ⟨x2, xs, rfl, h13⟩
  rcases exists_cons_of_length_eq_succ 12 xs h13 with ⟨x3, xs, rfl, h12⟩
  rcases exists_cons_of_length_eq_succ 11 xs h12 with ⟨x4, xs, rfl, h11⟩
  rcases exists_cons_of_length_eq_succ 10 xs h11 with ⟨x5, xs, rfl, h10⟩
  rcases exists_cons_of_length_eq_succ 9 xs h10 with ⟨x6, xs, rfl, h9⟩
  rcases exists_cons_of_length_eq_succ 8 xs h9 with ⟨x7, xs, rfl, h8⟩
  rcases exists_cons_of_length_eq_succ 7 xs h8 with ⟨x8, xs, rfl, h7⟩
  rcases exists_cons_of_length_eq_succ 6 xs h7 with ⟨x9, xs, rfl, h6⟩
  rcases exists_cons_of_length_eq_succ 5 xs h6 with ⟨xA, xs, rfl, h5⟩
  rcases exists_cons_of_length_eq_succ 4 xs h5 with ⟨xB, xs, rfl, h4⟩
  rcases exists_cons_of_length_eq_succ 3 xs h4 with ⟨xC, xs, rfl, h3⟩
  rcases exists_cons_of_length_eq_succ 2 xs h3 with ⟨xD, xs, rfl, h2⟩
  rcases exists_cons_of_length_eq_succ 1 xs h2 with ⟨xE, xs, rfl, h1⟩
  rcases exists_cons_of_length_eq_succ 0 xs h1 with ⟨xF, xs, rfl, h0⟩
  have h_nil : xs = [] := by simpa using h0
  subst xs
  exact ⟨x0, x1, x2, x3, x4, x5, x6, x7,
    x8, x9, xA, xB, xC, xD, xE, xF, rfl⟩

theorem rvvBlockFromIntrinsics_eq_zipWith
    (p : QS8AddMinmaxParams)
    (chunk_a chunk_b : List (BitVec 8))
    (h_len : chunk_a.length = chunk_b.length) :
    rvvBlockFromIntrinsics p chunk_a chunk_b =
      List.zipWith (SALT.Kernel.QS8VAdd.RVV.rvvElemFn p) chunk_a chunk_b := by
  change
    SALT.Kernel.QS8VAdd.RVV.rvvPipelineFromIntrinsics p chunk_a chunk_b =
      List.zipWith (SALT.Kernel.QS8VAdd.RVV.rvvElemFn p) chunk_a chunk_b
  exact SALT.Kernel.QS8VAdd.RVV.rvvPipeline_eq_zipWith p chunk_a chunk_b h_len

theorem neonBlock16FromIntrinsics_eq_zipWith
    (p : QS8AddMinmaxParams)
    (chunk_a chunk_b : List (BitVec 8))
    (h_a : chunk_a.length = 16)
    (h_b : chunk_b.length = 16) :
    neonBlock16FromIntrinsics p chunk_a chunk_b =
      List.zipWith (SALT.Kernel.QS8VAdd.Neon.neonElemFn p) chunk_a chunk_b := by
  rcases exists_sixteen_of_length_eq chunk_a h_a with
    ⟨a0, a1, a2, a3, a4, a5, a6, a7, a8, a9, aA, aB, aC, aD, aE, aF, rfl⟩
  rcases exists_sixteen_of_length_eq chunk_b h_b with
    ⟨b0, b1, b2, b3, b4, b5, b6, b7, b8, b9, bA, bB, bC, bD, bE, bF, rfl⟩
  rfl

theorem generated_block_equiv
    (p : QS8AddMinmaxParams)
    (hwf : WellFormedParams p)
    (chunk_a chunk_b : List (BitVec 8))
    (h_a : chunk_a.length = 16)
    (h_b : chunk_b.length = 16) :
    neonBlock16FromIntrinsics p chunk_a chunk_b =
      rvvBlockFromIntrinsics p chunk_a chunk_b := by
  rw [neonBlock16FromIntrinsics_eq_zipWith p chunk_a chunk_b h_a h_b]
  rw [rvvBlockFromIntrinsics_eq_zipWith p chunk_a chunk_b (h_a.trans h_b.symm)]
  clear h_a h_b
  induction chunk_a generalizing chunk_b with
  | nil => simp
  | cons a as ih =>
      cases chunk_b with
      | nil => simp
      | cons b bs =>
          simp only [List.zipWith, List.cons.injEq]
          exact ⟨SALT.Kernel.QS8VAdd.Equivalence.elem_equiv p hwf a b, ih bs⟩

end SALT.Generated.QS8VAddMinmax
