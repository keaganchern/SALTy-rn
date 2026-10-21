import SALT.Generated.QS8VCvt.Proof

namespace SALT.Test.QS8VCvt

open SALT.Generated.QS8VCvt
open SALT.Kernel.QS8VCvt

private def i8 (value : Int) : BitVec 8 := BitVec.ofInt 8 value
private def i16 (value : Int) : BitVec 16 := BitVec.ofInt 16 value
private def i32 (value : Int) : BitVec 32 := BitVec.ofInt 32 value

private def wrappingCorner : QS8CvtParams where
  input_zero_point := i16 128
  multiplier := i32 32768
  output_zero_point := i16 0

private def harnessParams : QS8CvtParams where
  input_zero_point := i16 10
  multiplier := i32 192
  output_zero_point := i16 (-5)

private def wrappingInput : List (BitVec 8) :=
  List.replicate 8 (i8 (-128))

example : WellFormedParams harnessParams := by
  unfold WellFormedParams
  decide

example : ¬ WellFormedParams wrappingCorner := by
  unfold WellFormedParams
  decide

example :
    neonBlock8FromIntrinsics wrappingCorner wrappingInput =
      List.replicate 8 (i8 127) := by
  rfl

example :
    rvvChunkFromIntrinsics wrappingCorner wrappingInput = wrappingInput := by
  rfl

example :
    neonBlock8FromIntrinsics wrappingCorner wrappingInput ≠
      rvvChunkFromIntrinsics wrappingCorner wrappingInput := by
  decide

end SALT.Test.QS8VCvt
