/-
  Lane-level combinators: lanewise, lanewiseBin, broadcast, selectMask,
  tableLookup. The last two enforce equal-length / in-bounds at the
  signature level; each combinator carries a `[simp]` lemma back to its
  underlying List operation.
-/
import SALT.Core.CoreOp

namespace SALT.Core

/-- Apply a per-lane unary function across a vector. -/
@[inline] def lanewise {α β : Type} (f : α → β) (xs : List α) : List β :=
  xs.map f

/-- Apply a per-lane binary function pointwise to two equal-length vectors.
    The length equality is a call-site obligation (default `by simp`) so
    ragged inputs are unrepresentable rather than silently truncated. -/
@[inline] def lanewiseBin {α β γ : Type} (f : α → β → γ)
    (xs : List α) (ys : List β)
    (h : xs.length = ys.length := by simp) : List γ :=
  let _ := h
  List.zipWith f xs ys

/-- Produce a length-`n` vector where every lane holds `x`. -/
@[inline] def broadcast {α : Type} (x : α) (n : Nat) : List α :=
  List.replicate n x

/-- Per-lane conditional select: lane `i` is `t[i]` when `mask[i]`, else `f[i]`.
    Both data lanes must match the mask length. -/
def selectMask {α : Type} (mask : List Bool) (t f : List α)
    (h_t : t.length = mask.length := by rfl)
    (h_f : f.length = mask.length := by rfl) : List α :=
  let _ := h_t
  let _ := h_f
  List.zipWith (fun mt tf => if mt then tf.1 else tf.2)
    mask (List.zip t f)

/-- Per-lane table lookup. Indices are `Fin table.size`, so every lookup
    is total — no `Array.get!` panic path, no out-of-range wrap. -/
@[inline] def tableLookup {α : Type} (table : Array α)
    (idx : List (Fin table.size)) : List α :=
  idx.map (fun i => table[i])

-- Simp lemmas: every combinator normalises back to its underlying List op.

@[simp] theorem lanewise_eq_map {α β : Type} (f : α → β) (xs : List α) :
    lanewise f xs = xs.map f := rfl

@[simp] theorem lanewiseBin_eq_zipWith {α β γ : Type} (f : α → β → γ)
    (xs : List α) (ys : List β) (h : xs.length = ys.length) :
    lanewiseBin f xs ys h = List.zipWith f xs ys := rfl

@[simp] theorem broadcast_eq_replicate {α : Type} (x : α) (n : Nat) :
    broadcast x n = List.replicate n x := rfl

@[simp] theorem selectMask_eq_zipWith_zip {α : Type} (mask : List Bool)
    (t f : List α) (h_t : t.length = mask.length) (h_f : f.length = mask.length) :
    selectMask mask t f h_t h_f =
      List.zipWith (fun mt tf => if mt then tf.1 else tf.2)
        mask (List.zip t f) := rfl

@[simp] theorem tableLookup_eq_map {α : Type} (table : Array α)
    (idx : List (Fin table.size)) :
    tableLookup table idx = idx.map (fun i => table[i]) := rfl

end SALT.Core
