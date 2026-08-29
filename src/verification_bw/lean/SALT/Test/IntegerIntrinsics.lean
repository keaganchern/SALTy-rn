import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV

namespace SALT.Test.IntegerIntrinsics

private def i8 (value : Int) : BitVec 8 := BitVec.ofInt 8 value
private def i16 (value : Int) : BitVec 16 := BitVec.ofInt 16 value
private def i32 (value : Int) : BitVec 32 := BitVec.ofInt 32 value

example : SALT.Intrinsics.Neon.sqrdmulh_s16 (i16 (-32768)) (i16 (-32768)) = i16 32767 := by
  rfl

example : SALT.Intrinsics.Neon.sqrdmulh_s16 (i16 16384) (i16 16384) = i16 8192 := by
  rfl

example : SALT.Intrinsics.RVV.vnclipSigned 16 .rnu 16 (i32 98304) = i16 2 := by
  rfl

example : SALT.Intrinsics.RVV.vnclipSigned 16 .rnu 16 (i32 (-98304)) = i16 (-1) := by
  rfl

example : SALT.Intrinsics.RVV.vnclipSigned 16 .rdn 16 (i32 (-98304)) = i16 (-2) := by
  rfl

example : SALT.Intrinsics.RVV.vnclipSigned 16 .rne 16 (i32 32768) = i16 0 := by
  rfl

example : SALT.Intrinsics.RVV.vnclipSigned 16 .rod 16 (i32 131073) = i16 3 := by
  rfl

example : SALT.Intrinsics.RVV.vnclip_wx_i16_mode [i32 98304] 16 0 = [i16 2] := by
  rfl

example : SALT.Intrinsics.RVV.vnclip_wx_i8_mode [i16 300, i16 (-200)] 0 2 =
    [i8 127, i8 (-128)] := by
  rfl

example : SALT.Intrinsics.RVV.vnclipu_wx_u8_mode [i16 300] 0 2 = [i8 255] := by
  rfl

/-- The RVV instruction sequence wraps before narrowing at the one input pair
    where NEON qrdmulh saturates. A kernel proof therefore needs a parameter
    contract excluding this pair, or a different RVV lowering. -/
example :
    SALT.Intrinsics.RVV.vnclip_wx_i16_mode
      (SALT.Intrinsics.RVV.vsll_vx_i32
        (SALT.Intrinsics.RVV.vwmul_vx_i32 [i16 (-32768)] (i16 (-32768))) 1)
      16 0 = [i16 (-32768)] := by
  rfl

example : SALT.Intrinsics.Neon.vcltq_s16 [i16 (-1), i16 1] [i16 0, i16 0] =
    [BitVec.allOnes 16, i16 0] := by
  rfl

example :
    SALT.Intrinsics.Neon.vbslq_s16
      [BitVec.allOnes 16, i16 0] [i16 7, i16 8] [i16 9, i16 10] =
      [i16 7, i16 10] := by
  rfl

example : SALT.Intrinsics.RVV.vmerge_vxm_i16 [i16 7, i16 8] (i16 9) [true, false] =
    [i16 9, i16 8] := by
  rfl

example : SALT.Intrinsics.Neon.vsubl_u8 [i8 0] [i8 255] = [i16 (-255)] := by
  rfl

example : SALT.Intrinsics.Neon.vqmovun_s16 [i16 (-1), i16 300] = [i8 0, i8 255] := by
  rfl

example : SALT.Intrinsics.RVV.vshift_signed_i32_rnu [i32 3] (i32 1) = [i32 2] := by
  rfl

example : SALT.Intrinsics.RVV.vshift_signed_i32_rnu [i32 3] (i32 (-1)) = [i32 6] := by
  rfl

example : SALT.Intrinsics.RVV.vnsrl_wx_u16 [BitVec.ofNat 32 0x12345678] 32 =
    [BitVec.ofNat 16 0x5678] := by
  decide

example : SALT.Intrinsics.RVV.vsll_vx_i16 [i16 3] 16 = [i16 3] := by
  decide

example : SALT.Intrinsics.RVV.vsll_vx_i32 [i32 3] 33 = [i32 6] := by
  decide

example : SALT.Intrinsics.RVV.vssra_vx_i32_mode [i32 (-3)] 33 0 = [i32 (-1)] := by
  decide

example : SALT.Intrinsics.RVV.vnclip_wx_i16_mode [i32 65536] 48 0 = [i16 1] := by
  decide

end SALT.Test.IntegerIntrinsics
