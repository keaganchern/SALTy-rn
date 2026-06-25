import SALT.Kernel.QS8VAddParsed.Neon
import SALT.Kernel.QS8VAddParsed.RVV
import SALT.Core.Tactic
import SALT.Kernel.Class
import SALT.Kernel.QS8.Params

namespace SALT.Kernel.QS8VAddParsed.Equivalence

open SALT
open SALT.Kernel.QS8VAddParsed.Neon
open SALT.Kernel.QS8VAddParsed.RVV
open SALT.Kernel.Class
open SALT.Kernel.QS8

theorem elem_equiv (p : QS8AddMinmaxParams) (hwf : WellFormedParams p)
    (a b : BitVec 8) :
    Neon.neonElemFn p a b =
    RVV.rvvElemFn p a b := by
  have h_shift_bound : p.shift.toNat ≤ 31 := hwf.2.1
  elem_equiv_tac [Neon.neonElemFn, RVV.rvvElemFn, h_shift_bound]


theorem qs8vaddparsed_equiv (p : QS8AddMinmaxParams) (hwf : WellFormedParams p)
    (a b : List (BitVec 8))
    (h_len : a.length = b.length)
    (vlmax : Nat) (h_vlmax : vlmax > 0) :
    Neon.neonLoop p a b h_len =
    RVV.rvvLoop p a b vlmax h_vlmax h_len :=
  BinaryZip.kernel_equiv
    (neonLoop := fun xs ys h => Neon.neonLoop p xs ys h)
    (rvvLoop := fun xs ys h => RVV.rvvLoop p xs ys vlmax h_vlmax h)
    (fNeon := Neon.neonElemFn p)
    (fRvv := RVV.rvvElemFn p)
    (h_neon_spec := Neon.neonLoop_eq_zipWith p)
    (h_rvv_spec := fun xs ys h => RVV.rvvLoop_eq_zipWith p xs ys h vlmax h_vlmax)
    (h_elem := elem_equiv p hwf)
    a b h_len

end SALT.Kernel.QS8VAddParsed.Equivalence
