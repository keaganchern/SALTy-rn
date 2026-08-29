-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.qs8vaddminmax

def programManifestSha256 : String := "fb412a59d31e61f85cdefb9a846f63890fda528cd1a704aeb387eab1634dcf14"
def consumedEffectsSha256 : String := "246f0407d26a191a07bb34fc95b5bb5a437caf56a824a2de598ac71bbfc7c52b"

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
def registrySha256 : String :=
  "4b3993c44588cc88066260d7e1a681008ebaef3e148e407e961c16285052b0cc"

structure qs8vaddminmaxParams where
  a_multiplier : BitVec 32
  a_zero_point : BitVec 8
  b_multiplier : BitVec 32
  b_zero_point : BitVec 8
  output_max : BitVec 8
  output_min : BitVec 8
  output_zero_point : BitVec 16
  shift : BitVec 64
  deriving Repr, DecidableEq

def neonBlock16FromIntrinsics (p : qs8vaddminmaxParams)
    (input_a : List (BitVec 8))
    (input_b : List (BitVec 8)) : List (BitVec 8) :=
  let va_zero_point_0 := List.replicate 8 ((p.a_zero_point).truncate 8)
  let vb_zero_point_0 := List.replicate 8 ((p.b_zero_point).truncate 8)
  let va_multiplier_0 := List.replicate 4 ((p.a_multiplier).truncate 32)
  let vb_multiplier_0 := List.replicate 4 ((p.b_multiplier).truncate 32)
  let vright_shift_0 := List.replicate 4 (-(p.shift).truncate 32)
  let voutput_zero_point_0 := List.replicate 8 ((p.output_zero_point).truncate 16)
  let voutput_min_0 := List.replicate 16 ((p.output_min).truncate 8)
  let voutput_max_0 := List.replicate 16 ((p.output_max).truncate 8)
  let va01234567_0 := (input_a).take 8
  let vb01234567_0 := (input_b).take 8
  let va89ABCDEF_0 := ((input_a).drop 8).take 8
  let vb89ABCDEF_0 := ((input_b).drop 8).take 8
  let vxa01234567_0 := SALT.Intrinsics.Neon.vsubl_s8 (va01234567_0) (va_zero_point_0)
  let vxb01234567_0 := SALT.Intrinsics.Neon.vsubl_s8 (vb01234567_0) (vb_zero_point_0)
  let vxa89ABCDEF_0 := SALT.Intrinsics.Neon.vsubl_s8 (va89ABCDEF_0) (va_zero_point_0)
  let vxb89ABCDEF_0 := SALT.Intrinsics.Neon.vsubl_s8 (vb89ABCDEF_0) (vb_zero_point_0)
  let call_0016 := (vxa01234567_0).take 4
  let call_0017 := SALT.Intrinsics.Neon.vmovl_s16 (call_0016)
  let vacc0123_0 := SALT.Intrinsics.Neon.vmulq_s32 (call_0017) ((p.a_multiplier).truncate 32)
  let call_0019 := (vxa01234567_0).drop 4
  let call_0020 := SALT.Intrinsics.Neon.vmovl_s16 (call_0019)
  let vacc4567_0 := SALT.Intrinsics.Neon.vmulq_s32 (call_0020) ((p.a_multiplier).truncate 32)
  let call_0022 := (vxa89ABCDEF_0).take 4
  let call_0023 := SALT.Intrinsics.Neon.vmovl_s16 (call_0022)
  let vacc89AB_0 := SALT.Intrinsics.Neon.vmulq_s32 (call_0023) ((p.a_multiplier).truncate 32)
  let call_0025 := (vxa89ABCDEF_0).drop 4
  let call_0026 := SALT.Intrinsics.Neon.vmovl_s16 (call_0025)
  let vaccCDEF_0 := SALT.Intrinsics.Neon.vmulq_s32 (call_0026) ((p.a_multiplier).truncate 32)
  let call_0028 := (vxb01234567_0).take 4
  let call_0029 := SALT.Intrinsics.Neon.vmovl_s16 (call_0028)
  let vacc0123_1 := SALT.Intrinsics.Neon.vmlaq_s32 (vacc0123_0) (call_0029) ((p.b_multiplier).truncate 32)
  let call_0031 := (vxb01234567_0).drop 4
  let call_0032 := SALT.Intrinsics.Neon.vmovl_s16 (call_0031)
  let vacc4567_1 := SALT.Intrinsics.Neon.vmlaq_s32 (vacc4567_0) (call_0032) ((p.b_multiplier).truncate 32)
  let call_0034 := (vxb89ABCDEF_0).take 4
  let call_0035 := SALT.Intrinsics.Neon.vmovl_s16 (call_0034)
  let vacc89AB_1 := SALT.Intrinsics.Neon.vmlaq_s32 (vacc89AB_0) (call_0035) ((p.b_multiplier).truncate 32)
  let call_0037 := (vxb89ABCDEF_0).drop 4
  let call_0038 := SALT.Intrinsics.Neon.vmovl_s16 (call_0037)
  let vaccCDEF_1 := SALT.Intrinsics.Neon.vmlaq_s32 (vaccCDEF_0) (call_0038) ((p.b_multiplier).truncate 32)
  let vacc0123_2 := SALT.Intrinsics.Neon.vrshlq_s32_vec (vacc0123_1) (vright_shift_0)
  let vacc4567_2 := SALT.Intrinsics.Neon.vrshlq_s32_vec (vacc4567_1) (vright_shift_0)
  let vacc89AB_2 := SALT.Intrinsics.Neon.vrshlq_s32_vec (vacc89AB_1) (vright_shift_0)
  let vaccCDEF_2 := SALT.Intrinsics.Neon.vrshlq_s32_vec (vaccCDEF_1) (vright_shift_0)
  let call_0044 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc0123_2)
  let call_0045 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc4567_2)
  let call_0046 := call_0044 ++ call_0045
  let vacc01234567_0 := SALT.Intrinsics.Neon.vqaddq_s16 (call_0046) ((p.output_zero_point).truncate 16)
  let call_0048 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc89AB_2)
  let call_0049 := SALT.Intrinsics.Neon.vqmovn_s32 (vaccCDEF_2)
  let call_0050 := call_0048 ++ call_0049
  let vacc89ABCDEF_0 := SALT.Intrinsics.Neon.vqaddq_s16 (call_0050) ((p.output_zero_point).truncate 16)
  let call_0052 := SALT.Intrinsics.Neon.vqmovn_s16 (vacc01234567_0)
  let call_0053 := SALT.Intrinsics.Neon.vqmovn_s16 (vacc89ABCDEF_0)
  let vout0123456789ABCDEF_0 := call_0052 ++ call_0053
  let vout0123456789ABCDEF_1 := SALT.Intrinsics.Neon.vmaxq_s8 (vout0123456789ABCDEF_0) (voutput_min_0)
  let vout0123456789ABCDEF_2 := SALT.Intrinsics.Neon.vminq_s8 (vout0123456789ABCDEF_1) (voutput_max_0)
  (vout0123456789ABCDEF_2)

/-- Generated 8-lane secondary block from the extracted call graph. -/
def neonBlock8FromIntrinsics (p : qs8vaddminmaxParams)
    (loadedA loadedB : List (BitVec 8)) : List (BitVec 8) :=
  let va_zero_point_0 := List.replicate 8 ((p.a_zero_point).truncate 8)
  let vb_zero_point_0 := List.replicate 8 ((p.b_zero_point).truncate 8)
  let va_multiplier_0 := List.replicate 4 ((p.a_multiplier).truncate 32)
  let vb_multiplier_0 := List.replicate 4 ((p.b_multiplier).truncate 32)
  let vright_shift_0 := List.replicate 4 (-(p.shift).truncate 32)
  let voutput_zero_point_0 := List.replicate 8 ((p.output_zero_point).truncate 16)
  let voutput_min_0 := List.replicate 16 ((p.output_min).truncate 8)
  let voutput_max_0 := List.replicate 16 ((p.output_max).truncate 8)
  let va01234567_1 := (loadedA).take 8
  let vb01234567_1 := (loadedB).take 8
  let vxa01234567_1 := SALT.Intrinsics.Neon.vsubl_s8 (va01234567_1) (va_zero_point_0)
  let vxb01234567_1 := SALT.Intrinsics.Neon.vsubl_s8 (vb01234567_1) (vb_zero_point_0)
  let call_0062 := (vxa01234567_1).take 4
  let call_0063 := SALT.Intrinsics.Neon.vmovl_s16 (call_0062)
  let vacc0123_3 := SALT.Intrinsics.Neon.vmulq_s32 (call_0063) ((p.a_multiplier).truncate 32)
  let call_0065 := (vxa01234567_1).drop 4
  let call_0066 := SALT.Intrinsics.Neon.vmovl_s16 (call_0065)
  let vacc4567_3 := SALT.Intrinsics.Neon.vmulq_s32 (call_0066) ((p.a_multiplier).truncate 32)
  let call_0068 := (vxb01234567_1).take 4
  let call_0069 := SALT.Intrinsics.Neon.vmovl_s16 (call_0068)
  let vacc0123_4 := SALT.Intrinsics.Neon.vmlaq_s32 (vacc0123_3) (call_0069) ((p.b_multiplier).truncate 32)
  let call_0071 := (vxb01234567_1).drop 4
  let call_0072 := SALT.Intrinsics.Neon.vmovl_s16 (call_0071)
  let vacc4567_4 := SALT.Intrinsics.Neon.vmlaq_s32 (vacc4567_3) (call_0072) ((p.b_multiplier).truncate 32)
  let vacc0123_5 := SALT.Intrinsics.Neon.vrshlq_s32_vec (vacc0123_4) (vright_shift_0)
  let vacc4567_5 := SALT.Intrinsics.Neon.vrshlq_s32_vec (vacc4567_4) (vright_shift_0)
  let call_0076 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc0123_5)
  let call_0077 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc4567_5)
  let call_0078 := call_0076 ++ call_0077
  let vacc01234567_1 := SALT.Intrinsics.Neon.vqaddq_s16 (call_0078) ((p.output_zero_point).truncate 16)
  let vout01234567_0 := SALT.Intrinsics.Neon.vqmovn_s16 (vacc01234567_1)
  let call_0081 := (voutput_min_0).take 8
  let vout01234567_1 := SALT.Intrinsics.Neon.vmax_s8_vec (vout01234567_0) (call_0081)
  let call_0083 := (voutput_max_0).take 8
  let vout01234567_2 := SALT.Intrinsics.Neon.vmin_s8_vec (vout01234567_1) (call_0083)
  vout01234567_2

/-- Generated little-endian live-prefix abstraction of the 4/2/1 stores. -/
def neonPartialTailLivePrefixFromIntrinsics (p : qs8vaddminmaxParams)
    (loadedA loadedB : List (BitVec 8)) (live : Nat) : List (BitVec 8) :=
  let va_zero_point_0 := List.replicate 8 ((p.a_zero_point).truncate 8)
  let vb_zero_point_0 := List.replicate 8 ((p.b_zero_point).truncate 8)
  let va_multiplier_0 := List.replicate 4 ((p.a_multiplier).truncate 32)
  let vb_multiplier_0 := List.replicate 4 ((p.b_multiplier).truncate 32)
  let vright_shift_0 := List.replicate 4 (-(p.shift).truncate 32)
  let voutput_zero_point_0 := List.replicate 8 ((p.output_zero_point).truncate 16)
  let voutput_min_0 := List.replicate 16 ((p.output_min).truncate 8)
  let voutput_max_0 := List.replicate 16 ((p.output_max).truncate 8)
  let va01234567_1 := (loadedA).take 8
  let vb01234567_1 := (loadedB).take 8
  let vxa01234567_1 := SALT.Intrinsics.Neon.vsubl_s8 (va01234567_1) (va_zero_point_0)
  let vxb01234567_1 := SALT.Intrinsics.Neon.vsubl_s8 (vb01234567_1) (vb_zero_point_0)
  let call_0062 := (vxa01234567_1).take 4
  let call_0063 := SALT.Intrinsics.Neon.vmovl_s16 (call_0062)
  let vacc0123_3 := SALT.Intrinsics.Neon.vmulq_s32 (call_0063) ((p.a_multiplier).truncate 32)
  let call_0065 := (vxa01234567_1).drop 4
  let call_0066 := SALT.Intrinsics.Neon.vmovl_s16 (call_0065)
  let vacc4567_3 := SALT.Intrinsics.Neon.vmulq_s32 (call_0066) ((p.a_multiplier).truncate 32)
  let call_0068 := (vxb01234567_1).take 4
  let call_0069 := SALT.Intrinsics.Neon.vmovl_s16 (call_0068)
  let vacc0123_4 := SALT.Intrinsics.Neon.vmlaq_s32 (vacc0123_3) (call_0069) ((p.b_multiplier).truncate 32)
  let call_0071 := (vxb01234567_1).drop 4
  let call_0072 := SALT.Intrinsics.Neon.vmovl_s16 (call_0071)
  let vacc4567_4 := SALT.Intrinsics.Neon.vmlaq_s32 (vacc4567_3) (call_0072) ((p.b_multiplier).truncate 32)
  let vacc0123_5 := SALT.Intrinsics.Neon.vrshlq_s32_vec (vacc0123_4) (vright_shift_0)
  let vacc4567_5 := SALT.Intrinsics.Neon.vrshlq_s32_vec (vacc4567_4) (vright_shift_0)
  let call_0076 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc0123_5)
  let call_0077 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc4567_5)
  let call_0078 := call_0076 ++ call_0077
  let vacc01234567_1 := SALT.Intrinsics.Neon.vqaddq_s16 (call_0078) ((p.output_zero_point).truncate 16)
  let vout01234567_0 := SALT.Intrinsics.Neon.vqmovn_s16 (vacc01234567_1)
  let call_0081 := (voutput_min_0).take 8
  let vout01234567_1 := SALT.Intrinsics.Neon.vmax_s8_vec (vout01234567_0) (call_0081)
  let call_0083 := (voutput_max_0).take 8
  let vout01234567_2 := SALT.Intrinsics.Neon.vmin_s8_vec (vout01234567_1) (call_0083)
  let call_0086 := vout01234567_2
  let stored4 := if live.testBit 2 then (call_0086).take 4 else []
  let vout01234567_3 := ((vout01234567_2 ++ vout01234567_2).drop 4).take 8
  let after4 := if live.testBit 2 then vout01234567_3 else vout01234567_2
  let call_0089 := after4
  let stored2 := if live.testBit 1 then (call_0089).take 2 else []
  let vout01234567_4 := ((after4 ++ after4).drop 2).take 8
  let after2 := if live.testBit 1 then vout01234567_4 else after4
  let stored1 := if live.testBit 0 then (after2).take 1 else []
  (stored4) ++ (stored2) ++ (stored1)

/-- Generated value-only lifting of the validated two-phase control shape. -/
def neonValueLoopWithOverreadFromIntrinsics (p : qs8vaddminmaxParams)
    (input_a input_b overreadA overreadB : List (BitVec 8))
    (sameLength : input_a.length = input_b.length) : List (BitVec 8) :=
  SALT.Kernel.Schedule.runTwoPhaseTail2 16 8 (by decide) (by decide)
    (neonBlock16FromIntrinsics p) (neonBlock8FromIntrinsics p)
    (fun tailA tailB =>
      let loadedA := (tailA ++ overreadA).take 8
      let loadedB := (tailB ++ overreadB).take 8
      neonPartialTailLivePrefixFromIntrinsics p loadedA loadedB tailA.length)
    input_a input_b sameLength

/-- Zero-filled compatibility specialization of the explicit-overread model. -/
def neonValueLoopFromIntrinsics (p : qs8vaddminmaxParams)
    (input_a input_b : List (BitVec 8))
    (sameLength : input_a.length = input_b.length) : List (BitVec 8) :=
  neonValueLoopWithOverreadFromIntrinsics p input_a input_b
    (List.replicate 7 (0 : BitVec 8))
    (List.replicate 7 (0 : BitVec 8)) sameLength

def rvvChunkFromIntrinsics (p : qs8vaddminmaxParams)
    (input_a : List (BitVec 8))
    (input_b : List (BitVec 8)) : List (BitVec 8) :=
  let va_0 := input_a
  let vb_0 := input_b
  let vxa_0 := SALT.Intrinsics.RVV.vwsub_vx (va_0) ((p.a_zero_point).truncate 8)
  let vxb_0 := SALT.Intrinsics.RVV.vwsub_vx (vb_0) ((p.b_zero_point).truncate 8)
  let vxa32_0 := SALT.Intrinsics.RVV.vsext_vf2 (vxa_0)
  let vxb32_0 := SALT.Intrinsics.RVV.vsext_vf2 (vxb_0)
  let vacc_0 := SALT.Intrinsics.RVV.vmul_vx (vxa32_0) ((p.a_multiplier).truncate 32)
  let vacc_1 := SALT.Intrinsics.RVV.vmacc_vx (vacc_0) ((p.b_multiplier).truncate 32) (vxb32_0)
  let vacc_2 := SALT.Intrinsics.RVV.vssra_vx_i32_mode (vacc_1) (((p.shift).signExtend 64).toNat) (0)
  let vacc16_0 := SALT.Intrinsics.RVV.vnclip_wx_i16_mode (vacc_2) (0) (2)
  let vacc16_1 := SALT.Intrinsics.RVV.vsadd_vx (vacc16_0) ((p.output_zero_point).truncate 16)
  let vout_0 := SALT.Intrinsics.RVV.vnclip_wx_i8_mode (vacc16_1) (0) (2)
  let vout_1 := SALT.Intrinsics.RVV.vmax_vx (vout_0) ((p.output_min).truncate 8)
  let vout_2 := SALT.Intrinsics.RVV.vmin_vx (vout_1) ((p.output_max).truncate 8)
  vout_2


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : qs8vaddminmaxParams) (x y : BitVec 8) : BitVec 8 :=
  (neonBlock16FromIntrinsics p (List.replicate 16 x) (List.replicate 16 y)).headD x

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : qs8vaddminmaxParams) (x y : BitVec 8) : BitVec 8 :=
  (rvvChunkFromIntrinsics p [x] [y]).headD x

/-- Generated RVV positive-partition assembly. -/
def rvvValueLoopFromIntrinsics (p : qs8vaddminmaxParams)
    (input_a input_b : List (BitVec 8))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length) :
    List (BitVec 8) :=
  SALT.Kernel.Schedule.processBlocks2 (rvvChunkFromIntrinsics p)
    input_a input_b sameLength schedule
end SALT.Corpus.qs8vaddminmax
