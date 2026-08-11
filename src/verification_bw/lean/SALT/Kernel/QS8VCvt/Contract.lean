import SALT.Generated.QS8VCvt.Models

namespace SALT.Kernel.QS8VCvt

open SALT.Generated.QS8VCvt

/-- Parameter domain constructed by XNNPACK@867d5a344790802ee067be62f572c2e2722bf6fb.
    These are value-level bounds; buffer and schedule obligations are separate. -/
def WellFormedParams (p : QS8CvtParams) : Prop :=
  -128 <= p.input_zero_point.toInt
  ∧ p.input_zero_point.toInt <= 127
  ∧ 1 <= p.multiplier.toInt
  ∧ p.multiplier.toInt <= 32768
  ∧ -128 <= p.output_zero_point.toInt
  ∧ p.output_zero_point.toInt <= 127

end SALT.Kernel.QS8VCvt
