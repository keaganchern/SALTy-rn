import SALT.Kernel.F32VELU.Neon
import SALT.Kernel.F32VELU.RVV
import SALT.Kernel.Class

namespace SALT.Kernel.F32VELU.Equivalence

open SALT.FP
open SALT.Kernel.F32VELU
open SALT.Kernel.F32VELU.Core
open SALT.Kernel.F32VELU.Neon
open SALT.Kernel.F32VELU.RVV
open SALT.Kernel.Class

-- Both ISA pipelines compute the same per-element function.
theorem elem_equiv (params : F32ELUParams) (x : Float32) :
    neonElemFn params x = rvvElemFn params x := by
  rw [neonElem_eq_core, rvvElem_eq_core]

-- NEON and RVV f32-velu produce bit-identical outputs for all input lengths
-- and all valid VLEN settings. Says nothing about hardware faithfulness
-- outside the validated domain (NaN / subnormal / infinite inputs).
theorem f32_velu_equiv
    (p : F32ELUParams)
    (xs : List Float32)
    (vlmax : Nat)
    (hvl : 0 < vlmax) :
    (neonLoop p xs).map Float32.toBits =
    (rvvLoop p xs vlmax).map Float32.toBits :=
  congrArg (List.map Float32.toBits) <|
    UnaryMap.kernel_equiv
      (neonLoop := neonLoop p)
      (rvvLoop := fun xs => rvvLoop p xs vlmax)
      (fNeon := neonElemFn p)
      (fRvv := rvvElemFn p)
      (h_neon_spec := fun xs => neonLoop_eq_map p xs)
      (h_rvv_spec := fun xs => rvvLoop_eq_map p xs vlmax hvl)
      (h_elem := elem_equiv p)
      xs

end SALT.Kernel.F32VELU.Equivalence
