/- Generic NEON/RVV equivalence theorems, one `kernel_equiv` per proof class. -/

namespace SALT.Kernel.Class

/-- `List.zipWith` congruence. -/
theorem List.zipWith_congr {α β γ : Type} {f g : α → β → γ}
    (h : ∀ x y, f x y = g x y) (xs : List α) (ys : List β) :
    List.zipWith f xs ys = List.zipWith g xs ys := by
  induction xs generalizing ys with
  | nil => rfl
  | cons hx tx ih =>
    cases ys with
    | nil => rfl
    | cons hy ty => simp [List.zipWith, h, ih]

namespace UnaryMap

/-- Equivalence for a unary-map-class kernel pair. -/
theorem kernel_equiv {I O : Type}
    (neonLoop rvvLoop : List I → List O)
    (fNeon fRvv : I → O)
    (h_neon_spec : ∀ xs, neonLoop xs = xs.map fNeon)
    (h_rvv_spec : ∀ xs, rvvLoop xs = xs.map fRvv)
    (h_elem : ∀ x, fNeon x = fRvv x)
    (xs : List I) :
    neonLoop xs = rvvLoop xs := by
  rw [h_neon_spec, h_rvv_spec]
  exact List.map_congr_left (fun x _ => h_elem x)

end UnaryMap

namespace BinaryZip

/-- Equivalence for a binary-zip-class kernel pair. Loops depend on the
    equal-length precondition `h_len`. -/
theorem kernel_equiv {I₁ I₂ O : Type}
    (neonLoop rvvLoop :
      (xs : List I₁) → (ys : List I₂) → xs.length = ys.length → List O)
    (fNeon fRvv : I₁ → I₂ → O)
    (h_neon_spec : ∀ xs ys (h : xs.length = ys.length),
        neonLoop xs ys h = List.zipWith fNeon xs ys)
    (h_rvv_spec : ∀ xs ys (h : xs.length = ys.length),
        rvvLoop xs ys h = List.zipWith fRvv xs ys)
    (h_elem : ∀ x y, fNeon x y = fRvv x y)
    (xs : List I₁) (ys : List I₂) (h_len : xs.length = ys.length) :
    neonLoop xs ys h_len = rvvLoop xs ys h_len := by
  rw [h_neon_spec xs ys h_len, h_rvv_spec xs ys h_len]
  exact List.zipWith_congr h_elem xs ys

end BinaryZip

namespace BinaryBroadcast

/-- Equivalence for a broadcast-class kernel pair. `h_bias` factors out
    the ISA-specific bias prep from the per-element equivalence. -/
theorem kernel_equiv {I O C A : Type}
    (neonLoop rvvLoop : C → List I → List O)
    (fNeon fRvv : C → I → O)
    (neonBias rvvBias : A → C)
    (h_neon_spec : ∀ c xs, neonLoop c xs = xs.map (fNeon c))
    (h_rvv_spec : ∀ c xs, rvvLoop c xs = xs.map (fRvv c))
    (h_bias : ∀ a, neonBias a = rvvBias a)
    (h_elem : ∀ c x, fNeon c x = fRvv c x)
    (a : A) (xs : List I) :
    neonLoop (neonBias a) xs = rvvLoop (rvvBias a) xs := by
  rw [h_bias, h_neon_spec, h_rvv_spec]
  exact List.map_congr_left (fun x _ => h_elem (rvvBias a) x)

end BinaryBroadcast

end SALT.Kernel.Class
