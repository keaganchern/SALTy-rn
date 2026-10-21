import SALT.Example.S8VMax.Proof

namespace SALT.Example.S8VMax

/-- Keep the teaching example bound to the intended local-block proposition.
    This stops an imported `block_equal` whose conclusion was weakened from
    generated-model equality from satisfying the audit module. -/
theorem block_equal_expected_type
    (p : S8VMaxParams)
    (input : List (BitVec 8))
    (hLength : input.length = 16) :
    neonBlock16FromIntrinsics p input = rvvChunkFromIntrinsics p input :=
  block_equal p input hLength

/-- The model emitted when the supported Neon operation is mutated from
    `vmaxq_s8` to `vminq_s8`. -/
def neonBlock16VminMutationFromIntrinsics (p : S8VMaxParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vthreshold := List.replicate 16 (p.threshold.truncate 8)
  let vx := input.take 16
  SALT.Intrinsics.Neon.vminq_s8 vx vthreshold

def mutationParams : S8VMaxParams where
  threshold := BitVec.ofNat 8 0

def mutationInput : List (BitVec 8) :=
  List.replicate 16 (BitVec.ofNat 8 1)

theorem mutationInput_length : mutationInput.length = 16 := by
  decide

/-- A concrete, kernel-checked witness that the supported `vmaxq_s8` to
    `vminq_s8` source mutation does not implement the RVV maximum model. -/
theorem vmax_to_vmin_mutation_inequivalent :
    neonBlock16VminMutationFromIntrinsics mutationParams mutationInput !=
      rvvChunkFromIntrinsics mutationParams mutationInput := by
  decide

end SALT.Example.S8VMax
