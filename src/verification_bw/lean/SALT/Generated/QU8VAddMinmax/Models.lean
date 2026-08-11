-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV

namespace SALT.Generated.QU8VAddMinmax

def neonSourceSha256 : String :=
  "7f6435954cc0ac4ab31881da9ff8b16f04abdfc8da0c1a945b15b64f3bcb2294"
def rvvSourceSha256 : String :=
  "e211e5fc712d38ea90776aff23bcdfe72ecec23aa08b5999683b483adfb2bbc9"
def neonPreprocessedSha256 : String :=
  "655d4240b2596f1cff6772bd19497a523649ba8eb337074af91e3709b72309c8"
def rvvPreprocessedSha256 : String :=
  "56dc3b779696422d0fc17702bc6e9ca72e925a2444b1b1ebfc864eac4386bcb6"
def parseFacadeSha256 : String :=
  "4b25fb1efa8257055b91ad1967db49dda327e9b883428797d8aa52ca79e38502"
def registrySha256 : String :=
  "ae699a8a3b35bc88dad4b79325246c9674b88c790b89d637a5abae4e3fc25f47"

structure QU8AddMinmaxParams where
  a_zero_point : BitVec 8
  b_zero_point : BitVec 8
  a_multiplier : BitVec 32
  b_multiplier : BitVec 32
  shift : BitVec 32
  output_zero_point : BitVec 16
  output_min : BitVec 8
  output_max : BitVec 8
  deriving Repr, DecidableEq

def neonBlock8FromIntrinsics (p : QU8AddMinmaxParams)
    (input_a : List (BitVec 8))
    (input_b : List (BitVec 8)) : List (BitVec 8) :=
  let va_zero_point_0 := List.replicate 8 ((p.a_zero_point).truncate 8)
  let vb_zero_point_0 := List.replicate 8 ((p.b_zero_point).truncate 8)
  let va_multiplier_0 := List.replicate 4 ((p.a_multiplier).truncate 32)
  let vb_multiplier_0 := List.replicate 4 ((p.b_multiplier).truncate 32)
  let vright_shift_0 := List.replicate 4 (-(p.shift).truncate 32)
  let voutput_zero_point_0 := List.replicate 8 ((p.output_zero_point).truncate 16)
  let voutput_min_0 := List.replicate 8 ((p.output_min).truncate 8)
  let voutput_max_0 := List.replicate 8 ((p.output_max).truncate 8)
  let va01234567_0 := (input_a).take 8
  let vb01234567_0 := (input_b).take 8
  let call_0010 := SALT.Intrinsics.Neon.vsubl_u8 (va01234567_0) (va_zero_point_0)
  let vxa01234567_0 := call_0010
  let call_0012 := SALT.Intrinsics.Neon.vsubl_u8 (vb01234567_0) (vb_zero_point_0)
  let vxb01234567_0 := call_0012
  let call_0014 := (vxa01234567_0).take 4
  let call_0015 := SALT.Intrinsics.Neon.vmovl_s16 (call_0014)
  let vacc0123_0 := SALT.Intrinsics.Neon.vmulq_s32 (call_0015) ((p.a_multiplier).truncate 32)
  let call_0017 := (vxa01234567_0).drop 4
  let call_0018 := SALT.Intrinsics.Neon.vmovl_s16 (call_0017)
  let vacc4567_0 := SALT.Intrinsics.Neon.vmulq_s32 (call_0018) ((p.a_multiplier).truncate 32)
  let call_0020 := (vxb01234567_0).take 4
  let call_0021 := SALT.Intrinsics.Neon.vmovl_s16 (call_0020)
  let vacc0123_1 := SALT.Intrinsics.Neon.vmlaq_s32 (vacc0123_0) (call_0021) ((p.b_multiplier).truncate 32)
  let call_0023 := (vxb01234567_0).drop 4
  let call_0024 := SALT.Intrinsics.Neon.vmovl_s16 (call_0023)
  let vacc4567_1 := SALT.Intrinsics.Neon.vmlaq_s32 (vacc4567_0) (call_0024) ((p.b_multiplier).truncate 32)
  let vacc0123_2 := SALT.Intrinsics.Neon.vrshlq_s32_vec (vacc0123_1) (vright_shift_0)
  let vacc4567_2 := SALT.Intrinsics.Neon.vrshlq_s32_vec (vacc4567_1) (vright_shift_0)
  let call_0028 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc0123_2)
  let call_0029 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc4567_2)
  let call_0030 := call_0028 ++ call_0029
  let vacc01234567_0 := SALT.Intrinsics.Neon.vqaddq_s16 (call_0030) ((p.output_zero_point).truncate 16)
  let vout01234567_0 := SALT.Intrinsics.Neon.vqmovun_s16 (vacc01234567_0)
  let vout01234567_1 := SALT.Intrinsics.Neon.vmax_u8 (vout01234567_0) (voutput_min_0)
  let vout01234567_2 := SALT.Intrinsics.Neon.vmin_u8 (vout01234567_1) (voutput_max_0)
  (vout01234567_2)

def rvvChunkFromIntrinsics (p : QU8AddMinmaxParams)
    (input_a : List (BitVec 8))
    (input_b : List (BitVec 8)) : List (BitVec 8) :=
  let va_0 := input_a
  let vb_0 := input_b
  let vxa_u_0 := SALT.Intrinsics.RVV.vwsubu_vx_u16 (va_0) ((p.a_zero_point).truncate 8)
  let vxa_0 := vxa_u_0
  let vxb_u_0 := SALT.Intrinsics.RVV.vwsubu_vx_u16 (vb_0) ((p.b_zero_point).truncate 8)
  let vxb_0 := vxb_u_0
  let vxa32_0 := SALT.Intrinsics.RVV.vsext_vf2 (vxa_0)
  let vacc_0 := SALT.Intrinsics.RVV.vmul_vx (vxa32_0) ((p.a_multiplier).truncate 32)
  let vxb32_0 := SALT.Intrinsics.RVV.vsext_vf2 (vxb_0)
  let vacc_1 := SALT.Intrinsics.RVV.vmacc_vx (vacc_0) ((p.b_multiplier).truncate 32) (vxb32_0)
  let vacc_2 := SALT.Intrinsics.RVV.vssra_vx_i32_mode (vacc_1) (((p.shift).truncate 32).toNat) (0)
  let vacc_3 := SALT.Intrinsics.RVV.vsll_vx_i32 (vacc_1) ((-((p.shift).truncate 32).toInt).toNat)
  let vacc_3_join := if ((p.shift).truncate 32).toInt >= 0 then vacc_2 else vacc_3
  let vacc16_0 := SALT.Intrinsics.RVV.vnclip_wx_i16_mode (vacc_3_join) (0) (2)
  let vacc16_1 := SALT.Intrinsics.RVV.vsadd_vx (vacc16_0) ((p.output_zero_point).truncate 16)
  let vacc16_2 := SALT.Intrinsics.RVV.vmax_vx_i16 (vacc16_1) (0)
  let vacc16_u_0 := vacc16_2
  let vout_0 := SALT.Intrinsics.RVV.vnclipu_wx_u8_mode (vacc16_u_0) (0) (2)
  let vout_1 := SALT.Intrinsics.RVV.vmaxu_vx_u8 (vout_0) ((p.output_min).truncate 8)
  let vout_2 := SALT.Intrinsics.RVV.vminu_vx_u8 (vout_1) ((p.output_max).truncate 8)
  vout_2

end SALT.Generated.QU8VAddMinmax
