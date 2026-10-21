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
example : FP32.maxPropagatingNaN 0x7FC00001 0xFFA00002 =
    (0xFFE00002 : BitVec 32) := by decide
example : FP32.minPropagatingNaN 0x7FA00001 0xFFA00002 =
    (0x7FE00001 : BitVec 32) := by decide

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
#eval if FP32.sub 0x40400000 0x3F800000 == (0x40000000 : BitVec 32)
  then true else panic! "FP32.sub"
#eval if FP32.add 0x7FA00001 0x3F800000 == (0x7FC00000 : BitVec 32)
  then true else panic! "FP32.add canonical input NaN"
#eval if FP32.add 0x7F800000 0xFF800000 == (0x7FC00000 : BitVec 32)
  then true else panic! "FP32.add invalid infinity"
#eval if FP32.sub 0x7F800000 0x7F800000 == (0x7FC00000 : BitVec 32)
  then true else panic! "FP32.sub invalid infinity"
#eval if FP32.armAddDN0AH0 0x7FA00001 0x3F800000 ==
    (0x7FE00001 : BitVec 32)
  then true else panic! "FP32.armAddDN0AH0 signaling NaN"
#eval if FP32.armSubDN0AH0 0x3F800000 0xFFA00002 ==
    (0xFFE00002 : BitVec 32)
  then true else panic! "FP32.armSubDN0AH0 right signaling NaN"
#eval if FP32.armAddDN0AH0 0x7FC00001 0xFFA00002 ==
    (0xFFE00002 : BitVec 32)
  then true else panic! "FP32.armAddDN0AH0 signaling priority"
#eval if FP32.armAddDN0AH0 0x7FC00001 0xFFC00002 ==
    (0x7FC00001 : BitVec 32)
  then true else panic! "FP32.armAddDN0AH0 operand priority"
#eval if FP32.armAddDN0AH0 0x7FA00001 0xFFA00002 ==
    (0x7FE00001 : BitVec 32)
  then true else panic! "FP32.armAddDN0AH0 signaling operand priority"
#eval if FP32.armAddDN0AH0 0x7F800000 0xFF800000 ==
    (0x7FC00000 : BitVec 32)
  then true else panic! "FP32.armAddDN0AH0 invalid infinity"
#eval if FP32.armSubDN0AH0 0x7F800000 0x7F800000 ==
    (0x7FC00000 : BitVec 32)
  then true else panic! "FP32.armSubDN0AH0 invalid infinity"
#eval if FP32.mul 0x40000000 0x40400000 == (0x40C00000 : BitVec 32)
  then true else panic! "FP32.mul"
#eval if FP32.mul 0x7FA00001 0x3F800000 == (0x7FC00000 : BitVec 32)
  then true else panic! "FP32.mul canonical input NaN"
#eval if FP32.mul 0x00000000 0x7F800000 == (0x7FC00000 : BitVec 32)
  then true else panic! "FP32.mul invalid"
#eval if FP32.armMulDN0AH0 0x7FA00001 0x3F800000 ==
    (0x7FE00001 : BitVec 32)
  then true else panic! "FP32.armMulDN0AH0 signaling NaN"
#eval if FP32.armMulDN0AH0 0x00000000 0x7F800000 ==
    (0x7FC00000 : BitVec 32)
  then true else panic! "FP32.armMulDN0AH0 invalid zero infinity"
#eval if FP32.div 0x3F800000 0x00000000 == (0x7F800000 : BitVec 32)
  then true else panic! "FP32.div"
#eval if FP32.div 0x00000000 0x00000000 == (0x7FC00000 : BitVec 32)
  then true else panic! "FP32.div invalid"
#eval if FP32.armDivDN0AH0 0x7FA00001 0x3F800000 ==
    (0x7FE00001 : BitVec 32)
  then true else panic! "FP32.armDivDN0AH0 signaling NaN"
#eval if FP32.armDivDN0AH0 0x00000000 0x00000000 ==
    (0x7FC00000 : BitVec 32)
  then true else panic! "FP32.armDivDN0AH0 invalid zero zero"
#eval if FP32.sqrt 0x40800000 == (0x40000000 : BitVec 32)
  then true else panic! "FP32.sqrt"
#eval if FP32.sqrt 0x7FA00001 == (0x7FC00000 : BitVec 32)
  then true else panic! "FP32.sqrt canonical input NaN"
#eval if FP32.sqrt 0xBF800000 == (0x7FC00000 : BitVec 32)
  then true else panic! "FP32.sqrt invalid"
#eval if FP32.armSqrtDN0AH0 0xFFA00002 == (0xFFE00002 : BitVec 32)
  then true else panic! "FP32.armSqrtDN0AH0 signaling NaN"
#eval if FP32.armSqrtDN0AH0 0xBF800000 == (0x7FC00000 : BitVec 32)
  then true else panic! "FP32.armSqrtDN0AH0 invalid negative"
example : FP32.abs 0xFFC00001 = (0x7FC00001 : BitVec 32) := by
  decide

example : FP32.ne 0x7FC00001 0x7FC00001 = true := by decide
example : FP32.ne 0x00000000 0x80000000 = false := by decide
example : FP32.ne 0x3F800000 0x3F800000 = false := by decide
example : FP32.ne 0x3F800000 0x40000000 = true := by decide
example : FP32.ne 0x7F800000 0x7F800000 = false := by decide
example (value : BitVec 32) : FP32.ne value value = FP32.isNaN value := by
  exact FP32.ne_self value
example : FP32.lt 0x7FC00001 0x3F800000 = false := by decide
example : FP32.lt 0x3F800000 0x7FA00001 = false := by decide
example : FP32.lt 0x80000000 0x00000000 = false := by decide
example : FP32.lt 0xBF800000 0x00000000 = true := by decide
example : FP32.lt 0x00000000 0x3F800000 = true := by decide
example : FP32.lt 0xFF800000 0x7F800000 = true := by decide

private def vrndneNeonWitness : BitVec 32 :=
  let input : List (BitVec 32) := [0x7FA00001]
  let magic : List (BitVec 32) := [0x4B000000]
  let absolute := Neon.vabsq_f32 input
  let mask := Neon.vcaltq_f32 magic input
  let rounded := Neon.vsubq_f32 (Neon.vaddq_f32 absolute magic) magic
  let signedMask := Neon.vorrq_u32 mask [0x80000000]
  (Neon.vbslq_f32 signedMask input rounded).headD 0

private def vrndneRvvWitness : BitVec 32 :=
  let input : List (BitVec 32) := [0x7FA00001]
  let absolute := RVV.vfabs_v_f32 input
  let aboveMagic := RVV.vmfgt_vf_f32 absolute 0x4B000000
  let rounded := RVV.vfsub_vf_f32 (RVV.vfadd_vf_f32 absolute 0x4B000000) 0x4B000000
  let signed := RVV.vfsgnj_vv_f32 rounded input
  let selected := RVV.vmerge_vvm_f32 signed input aboveMagic
  let isNaN := RVV.vmfne_vv_f32 input input
  let quieted := RVV.vor_vx_u32 input 0x00400000
  (RVV.vmerge_vvm_f32 selected quieted isNaN).headD 0

example : vrndneNeonWitness = (0x7FE00001 : BitVec 32) := by decide
example : vrndneRvvWitness = (0x7FE00001 : BitVec 32) := by decide

end SALT.Test.FP32
