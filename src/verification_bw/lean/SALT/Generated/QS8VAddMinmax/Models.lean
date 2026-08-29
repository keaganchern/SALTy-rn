-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.QS8.Params

namespace SALT.Generated.QS8VAddMinmax

open SALT.Kernel.QS8

def neonSourceSha256 : String :=
  "01a0bdcc9344c5f095a47a79ce0d346bd44e937ceceefd1f12e275f9091456f3"
def rvvSourceSha256 : String :=
  "1e8af584a849673c663f114ba74cc436dbd4eb33819113a80424d67bc0abddb1"
def neonPreprocessedSha256 : String :=
  "319a5b740a907ad54e47f8117d010f73679123df560384482a1f6bac1aa9cbd1"
def rvvPreprocessedSha256 : String :=
  "8494a3775292164ac5c7ea702e35564ad32b231084990e051e7683d3053c4c95"
def parseFacadeSha256 : String :=
  "bf718e923d59d83073524c04af8881ded5413be50005bba97889f08cb154e8df"
def registrySourceSha256 : String :=
  "f5054a8b4b263af58ba71267db7b554cea04f08a2aef80094c0cad79960c35e5"

def neonBlock16FromIntrinsics (p : QS8AddMinmaxParams)
    (chunk_a chunk_b : List (BitVec 8)) : List (BitVec 8) :=
  let va_zero_point_0 := List.replicate 8 (p.a_zero_point)
  let vb_zero_point_0 := List.replicate 8 (p.b_zero_point)
  let va01234567_0 := (chunk_a).take 8
  let vb01234567_0 := (chunk_b).take 8
  let va89ABCDEF_0 := ((chunk_a).drop 8).take 8
  let vb89ABCDEF_0 := ((chunk_b).drop 8).take 8
  let vxa01234567_0 := SALT.Intrinsics.Neon.vsubl_s8 (va01234567_0) (va_zero_point_0)
  let vxb01234567_0 := SALT.Intrinsics.Neon.vsubl_s8 (vb01234567_0) (vb_zero_point_0)
  let vxa89ABCDEF_0 := SALT.Intrinsics.Neon.vsubl_s8 (va89ABCDEF_0) (va_zero_point_0)
  let vxb89ABCDEF_0 := SALT.Intrinsics.Neon.vsubl_s8 (vb89ABCDEF_0) (vb_zero_point_0)
  let call_0016 := (vxa01234567_0).take 4
  let call_0017 := SALT.Intrinsics.Neon.vmovl_s16 (call_0016)
  let vacc0123_0 := SALT.Intrinsics.Neon.vmulq_s32 (call_0017) (p.a_multiplier)
  let call_0019 := (vxa01234567_0).drop 4
  let call_0020 := SALT.Intrinsics.Neon.vmovl_s16 (call_0019)
  let vacc4567_0 := SALT.Intrinsics.Neon.vmulq_s32 (call_0020) (p.a_multiplier)
  let call_0022 := (vxa89ABCDEF_0).take 4
  let call_0023 := SALT.Intrinsics.Neon.vmovl_s16 (call_0022)
  let vacc89AB_0 := SALT.Intrinsics.Neon.vmulq_s32 (call_0023) (p.a_multiplier)
  let call_0025 := (vxa89ABCDEF_0).drop 4
  let call_0026 := SALT.Intrinsics.Neon.vmovl_s16 (call_0025)
  let vaccCDEF_0 := SALT.Intrinsics.Neon.vmulq_s32 (call_0026) (p.a_multiplier)
  let call_0028 := (vxb01234567_0).take 4
  let call_0029 := SALT.Intrinsics.Neon.vmovl_s16 (call_0028)
  let vacc0123_1 := SALT.Intrinsics.Neon.vmlaq_s32 (vacc0123_0) (call_0029) (p.b_multiplier)
  let call_0031 := (vxb01234567_0).drop 4
  let call_0032 := SALT.Intrinsics.Neon.vmovl_s16 (call_0031)
  let vacc4567_1 := SALT.Intrinsics.Neon.vmlaq_s32 (vacc4567_0) (call_0032) (p.b_multiplier)
  let call_0034 := (vxb89ABCDEF_0).take 4
  let call_0035 := SALT.Intrinsics.Neon.vmovl_s16 (call_0034)
  let vacc89AB_1 := SALT.Intrinsics.Neon.vmlaq_s32 (vacc89AB_0) (call_0035) (p.b_multiplier)
  let call_0037 := (vxb89ABCDEF_0).drop 4
  let call_0038 := SALT.Intrinsics.Neon.vmovl_s16 (call_0037)
  let vaccCDEF_1 := SALT.Intrinsics.Neon.vmlaq_s32 (vaccCDEF_0) (call_0038) (p.b_multiplier)
  let vacc0123_2 := SALT.Intrinsics.Neon.vrshlq_s32 (vacc0123_1) ((p.shift).toNat)
  let vacc4567_2 := SALT.Intrinsics.Neon.vrshlq_s32 (vacc4567_1) ((p.shift).toNat)
  let vacc89AB_2 := SALT.Intrinsics.Neon.vrshlq_s32 (vacc89AB_1) ((p.shift).toNat)
  let vaccCDEF_2 := SALT.Intrinsics.Neon.vrshlq_s32 (vaccCDEF_1) ((p.shift).toNat)
  let call_0044 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc0123_2)
  let call_0045 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc4567_2)
  let call_0046 := call_0044 ++ call_0045
  let vacc01234567_0 := SALT.Intrinsics.Neon.vqaddq_s16 (call_0046) (p.output_zero_point)
  let call_0048 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc89AB_2)
  let call_0049 := SALT.Intrinsics.Neon.vqmovn_s32 (vaccCDEF_2)
  let call_0050 := call_0048 ++ call_0049
  let vacc89ABCDEF_0 := SALT.Intrinsics.Neon.vqaddq_s16 (call_0050) (p.output_zero_point)
  let call_0052 := SALT.Intrinsics.Neon.vqmovn_s16 (vacc01234567_0)
  let call_0053 := SALT.Intrinsics.Neon.vqmovn_s16 (vacc89ABCDEF_0)
  let vout0123456789ABCDEF_0 := call_0052 ++ call_0053
  let vout0123456789ABCDEF_1 := SALT.Intrinsics.Neon.vmax_s8 (vout0123456789ABCDEF_0) (p.output_min)
  let vout0123456789ABCDEF_2 := SALT.Intrinsics.Neon.vmin_s8 (vout0123456789ABCDEF_1) (p.output_max)
  vout0123456789ABCDEF_2

def rvvBlockFromIntrinsics (p : QS8AddMinmaxParams)
    (chunk_a chunk_b : List (BitVec 8)) : List (BitVec 8) :=
  let va_0 := chunk_a
  let vb_0 := chunk_b
  let vxa_0 := SALT.Intrinsics.RVV.vwsub_vx (va_0) (p.a_zero_point)
  let vxb_0 := SALT.Intrinsics.RVV.vwsub_vx (vb_0) (p.b_zero_point)
  let vxa32_0 := SALT.Intrinsics.RVV.vsext_vf2 (vxa_0)
  let vxb32_0 := SALT.Intrinsics.RVV.vsext_vf2 (vxb_0)
  let vacc_0 := SALT.Intrinsics.RVV.vmul_vx (vxa32_0) (p.a_multiplier)
  let vacc_1 := SALT.Intrinsics.RVV.vmacc_vx (vacc_0) (p.b_multiplier) (vxb32_0)
  let vacc_2 := SALT.Intrinsics.RVV.vssra_vx_rnu (vacc_1) ((p.shift).toNat)
  let vacc16_0 := SALT.Intrinsics.RVV.vnclip_wx_i16 (vacc_2)
  let vacc16_1 := SALT.Intrinsics.RVV.vsadd_vx (vacc16_0) (p.output_zero_point)
  let vout_0 := SALT.Intrinsics.RVV.vnclip_wx_i8 (vacc16_1)
  let vout_1 := SALT.Intrinsics.RVV.vmax_vx (vout_0) (p.output_min)
  let vout_2 := SALT.Intrinsics.RVV.vmin_vx (vout_1) (p.output_max)
  vout_2

end SALT.Generated.QS8VAddMinmax
