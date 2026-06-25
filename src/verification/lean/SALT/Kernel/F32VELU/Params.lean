import SALT.FP.Basic

namespace SALT.Kernel.F32VELU

open SALT.FP

structure F32ELUParams where
  prescale : Float32
  alpha    : Float32
  beta     : Float32
  deriving Repr

def WellFormedParams (p : F32ELUParams) : Prop :=
  FiniteF32 p.prescale ∧ FiniteF32 p.alpha ∧ FiniteF32 p.beta

def InDomain (x : Float32) : Prop := FiniteF32 x

end SALT.Kernel.F32VELU
