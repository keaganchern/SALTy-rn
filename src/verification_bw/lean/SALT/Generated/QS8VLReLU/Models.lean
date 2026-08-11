-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV

namespace SALT.Generated.QS8VLReLU

def neonSourceSha256 : String :=
  "b855a4d1ecc42155b81c2355ce28f221a884bf732625c53e1000ca596abf9d4f"
def rvvSourceSha256 : String :=
  "a6821a3561b7dc9d7be3d1d0ba5582840fac0fa88c4c821abc55b8a831c5f234"
def neonPreprocessedSha256 : String :=
  "653d57f9f3b2df7f5c776356f64a31bc5ca341aac4479eef71ea5509785bdf62"
def rvvPreprocessedSha256 : String :=
  "b6ed5a5a15625a37ad325c814810a91adc48407e178d056dce381b74d2d42289"
def parseFacadeSha256 : String :=
  "142f6d01509954ce78c98dc713664c26c9e1017ca79aa6eb2a25ee717f8b808b"
def registrySha256 : String :=
  "d0fc618170288aca68120b46bf98e8ad88239ff39c97f42946857757927f9fa3"

structure QS8LReLUParams where
  input_zero_point : BitVec 32
  positive_multiplier : BitVec 32
  negative_multiplier : BitVec 32
  output_zero_point : BitVec 32
  deriving Repr, DecidableEq

def neonBlock8FromIntrinsics (p : QS8LReLUParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vinput_zero_point_0 := List.replicate 8 ((p.input_zero_point).truncate 16)
  let vpositive_multiplier_0 := List.replicate 8 (-(p.positive_multiplier).truncate 16)
  let vnegative_multiplier_0 := List.replicate 8 (-(p.negative_multiplier).truncate 16)
  let voutput_zero_point_0 := List.replicate 8 ((p.output_zero_point).truncate 16)
  let vx_0 := (input).take 8
  let vacc_0 := SALT.Intrinsics.Neon.vsubw_s8 (vinput_zero_point_0) (vx_0)
  let call_0006 := List.replicate 8 (0)
  let vmask_0 := SALT.Intrinsics.Neon.vcltq_s16 (vacc_0) (call_0006)
  let vacc_1 := SALT.Intrinsics.Neon.vshlq_n_s16 (vacc_0) (7)
  let vmultiplier_0 := SALT.Intrinsics.Neon.vbslq_s16 (vmask_0) (vpositive_multiplier_0) (vnegative_multiplier_0)
  let vacc_2 := SALT.Intrinsics.Neon.vqrdmulhq_s16 (vacc_1) (vmultiplier_0)
  let vacc_3 := SALT.Intrinsics.Neon.vqaddq_s16 (vacc_2) ((p.output_zero_point).truncate 16)
  let vy_0 := SALT.Intrinsics.Neon.vqmovn_s16 (vacc_3)
  (vy_0)

def rvvChunkFromIntrinsics (p : QS8LReLUParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vx_0 := input
  let vx_wide_0 := SALT.Intrinsics.RVV.vsext_vf2_i16 (vx_0)
  let vacc_0 := SALT.Intrinsics.RVV.vrsub_vx_i16 (vx_wide_0) ((p.input_zero_point).truncate 16)
  let vmask_0 := SALT.Intrinsics.RVV.vmslt_vx_i16 (vacc_0) (0)
  let vacc_1 := SALT.Intrinsics.RVV.vsll_vx_i16 (vacc_0) (7)
  let vneg_mult_0 := List.replicate input.length (((-p.negative_multiplier)).truncate 16)
  let vmultiplier_0 := SALT.Intrinsics.RVV.vmerge_vxm_i16 (vneg_mult_0) (((-p.positive_multiplier)).truncate 16) (vmask_0)
  let prod_0 := SALT.Intrinsics.RVV.vwmul_vv_i32 (vacc_1) (vmultiplier_0)
  let vacc_2 := SALT.Intrinsics.RVV.vnclip_wx_i16_mode (prod_0) (15) (0)
  let vacc_3 := SALT.Intrinsics.RVV.vsadd_vx (vacc_2) ((p.output_zero_point).truncate 16)
  let vy_0 := SALT.Intrinsics.RVV.vnclip_wx_i8_mode (vacc_3) (0) (2)
  vy_0

end SALT.Generated.QS8VLReLU
