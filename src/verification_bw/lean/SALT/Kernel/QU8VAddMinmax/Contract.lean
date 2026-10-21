import SALT.Generated.QU8VAddMinmax.Models

namespace SALT.Kernel.QU8VAddMinmax

open SALT.Generated.QU8VAddMinmax

/-- Range invariants established by
    XNNPACK@867d5a344790802ee067be62f572c2e2722bf6fb's parameter producer for
    validated QU8 quantization inputs.
    These are value-level bounds; buffer and schedule obligations are separate. -/
def WellFormedParams (p : QU8AddMinmaxParams) : Prop :=
  12 <= p.shift.toNat
  ∧ p.shift.toNat <= 30
  ∧ 0 < p.a_multiplier.toInt
  ∧ p.a_multiplier.toInt <= 2097152
  ∧ 0 < p.b_multiplier.toInt
  ∧ p.b_multiplier.toInt <= 2097152
  ∧ 1048576 <= max p.a_multiplier.toInt p.b_multiplier.toInt
  ∧ 0 <= p.output_zero_point.toInt
  ∧ p.output_zero_point.toInt <= 255
  ∧ p.output_min = BitVec.ofNat 8 0
  ∧ p.output_max = BitVec.ofNat 8 255

end SALT.Kernel.QU8VAddMinmax
