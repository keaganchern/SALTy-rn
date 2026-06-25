import SALT.Kernel.F32VELUEmit.Neon
import SALT.Kernel.F32VELUEmit.RVV
import SALT.Core.Tactic
import SALT.Kernel.Class
import SALT.Kernel.F32VELU.Params
import SALT.FP.Basic
import SALT.Kernel.F32VELU.Core

namespace SALT.Kernel.F32VELUEmit.Equivalence

open SALT
open SALT.Kernel.F32VELUEmit.Neon
open SALT.Kernel.F32VELUEmit.RVV
open SALT.Kernel.Class
open SALT.FP
open SALT.Kernel.F32VELU
open SALT.Kernel.F32VELU.Core

theorem elem_equiv (params : F32ELUParams) (x : Float32) :
    Neon.neonElemFn params x = RVV.rvvElemFn params x := by
  elem_equiv_tac [Neon.neonElemFn, RVV.rvvElemFn]


theorem f32veluemit_equiv (params : F32ELUParams)
    (xs : List (Float32))
    (vlmax : Nat) (h_vlmax : vlmax > 0) :
    Neon.neonLoop params xs =
    RVV.rvvLoop params xs vlmax :=
  UnaryMap.kernel_equiv
    (neonLoop := Neon.neonLoop params)
    (rvvLoop := fun xs => RVV.rvvLoop params xs vlmax)
    (fNeon := Neon.neonElemFn params)
    (fRvv := RVV.rvvElemFn params)
    (h_neon_spec := Neon.neonLoop_eq_map params)
    (h_rvv_spec := fun xs => RVV.rvvLoop_eq_map params xs vlmax h_vlmax)
    (h_elem := elem_equiv params)
    xs

end SALT.Kernel.F32VELUEmit.Equivalence
