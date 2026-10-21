import SALT.Generated.QS8VLReLU.Proof

namespace SALT.Test.QS8VLReLU

open SALT.Generated.QS8VLReLU
open SALT.Kernel.QS8VLReLU

private def i32 (value : Int) : BitVec 32 := BitVec.ofInt 32 value

private def harnessParams : QS8LReLUParams where
  input_zero_point := i32 8
  positive_multiplier := i32 256
  negative_multiplier := i32 64
  output_zero_point := i32 (-4)

private def negativeSlopeEndpoint : QS8LReLUParams where
  input_zero_point := i32 (-128)
  positive_multiplier := i32 32768
  negative_multiplier := i32 (-32767)
  output_zero_point := i32 127

private def zeroNegativeMultiplier : QS8LReLUParams where
  input_zero_point := i32 0
  positive_multiplier := i32 1
  negative_multiplier := i32 0
  output_zero_point := i32 0

example : WellFormedParams harnessParams := by
  unfold WellFormedParams
  decide

example : WellFormedParams negativeSlopeEndpoint := by
  unfold WellFormedParams
  decide

example : Not (WellFormedParams zeroNegativeMultiplier) := by
  unfold WellFormedParams
  decide

end SALT.Test.QS8VLReLU
