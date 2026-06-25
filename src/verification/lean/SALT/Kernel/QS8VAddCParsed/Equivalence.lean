import SALT.Kernel.QS8VAddCParsed.Neon
import SALT.Kernel.QS8VAddCParsed.RVV
import SALT.Core.Tactic
import SALT.Kernel.Class
import SALT.Kernel.QS8.Params

namespace SALT.Kernel.QS8VAddCParsed.Equivalence

open SALT
open SALT.Kernel.QS8VAddCParsed.Neon
open SALT.Kernel.QS8VAddCParsed.RVV
open SALT.Kernel.Class
open SALT.Kernel.QS8

theorem elem_equiv (p : QS8AddMinmaxParams) (hwf : WellFormedParams p)
    (bias : BitVec 32) (x : BitVec 8) :
    Neon.neonElemFn p bias x =
    RVV.rvvElemFn p bias x := by
  have h_shift_bound : p.shift.toNat ≤ 31 := hwf.2.1
  elem_equiv_tac [Neon.neonElemFn, RVV.rvvElemFn, h_shift_bound]

theorem computeBias_eq (p : QS8AddMinmaxParams) (input_b : BitVec 8) :
    Neon.computeBias p input_b = RVV.computeBias p input_b := by
  rfl

theorem qs8vaddcparsed_equiv (p : QS8AddMinmaxParams) (hwf : WellFormedParams p)
    (input_b : BitVec 8)
    (x : List (BitVec 8))
    (vlmax : Nat) (h_vlmax : vlmax > 0) :
    Neon.neonLoop p (Neon.computeBias p input_b) x =
    RVV.rvvLoop p (RVV.computeBias p input_b) x vlmax :=
  BinaryBroadcast.kernel_equiv
    (neonLoop := Neon.neonLoop p)
    (rvvLoop := fun bias xs => RVV.rvvLoop p bias xs vlmax)
    (fNeon := Neon.neonElemFn p)
    (fRvv := RVV.rvvElemFn p)
    (neonBias := Neon.computeBias p)
    (rvvBias := RVV.computeBias p)
    (h_neon_spec := Neon.neonLoop_eq_map p)
    (h_rvv_spec := fun bias xs => RVV.rvvLoop_eq_map p bias xs vlmax h_vlmax)
    (h_bias := computeBias_eq p)
    (h_elem := elem_equiv p hwf)
    input_b x

end SALT.Kernel.QS8VAddCParsed.Equivalence
