namespace SALT.FP

-- Float32 helpers for kernel modeling
def sameBits (x y : Float32) : Prop := x.toBits = y.toBits

def FiniteF32 (x : Float32) : Prop := x.isFinite = true

-- NaN-suppressing max (models FMAXNM / vfmax for finite inputs)
def fmax (a b : Float32) : Float32 :=
  if b ≤ a then a else b

-- xnn_table_exp2minus_k_over_16 (16 entries, from XNNPACK source).
-- Each entry is the Float32 bit pattern for 2^(-k/16), k ∈ 0..15.

def exp2MinusKOver16 : Array (BitVec 32) := #[
  0x3F800000#32, 0x3F7DAAC3#32, 0x3F7B95C2#32, 0x3F79C3D3#32,
  0x3F7837F0#32, 0x3F76F532#32, 0x3F75FED7#32, 0x3F75583F#32,
  0x3F7504F3#32, 0x3F7508A4#32, 0x3F75672A#32, 0x3F76248C#32,
  0x3F7744FD#32, 0x3F78CCDF#32, 0x3F7AC0C7#32, 0x3F7D257D#32
]

/-- Table lookup for `exp2MinusKOver16`. Panics on out-of-range access. -/
def tableLookup (idx : BitVec 32) : BitVec 32 :=
  exp2MinusKOver16[idx.toNat]!

-- List helpers
theorem map_append_take_f32 {α β : Type} (f : α → β)
    (xs pad : List α) :
    ((xs ++ pad).map f).take xs.length = xs.map f := by
  rw [List.map_append]
  have h_len : (xs.map f).length = xs.length := by simp
  rw [← h_len]
  exact List.take_left ..

theorem zipWith_map_map {α β γ δ : Type} (f : β → γ → δ) (g : α → β) (h : α → γ)
    (xs : List α) :
    List.zipWith f (xs.map g) (xs.map h) = xs.map (fun x => f (g x) (h x)) := by
  induction xs with
  | nil => rfl
  | cons hd tl ih => simp [ih]

theorem zipWith_map_right {α β γ : Type} (f : α → β → γ) (g : α → β)
    (xs : List α) :
    List.zipWith f xs (xs.map g) = xs.map (fun x => f x (g x)) := by
  induction xs with
  | nil => rfl
  | cons hd tl ih => simp [ih]

end SALT.FP
