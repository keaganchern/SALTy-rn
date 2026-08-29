import SALT.Intrinsics.FP32

namespace SALT.Test.FP32

open SALT.Intrinsics

example : FP32.toInt32RNE 0x3F000000 = (0 : BitVec 32) := by decide
example : FP32.toInt32RNE 0x3F000001 = (1 : BitVec 32) := by decide
example : FP32.toInt32RNE 0x3FC00000 = (2 : BitVec 32) := by decide
example : FP32.toInt32RNE 0x40200000 = (2 : BitVec 32) := by decide
example : FP32.toInt32RNE 0x40600000 = (4 : BitVec 32) := by decide
example : FP32.toInt32RNE 0xBFC00000 = (0xFFFFFFFE : BitVec 32) := by
  decide

example : FP32.toInt32RNE 0x7FC00001 = (0x7FFFFFFF : BitVec 32) := by
  decide
example : FP32.toInt32RNE 0x7F800000 = (0x7FFFFFFF : BitVec 32) := by
  decide
example : FP32.toInt32RNE 0xFF800000 = (0x80000000 : BitVec 32) := by
  decide
example : FP32.toInt32RNE 0x4F000000 = (0x7FFFFFFF : BitVec 32) := by
  decide
example : FP32.toInt32RNE 0xCF000000 = (0x80000000 : BitVec 32) := by
  decide

end SALT.Test.FP32
