/- NEON/RVV equivalence theorem for qs8-vadd. -/
import SALT.Kernel.QS8VAdd.Neon
import SALT.Kernel.QS8VAdd.RVV
import SALT.Core.Tactic
import SALT.Kernel.Class

namespace SALT.Kernel.QS8VAdd.Equivalence

open SALT
open SALT.Kernel.QS8
open SALT.Kernel.QS8VAdd.Neon
open SALT.Kernel.QS8VAdd.RVV
open SALT.Intrinsics.Neon
open SALT.Intrinsics.RVV
open SALT.Kernel.Class

/-- Per-element equivalence of the NEON and RVV element functions. -/
theorem elem_equiv
    (p : QS8AddMinmaxParams) (hwf : WellFormedParams p)
    (a b : BitVec 8) :
    neonElemFn p a b = rvvElemFn p a b := by
  have h_shift_bound : p.shift.toNat ≤ 31 := hwf.2.1
  elem_equiv_tac [Neon.neonElemFn, RVV.rvvElemFn, h_shift_bound]

/-- NEON and RVV qs8-vadd produce identical outputs for equal-length inputs,
    well-formed parameters, and any positive vlmax, under bitvector semantics
    (int32_t arithmetic wraps modulo 2^32). -/
theorem qs8_vadd_equiv
    (p : QS8AddMinmaxParams) (hwf : WellFormedParams p)
    (input_a input_b : List (BitVec 8))
    (h_len : input_a.length = input_b.length)
    (vlmax : Nat) (h_vlmax : vlmax > 0) :
    neonLoop p input_a input_b h_len =
    rvvLoop p input_a input_b vlmax h_vlmax h_len :=
  BinaryZip.kernel_equiv
    (neonLoop := fun xs ys h => Neon.neonLoop p xs ys h)
    (rvvLoop := fun xs ys h => RVV.rvvLoop p xs ys vlmax h_vlmax h)
    (fNeon := Neon.neonElemFn p)
    (fRvv := RVV.rvvElemFn p)
    (h_neon_spec := Neon.neonLoop_eq_zipWith p)
    (h_rvv_spec := fun xs ys h => RVV.rvvLoop_eq_zipWith p xs ys h vlmax h_vlmax)
    (h_elem := elem_equiv p hwf)
    input_a input_b h_len

end SALT.Kernel.QS8VAdd.Equivalence
