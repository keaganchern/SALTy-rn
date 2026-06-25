import SALT.Kernel.QS8ClampEmit.Neon
import SALT.Kernel.QS8ClampEmit.RVV
import SALT.Core.Tactic
import SALT.Kernel.Class
import SALT.Kernel.QS8.Params

namespace SALT.Kernel.QS8ClampEmit.Equivalence

open SALT
open SALT.Kernel.QS8ClampEmit.Neon
open SALT.Kernel.QS8ClampEmit.RVV
open SALT.Kernel.Class
open SALT.Kernel.QS8

theorem elem_equiv (p : QS8AddMinmaxParams) (x : BitVec 8) :
    Neon.neonElemFn p x = RVV.rvvElemFn p x := by
  elem_equiv_tac [Neon.neonElemFn, RVV.rvvElemFn]


theorem qs8clampemit_equiv (p : QS8AddMinmaxParams)
    (xs : List (BitVec 8))
    (vlmax : Nat) (h_vlmax : vlmax > 0) :
    Neon.neonLoop p xs =
    RVV.rvvLoop p xs vlmax :=
  UnaryMap.kernel_equiv
    (neonLoop := Neon.neonLoop p)
    (rvvLoop := fun xs => RVV.rvvLoop p xs vlmax)
    (fNeon := Neon.neonElemFn p)
    (fRvv := RVV.rvvElemFn p)
    (h_neon_spec := Neon.neonLoop_eq_map p)
    (h_rvv_spec := fun xs => RVV.rvvLoop_eq_map p xs vlmax h_vlmax)
    (h_elem := elem_equiv p)
    xs

end SALT.Kernel.QS8ClampEmit.Equivalence
