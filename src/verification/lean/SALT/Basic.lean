-- omega is builtin in Lean 4.29.0

namespace SALT

-- Signed clamp (saturating narrow)
def signedClamp {wide : Nat} (x : BitVec wide) (narrow : Nat) : BitVec narrow :=
  let xi := x.toInt
  let lo := -(2 ^ (narrow - 1) : Int)
  let hi := (2 ^ (narrow - 1) - 1 : Int)
  let clamped := max lo (min xi hi)
  BitVec.ofInt narrow clamped

-- Signed saturating add
def signedSatAdd {n : Nat} (a b : BitVec n) : BitVec n :=
  let sum := a.toInt + b.toInt
  let lo := -(2 ^ (n - 1) : Int)
  let hi := (2 ^ (n - 1) - 1 : Int)
  let clamped := max lo (min sum hi)
  BitVec.ofInt n clamped

-- Signed min / max (element-wise)
def bvSignedMax {n : Nat} (a b : BitVec n) : BitVec n :=
  if a.toInt ≥ b.toInt then a else b

def bvSignedMin {n : Nat} (a b : BitVec n) : BitVec n :=
  if a.toInt ≤ b.toInt then a else b

-- Clamp (signed min/max composition)
def clamp {n : Nat} (x lo hi : BitVec n) : BitVec n :=
  bvSignedMin (bvSignedMax x lo) hi

-- Sign extension
def sext {n : Nat} (x : BitVec n) (m : Nat) : BitVec m :=
  x.signExtend m

-- Width-generalized rounding shifts (two ISA-specific algorithms)

/-- NEON's VRSHL.S<w>: widen, add round constant 1 << (shift - 1), sshift, truncate. -/
def neonRoundingShiftRight {w : Nat} (x : BitVec w) (shift : Nat) : BitVec w :=
  if shift = 0 then x
  else
    let wide : BitVec (w + 1) := x.signExtend (w + 1)
    let round_const : BitVec (w + 1) := BitVec.ofNat (w + 1) (1 <<< (shift - 1))
    let rounded : BitVec (w + 1) := wide + round_const
    (rounded.sshiftRight shift).truncate w

/-- RVV's VSSRA.VX with vxrm = RNU (round-to-nearest up): sshift then
    conditionally increment by the shifted-out LSB. -/
def rvvRoundingShiftRight {w : Nat} (x : BitVec w) (shift : Nat) : BitVec w :=
  if shift = 0 then x
  else
    let shifted : BitVec w := x.sshiftRight shift
    let round_bit : Bool := x.getLsbD (shift - 1)
    if round_bit then shifted + 1 else shifted

-- List helpers for intrinsic bridge proofs
theorem zipWith_replicate_left {α β γ : Type} (f : α → β → γ) (a : α)
    (l : List β) (n : Nat) (h : n = l.length := by simp) :
    List.zipWith f (List.replicate n a) l = l.map (f a) := by
  subst h
  induction l with
  | nil => rfl
  | cons hd tl ih => simp [List.replicate, ih]

theorem zipWith_replicate_right {α β γ : Type} (f : α → β → γ) (b : β)
    (l : List α) (n : Nat) (h : n = l.length := by simp) :
    List.zipWith f l (List.replicate n b) = l.map (fun x => f x b) := by
  subst h
  induction l with
  | nil => rfl
  | cons hd tl ih => simp [List.replicate, ih]

-- List helper for tail-padding proofs
theorem map_append_take {α β : Type} (f : α → β)
    (xs pad : List α) :
    ((xs ++ pad).map f).take xs.length = xs.map f := by
  rw [List.map_append]
  have h_len : (xs.map f).length = xs.length := by simp
  rw [← h_len]
  exact List.take_left ..

-- List helpers for binary elementwise (zipWith) loop proofs
theorem zipWith_append {α β γ : Type} (f : α → β → γ)
    (a₁ a₂ : List α) (b₁ b₂ : List β) (h : a₁.length = b₁.length) :
    List.zipWith f (a₁ ++ a₂) (b₁ ++ b₂) =
    List.zipWith f a₁ b₁ ++ List.zipWith f a₂ b₂ := by
  induction a₁ generalizing b₁ with
  | nil =>
    have : b₁ = [] := by cases b₁ <;> simp_all
    subst this; simp
  | cons hd tl ih =>
    cases b₁ with
    | nil => simp at h
    | cons hd' tl' =>
      simp [List.zipWith]
      exact ih tl' (by simpa using h)

theorem zipWith_take_append_drop {α β γ : Type} (f : α → β → γ)
    (a : List α) (b : List β) (n : Nat) (h : a.length = b.length) :
    List.zipWith f (a.take n) (b.take n) ++
    List.zipWith f (a.drop n) (b.drop n) =
    List.zipWith f a b := by
  rw [← zipWith_append f (a.take n) (a.drop n) (b.take n) (b.drop n)
        (by simp [List.length_take]; omega),
      List.take_append_drop, List.take_append_drop]

theorem zipWith_append_take {α β γ : Type} (f : α → β → γ)
    (a pad_a : List α) (b pad_b : List β) (h : a.length = b.length) :
    (List.zipWith f (a ++ pad_a) (b ++ pad_b)).take a.length =
    List.zipWith f a b := by
  rw [zipWith_append f a pad_a b pad_b h]
  have h_len : (List.zipWith f a b).length = a.length := by
    simp [List.length_zipWith, h]
  rw [← h_len]
  exact List.take_left ..

end SALT
