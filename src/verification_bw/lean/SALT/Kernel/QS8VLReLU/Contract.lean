import SALT.Generated.QS8VLReLU.Models

namespace SALT.Kernel.QS8VLReLU

open SALT.Generated.QS8VLReLU

/-- Parameter domain constructed by XNNPACK@867d5a344790802ee067be62f572c2e2722bf6fb.
    These are value-level bounds; buffer and schedule obligations are separate. -/
def WellFormedParams (p : QS8LReLUParams) : Prop :=
  -128 <= p.input_zero_point.toInt
  ∧ p.input_zero_point.toInt <= 127
  ∧ 1 <= p.positive_multiplier.toInt
  ∧ p.positive_multiplier.toInt <= 32768
  ∧ -32767 <= p.negative_multiplier.toInt
  ∧ p.negative_multiplier.toInt <= 32768
  ∧ p.negative_multiplier.toInt ≠ 0
  ∧ -128 <= p.output_zero_point.toInt
  ∧ p.output_zero_point.toInt <= 127

end SALT.Kernel.QS8VLReLU
