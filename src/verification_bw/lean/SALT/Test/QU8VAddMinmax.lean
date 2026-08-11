import SALT.Generated.QU8VAddMinmax.Proof

namespace SALT.Test.QU8VAddMinmax

open SALT.Generated.QU8VAddMinmax
open SALT.Kernel.QU8VAddMinmax

private def u8 (value : Nat) : BitVec 8 := BitVec.ofNat 8 value
private def i16 (value : Int) : BitVec 16 := BitVec.ofInt 16 value
private def i32 (value : Int) : BitVec 32 := BitVec.ofInt 32 value

private def producerParams : QU8AddMinmaxParams where
  a_zero_point := u8 130
  b_zero_point := u8 120
  a_multiplier := i32 1048576
  b_multiplier := i32 1048576
  shift := i32 20
  output_zero_point := i16 128
  output_min := u8 0
  output_max := u8 255

private def harnessParams : QU8AddMinmaxParams where
  a_zero_point := u8 130
  b_zero_point := u8 120
  a_multiplier := i32 2
  b_multiplier := i32 3
  shift := i32 2
  output_zero_point := i16 128
  output_min := u8 0
  output_max := u8 255

example : WellFormedParams producerParams := by
  unfold WellFormedParams producerParams u8 i16 i32
  decide

example : Not (WellFormedParams harnessParams) := by
  unfold WellFormedParams harnessParams u8 i16 i32
  decide

example (inputA inputB : List (BitVec 8))
    (hA : inputA.length = 8) (hB : inputB.length = 8) :
    neonBlock8FromIntrinsics producerParams inputA inputB =
      rvvChunkFromIntrinsics producerParams inputA inputB := by
  apply generated_block_equal producerParams (by
    unfold WellFormedParams producerParams u8 i16 i32
    decide) inputA inputB hA hB

example (inputA inputB : List (BitVec 8))
    (hA : inputA.length = 8) (hB : inputB.length = 8) :
    neonBlock8FromIntrinsics harnessParams inputA inputB =
      rvvChunkFromIntrinsics harnessParams inputA inputB := by
  apply generated_block_equal_of_shift_le harnessParams (by
    unfold harnessParams i32
    decide) inputA inputB hA hB

end SALT.Test.QU8VAddMinmax
