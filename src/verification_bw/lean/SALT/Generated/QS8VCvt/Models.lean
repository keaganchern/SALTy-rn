-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV

namespace SALT.Generated.QS8VCvt

def neonSourceSha256 : String :=
  "715bd7cd48e9241c1a56b287cbfc2c7e2fbbc100e22226abea93d438b137530d"
def rvvSourceSha256 : String :=
  "19da29a3dd0c32ac1a44ad5cec73b0e25d81ecd765a60e9a01e6a128c21f4b76"
def neonPreprocessedSha256 : String :=
  "ef12c4fd0f90356e272f514099e669fd748c97d9740f4f3ddc22d59595723e28"
def rvvPreprocessedSha256 : String :=
  "733efa4bed1f4f407b6d51e0dcffe04b28be27cb0e40c1d534ccb1a4e17f8972"
def parseFacadeSha256 : String :=
  "6e8a1a41f53ecd88abdff17e8a4ca08aa47199a189155d4a7bbc551f4891fa54"
def registrySha256 : String :=
  "de5dd90a7df5f87e96da3117c989da05a0bbdab03b599447842cb9abd28ebe9d"

structure QS8CvtParams where
  input_zero_point : BitVec 16
  multiplier : BitVec 32
  output_zero_point : BitVec 16
  deriving Repr, DecidableEq

def neonBlock8FromIntrinsics (p : QS8CvtParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vinput_zero_point_0 := List.replicate 8 ((p.input_zero_point).truncate 16)
  let vmultiplier_0 := List.replicate 8 (-(p.multiplier).truncate 16)
  let voutput_zero_point_0 := List.replicate 8 ((p.output_zero_point).truncate 16)
  let vx_0 := (input).take 8
  let vacc_0 := SALT.Intrinsics.Neon.vsubw_s8 (vinput_zero_point_0) (vx_0)
  let vacc_1 := SALT.Intrinsics.Neon.vshlq_n_s16 (vacc_0) (7)
  let vacc_2 := SALT.Intrinsics.Neon.vqrdmulhq_s16 (vacc_1) (vmultiplier_0)
  let vacc_3 := SALT.Intrinsics.Neon.vqaddq_s16 (vacc_2) ((p.output_zero_point).truncate 16)
  let vy_0 := SALT.Intrinsics.Neon.vqmovn_s16 (vacc_3)
  (vy_0)

def rvvChunkFromIntrinsics (p : QS8CvtParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vx_0 := input
  let vx_w_0 := SALT.Intrinsics.RVV.vsext_vf2_i16 (vx_0)
  let vacc_0 := SALT.Intrinsics.RVV.vrsub_vx_i16 (vx_w_0) ((p.input_zero_point).truncate 16)
  let vacc_1 := SALT.Intrinsics.RVV.vsll_vx_i16 (vacc_0) (7)
  let prod_0 := SALT.Intrinsics.RVV.vwmul_vx_i32 (vacc_1) (((-p.multiplier)).truncate 16)
  let prod_1 := SALT.Intrinsics.RVV.vsll_vx_i32 (prod_0) (1)
  let vacc_2 := SALT.Intrinsics.RVV.vnclip_wx_i16_mode (prod_1) (16) (0)
  let vacc_3 := SALT.Intrinsics.RVV.vsadd_vx (vacc_2) ((p.output_zero_point).truncate 16)
  let vy_0 := SALT.Intrinsics.RVV.vnclip_wx_i8_mode (vacc_3) (0) (2)
  vy_0

end SALT.Generated.QS8VCvt
