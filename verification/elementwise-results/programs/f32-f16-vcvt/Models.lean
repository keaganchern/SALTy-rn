-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.ElementwiseTwoPhase
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.f32f16vcvt

def programManifestSha256 : String := "c1512c08cb2802eb4f0fe12fd4c8d18c8f8f36ec20d35b3f85e78e4de0599a6c"
def consumedEffectsSha256 : String := "b4331fdea944181b1d446ba84bccf17f2d1244864f64e6c991a2a3dbb7db5c76"

def neonSourceSha256 : String :=
  "41a081db8c9503ca62f077ad790dd92d92f2fe374e554cef8a9baf35dabd2aaa"
def rvvSourceSha256 : String :=
  "35730ec8f13c282e4b690536c738cce15a455f03eb649395253cf8be4712f851"
def neonPreprocessedSha256 : String :=
  "c03f8107ef8c9453dd2caef3e8b2d3a8e447db878ebf81d076988ec7f9600115"
def rvvPreprocessedSha256 : String :=
  "01ef726c9a7ed00a5fe9ae56c27a6b502d8279f90e9bd5aafb730b5a96df574e"
def parseFacadeSha256 : String :=
  "829b8b0358b2a31d50a784422681ac9e821a4369619812194f800dc63287c4bc"
def registrySha256 : String :=
  "0612d71589ab681fd558733f5561bf88c55e2f75029053285a5b250d39dbceea"

structure f32f16vcvtParams where
  deriving Repr, DecidableEq

def neonBlock8FromIntrinsics (p : f32f16vcvtParams)
    (input : List (BitVec 32)) : List (BitVec 16) :=
  let vexp_bias_0 := List.replicate 4 (125829120)
  let vscale_to_inf_0 := List.replicate 4 (2004877312)
  let vexpw_max_0 := List.replicate 4 (2139095040)
  let vscale_to_zero_0 := List.replicate 4 (142606336)
  let vbias_min_0 := List.replicate 4 (1073741824)
  let vexph_mask_0 := List.replicate 8 (31744)
  let vmanth_mask_0 := List.replicate 8 (4095)
  let vsignh_mask_0 := List.replicate 8 (32768)
  let vnanh_0 := List.replicate 8 (32256)
  let vx0_0 := (input).take 4
  let vx1_0 := ((input).drop 4).take 4
  let vabsx0_0 := SALT.Intrinsics.Neon.vabsq_f32 (vx0_0)
  let vabsx1_0 := SALT.Intrinsics.Neon.vabsq_f32 (vx1_0)
  let call_0013 := vabsx0_0
  let vbias0_0 := SALT.Intrinsics.Neon.vadd_u32 (call_0013) (vexp_bias_0)
  let call_0015 := vabsx1_0
  let vbias1_0 := SALT.Intrinsics.Neon.vadd_u32 (call_0015) (vexp_bias_0)
  let vf0_0 := SALT.Intrinsics.Neon.vmulq_f32 (vabsx0_0) (vscale_to_inf_0)
  let vf1_0 := SALT.Intrinsics.Neon.vmulq_f32 (vabsx1_0) (vscale_to_inf_0)
  let call_0019 := vabsx0_0
  let vnanmaskw0_0 := SALT.Intrinsics.Neon.vcgt_u32 (call_0019) (vexpw_max_0)
  let call_0021 := vabsx1_0
  let vnanmaskw1_0 := SALT.Intrinsics.Neon.vcgt_u32 (call_0021) (vexpw_max_0)
  let vbias0_1 := SALT.Intrinsics.Neon.vand_u32 (vbias0_0) (vexpw_max_0)
  let vbias1_1 := SALT.Intrinsics.Neon.vand_u32 (vbias1_0) (vexpw_max_0)
  let vf0_1 := SALT.Intrinsics.Neon.vmulq_f32 (vf0_0) (vscale_to_zero_0)
  let vf1_1 := SALT.Intrinsics.Neon.vmulq_f32 (vf1_0) (vscale_to_zero_0)
  let call_0027 := SALT.Intrinsics.Neon.vmovn_u32 (vnanmaskw0_0)
  let call_0028 := SALT.Intrinsics.Neon.vmovn_u32 (vnanmaskw1_0)
  let vnanmaskh0_0 := call_0027 ++ call_0028
  let vbias0_2 := SALT.Intrinsics.Neon.vmax_u32 (vbias0_1) (vbias_min_0)
  let vbias1_2 := SALT.Intrinsics.Neon.vmax_u32 (vbias1_1) (vbias_min_0)
  let call_0032 := vbias0_2
  let vf0_2 := SALT.Intrinsics.Neon.vaddq_f32 (vf0_1) (call_0032)
  let call_0034 := vbias1_2
  let vf1_2 := SALT.Intrinsics.Neon.vaddq_f32 (vf1_1) (call_0034)
  let call_0036 := vf0_2
  let call_0037 := SALT.Intrinsics.Neon.vshrn_n_u32 (call_0036) (13)
  let call_0038 := vf1_2
  let call_0039 := SALT.Intrinsics.Neon.vshrn_n_u32 (call_0038) (13)
  let vexph0_0 := call_0037 ++ call_0039
  let call_0041 := vf0_2
  let call_0042 := SALT.Intrinsics.Neon.vmovn_u32 (call_0041)
  let call_0043 := vf1_2
  let call_0044 := SALT.Intrinsics.Neon.vmovn_u32 (call_0043)
  let vmanth0_0 := call_0042 ++ call_0044
  let call_0046 := vx0_0
  let call_0047 := SALT.Intrinsics.Neon.vshrn_n_u32 (call_0046) (16)
  let call_0048 := vx1_0
  let call_0049 := SALT.Intrinsics.Neon.vshrn_n_u32 (call_0048) (16)
  let vsignh0_0 := call_0047 ++ call_0049
  let vexph0_1 := SALT.Intrinsics.Neon.vand_u16 (vexph0_0) (vexph_mask_0)
  let vmanth0_1 := SALT.Intrinsics.Neon.vand_u16 (vmanth0_0) (vmanth_mask_0)
  let vsignh0_1 := SALT.Intrinsics.Neon.vand_u16 (vsignh0_0) (vsignh_mask_0)
  let vh0_0 := SALT.Intrinsics.Neon.vadd_u16 (vmanth0_1) (vexph0_1)
  let vh0_1 := SALT.Intrinsics.Neon.vbsl_u16 (vnanmaskh0_0) (vnanh_0) (vh0_0)
  let vh0_2 := SALT.Intrinsics.Neon.vorr_u16 (vh0_1) (vsignh0_1)
  (vh0_2)

/-- Generated 4-lane secondary block from the extracted call graph. -/
def neonBlock4FromIntrinsics (p : f32f16vcvtParams)
    (loaded : List (BitVec 32)) : List (BitVec 16) :=
  let vexp_bias_0 := List.replicate 4 (125829120)
  let vscale_to_inf_0 := List.replicate 4 (2004877312)
  let vexpw_max_0 := List.replicate 4 (2139095040)
  let vscale_to_zero_0 := List.replicate 4 (142606336)
  let vbias_min_0 := List.replicate 4 (1073741824)
  let vexph_mask_0 := List.replicate 8 (31744)
  let vmanth_mask_0 := List.replicate 8 (4095)
  let vsignh_mask_0 := List.replicate 8 (32768)
  let vnanh_0 := List.replicate 8 (32256)
  let vx_0 := (loaded).take 4
  let vabsx_0 := SALT.Intrinsics.Neon.vabsq_f32 (vx_0)
  let call_0060 := vabsx_0
  let vbias_0 := SALT.Intrinsics.Neon.vadd_u32 (call_0060) (vexp_bias_0)
  let vf_0 := SALT.Intrinsics.Neon.vmulq_f32 (vabsx_0) (vscale_to_inf_0)
  let call_0063 := vabsx_0
  let vnanmaskw_0 := SALT.Intrinsics.Neon.vcgt_u32 (call_0063) (vexpw_max_0)
  let vbias_1 := SALT.Intrinsics.Neon.vand_u32 (vbias_0) (vexpw_max_0)
  let vf_1 := SALT.Intrinsics.Neon.vmulq_f32 (vf_0) (vscale_to_zero_0)
  let vnanmaskh_0 := SALT.Intrinsics.Neon.vmovn_u32 (vnanmaskw_0)
  let vbias_2 := SALT.Intrinsics.Neon.vmax_u32 (vbias_1) (vbias_min_0)
  let call_0069 := vbias_2
  let vf_2 := SALT.Intrinsics.Neon.vaddq_f32 (vf_1) (call_0069)
  let call_0071 := vf_2
  let vexph_0 := SALT.Intrinsics.Neon.vshrn_n_u32 (call_0071) (13)
  let call_0073 := vf_2
  let vmanth_0 := SALT.Intrinsics.Neon.vmovn_u32 (call_0073)
  let call_0075 := vx_0
  let vsignh_0 := SALT.Intrinsics.Neon.vshrn_n_u32 (call_0075) (16)
  let call_0077 := (vexph_mask_0).take 4
  let vexph_1 := SALT.Intrinsics.Neon.vand_u16 (vexph_0) (call_0077)
  let call_0079 := (vmanth_mask_0).take 4
  let vmanth_1 := SALT.Intrinsics.Neon.vand_u16 (vmanth_0) (call_0079)
  let call_0081 := (vsignh_mask_0).take 4
  let vsignh_1 := SALT.Intrinsics.Neon.vand_u16 (vsignh_0) (call_0081)
  let vh_0 := SALT.Intrinsics.Neon.vadd_u16 (vmanth_1) (vexph_1)
  let call_0084 := (vnanh_0).take 4
  let vh_1 := SALT.Intrinsics.Neon.vbsl_u16 (vnanmaskh_0) (call_0084) (vh_0)
  let vh_2 := SALT.Intrinsics.Neon.vorr_u16 (vh_1) (vsignh_1)
  vh_2

/-- Generated little-endian live-prefix abstraction of the 2/1 stores. -/
def neonPartialTailLivePrefixFromIntrinsics (p : f32f16vcvtParams)
    (loaded : List (BitVec 32)) (live : Nat) : List (BitVec 16) :=
  let vexp_bias_0 := List.replicate 4 (125829120)
  let vscale_to_inf_0 := List.replicate 4 (2004877312)
  let vexpw_max_0 := List.replicate 4 (2139095040)
  let vscale_to_zero_0 := List.replicate 4 (142606336)
  let vbias_min_0 := List.replicate 4 (1073741824)
  let vexph_mask_0 := List.replicate 8 (31744)
  let vmanth_mask_0 := List.replicate 8 (4095)
  let vsignh_mask_0 := List.replicate 8 (32768)
  let vnanh_0 := List.replicate 8 (32256)
  let vx_1 := (loaded).take 4
  let vabsx_1 := SALT.Intrinsics.Neon.vabsq_f32 (vx_1)
  let call_0090 := vabsx_1
  let vbias_3 := SALT.Intrinsics.Neon.vadd_u32 (call_0090) (vexp_bias_0)
  let vf_3 := SALT.Intrinsics.Neon.vmulq_f32 (vabsx_1) (vscale_to_inf_0)
  let call_0093 := vabsx_1
  let vnanmaskw_1 := SALT.Intrinsics.Neon.vcgt_u32 (call_0093) (vexpw_max_0)
  let vbias_4 := SALT.Intrinsics.Neon.vand_u32 (vbias_3) (vexpw_max_0)
  let vf_4 := SALT.Intrinsics.Neon.vmulq_f32 (vf_3) (vscale_to_zero_0)
  let vnanmaskh_1 := SALT.Intrinsics.Neon.vmovn_u32 (vnanmaskw_1)
  let vbias_5 := SALT.Intrinsics.Neon.vmax_u32 (vbias_4) (vbias_min_0)
  let call_0099 := vbias_5
  let vf_5 := SALT.Intrinsics.Neon.vaddq_f32 (vf_4) (call_0099)
  let call_0101 := vf_5
  let vexph_2 := SALT.Intrinsics.Neon.vshrn_n_u32 (call_0101) (13)
  let call_0103 := vf_5
  let vmanth_2 := SALT.Intrinsics.Neon.vmovn_u32 (call_0103)
  let call_0105 := vx_1
  let vsignh_2 := SALT.Intrinsics.Neon.vshrn_n_u32 (call_0105) (16)
  let call_0107 := (vexph_mask_0).take 4
  let vexph_3 := SALT.Intrinsics.Neon.vand_u16 (vexph_2) (call_0107)
  let call_0109 := (vmanth_mask_0).take 4
  let vmanth_3 := SALT.Intrinsics.Neon.vand_u16 (vmanth_2) (call_0109)
  let call_0111 := (vsignh_mask_0).take 4
  let vsignh_3 := SALT.Intrinsics.Neon.vand_u16 (vsignh_2) (call_0111)
  let vh_3 := SALT.Intrinsics.Neon.vadd_u16 (vmanth_3) (vexph_3)
  let call_0114 := (vnanh_0).take 4
  let vh_4 := SALT.Intrinsics.Neon.vbsl_u16 (vnanmaskh_1) (call_0114) (vh_3)
  let vh_5 := SALT.Intrinsics.Neon.vorr_u16 (vh_4) (vsignh_3)
  let call_0117 := vh_5
  let stored2 := if live.testBit 1 then (call_0117).take 2 else []
  let vh_6 := ((vh_5 ++ vh_5).drop 2).take 4
  let after2 := if live.testBit 1 then vh_6 else vh_5
  let stored1 := if live.testBit 0 then (after2).take 1 else []
  (stored2) ++ (stored1)

/-- Generated value-only lifting of the validated 8/4/2/1 control shape.

The overread lists model physically loaded bytes beyond a nonempty short tail.
This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonValueLoopWithOverreadFromIntrinsics (p : f32f16vcvtParams)
    (input overread : List (BitVec 32)) : List (BitVec 16) :=
  SALT.Kernel.Schedule.runTwoPhaseTail 8 4 (by decide) (by decide)
    (neonBlock8FromIntrinsics p) (neonBlock4FromIntrinsics p)
    (fun tail =>
      let loaded := (tail ++ overread).take 4
      neonPartialTailLivePrefixFromIntrinsics p loaded tail.length)
    input

/-- Zero-filled compatibility specialization of the explicit-overread model. -/
def neonValueLoopFromIntrinsics (p : f32f16vcvtParams)
    (input : List (BitVec 32)) : List (BitVec 16) :=
  neonValueLoopWithOverreadFromIntrinsics p input
    (List.replicate 3 (0 : BitVec 32))

def rvvChunkFromIntrinsics (p : f32f16vcvtParams)
    (input : List (BitVec 32)) : List (BitVec 16) :=
  let vx_0 := input
  let vabsx_0 := SALT.Intrinsics.RVV.vfabs_v_f32 (vx_0)
  let vabsx_u_0 := vabsx_0
  let vbias_0 := SALT.Intrinsics.RVV.vadd_vx_u32 (vabsx_u_0) (125829120)
  let vf_0 := SALT.Intrinsics.RVV.vfmul_vf_f32 (vabsx_0) (2004877312)
  let vnanmask_0 := SALT.Intrinsics.RVV.vmsgtu_vx_u32 (vabsx_u_0) (2139095040)
  let vbias_1 := SALT.Intrinsics.RVV.vand_vx_u32 (vbias_0) (2139095040)
  let vf_1 := SALT.Intrinsics.RVV.vfmul_vf_f32 (vf_0) (142606336)
  let vbias_2 := SALT.Intrinsics.RVV.vmaxu_vx_u32 (vbias_1) (1073741824)
  let call_0010 := vbias_2
  let vf_2 := SALT.Intrinsics.RVV.vfadd_vv_f32 (vf_1) (call_0010)
  let vf_u_0 := vf_2
  let vx_u_0 := vx_0
  let vexph_0 := SALT.Intrinsics.RVV.vnsrl_wx_u16 (vf_u_0) (13)
  let vmanth_0 := SALT.Intrinsics.RVV.vnsrl_wx_u16 (vf_u_0) (0)
  let vsignh_0 := SALT.Intrinsics.RVV.vnsrl_wx_u16 (vx_u_0) (16)
  let vexph_1 := SALT.Intrinsics.RVV.vand_vx_u16 (vexph_0) (31744)
  let vmanth_1 := SALT.Intrinsics.RVV.vand_vx_u16 (vmanth_0) (4095)
  let vsignh_1 := SALT.Intrinsics.RVV.vand_vx_u16 (vsignh_0) (32768)
  let vh_0 := SALT.Intrinsics.RVV.vadd_vv_u16 (vmanth_1) (vexph_1)
  let vh_1 := SALT.Intrinsics.RVV.vmerge_vxm_u16 (vh_0) (32256) (vnanmask_0)
  let vh_2 := SALT.Intrinsics.RVV.vor_vv_u16 (vh_1) (vsignh_1)
  vh_2


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : f32f16vcvtParams) (x : BitVec 32) : BitVec 16 :=
  (neonBlock8FromIntrinsics p (List.replicate 8 x)).headD (0 : BitVec 16)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : f32f16vcvtParams) (x : BitVec 32) : BitVec 16 :=
  (rvvChunkFromIntrinsics p [x]).headD (0 : BitVec 16)

/-- Scalar action projected from the parsed secondary Neon block. -/
def fNeonSecondary (p : f32f16vcvtParams)
    (input : BitVec 32) : BitVec 16 :=
  (neonBlock4FromIntrinsics p [input]).headD (0 : BitVec 16)

/-- Generated RVV positive-partition assembly. -/
def rvvValueLoopFromIntrinsics (p : f32f16vcvtParams)
    (input : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length) :
    List (BitVec 16) :=
  SALT.Kernel.Schedule.processBlocks (rvvChunkFromIntrinsics p) input schedule
end SALT.Corpus.f32f16vcvt
