import SALT.Intrinsics.FP32
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV

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

-- Arm FMAX/FMIN propagate and quiet the selected NaN payload.
example : FP32.maxPropagatingNaN 0x7FA00001 0x3F800000 =
    (0x7FE00001 : BitVec 32) := by decide
example : FP32.minPropagatingNaN 0x3F800000 0xFFA00002 =
    (0xFFE00002 : BitVec 32) := by decide

-- RVV VFMAX/VFMIN implement maximumNumber/minimumNumber and signed-zero order.
example : FP32.maxNumber 0x7FC00001 0x3F800000 =
    (0x3F800000 : BitVec 32) := by decide
example : FP32.minNumber 0x7FC00001 0x7FC00002 =
    (0x7FC00000 : BitVec 32) := by decide
#eval if FP32.maxNumber 0x80000000 0x00000000 ==
    (0x00000000 : BitVec 32) then true else panic! "FP32.maxNumber signed zero"
#eval if FP32.minNumber 0x80000000 0x00000000 ==
    (0x80000000 : BitVec 32) then true else panic! "FP32.minNumber signed zero"

-- Sign/selection operations preserve payload bits and comparisons reject NaNs.
example : RVV.vfsgnj_vv_f32 [0x7FC00001] [0x80000000] =
    [(0xFFC00001 : BitVec 32)] := by decide
example : Neon.vbslq_f32 [0xFFFF0000] [0x12345678] [0xABCDEF01] =
    [(0x1234EF01 : BitVec 32)] := by decide
#eval if RVV.vmfgt_vf_f32 [0x7FC00001] 0x3F800000 == [false]
  then true else panic! "RVV.vmfgt_vf_f32 NaN"
#eval if RVV.vmfne_vv_f32 [0x7FC00001] [0x7FC00001] == [true]
  then true else panic! "RVV.vmfne_vv_f32 NaN"

-- The shared arithmetic primitive fixes the value model to binary32/RNE.
#eval if FP32.add 0x3F800000 0x40000000 == (0x40400000 : BitVec 32)
  then true else panic! "FP32.add"
#eval if FP32.mul 0x40000000 0x40400000 == (0x40C00000 : BitVec 32)
  then true else panic! "FP32.mul"
#eval if FP32.div 0x3F800000 0x00000000 == (0x7F800000 : BitVec 32)
  then true else panic! "FP32.div"
#eval if FP32.sqrt 0x40800000 == (0x40000000 : BitVec 32)
  then true else panic! "FP32.sqrt"
example : FP32.abs 0xFFC00001 = (0x7FC00001 : BitVec 32) := by
  decide

end SALT.Test.FP32
