-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.qs8vmulminmaxfp32

def programManifestSha256 : String := "9795d1f1f3da784b86514eccd7aadf924744d3d5fd6f06161bb2547f01e6dbaa"
def consumedEffectsSha256 : String := "521299ca9cbaf4be0d415ed0564761a14236409fb6fe74b2c4894ecb3ef2ac3c"

def neonSourceSha256 : String :=
  "cb4168849636fc68af462e57bcf80141316833b34dca0c7861f1b6dfa26cb390"
def rvvSourceSha256 : String :=
  "2d018286037d2bc6539c361907a8d8acc965d5d659b9eed327ca72cb6c4f9528"
def neonPreprocessedSha256 : String :=
  "1205d1e1cd47096ae41382f6952c3ca7a5d437a23e1a1d8eae52d52afb774a9c"
def rvvPreprocessedSha256 : String :=
  "0ff2e24e5bb6ca49d6cf4d2f472d10f8d34809b836fdca55cd8e7711790bcf2d"
def parseFacadeSha256 : String :=
  "829b8b0358b2a31d50a784422681ac9e821a4369619812194f800dc63287c4bc"
def registrySha256 : String :=
  "b5abbb46d20b8663846d820a60a8c868b108677ffef5da91538b2a5a6e6824b3"

structure qs8vmulminmaxfp32Params where
  a_zero_point : BitVec 8
  b_zero_point : BitVec 8
  output_max : BitVec 8
  output_min : BitVec 8
  output_zero_point : BitVec 16
  scale : BitVec 32
  deriving Repr, DecidableEq

def neonBlock8FromIntrinsics (p : qs8vmulminmaxfp32Params)
    (input_a : List (BitVec 8))
    (input_b : List (BitVec 8)) : List (BitVec 8) :=
  let va_zero_point_0 := List.replicate 8 ((p.a_zero_point).truncate 8)
  let vb_zero_point_0 := List.replicate 8 ((p.b_zero_point).truncate 8)
  let vscale_0 := List.replicate 4 ((p.scale).truncate 32)
  let vmagic_bias_0 := List.replicate 4 (1262485504)
  let vmagic_bias_less_output_zero_point_0 := List.replicate 4 ((BitVec.ofNat 32 1262485504) - ((p.output_zero_point).signExtend 32))
  let voutput_min_0 := List.replicate 8 ((p.output_min).truncate 8)
  let voutput_max_0 := List.replicate 8 ((p.output_max).truncate 8)
  let va01234567_0 := (input_a).take 8
  let vb01234567_0 := (input_b).take 8
  let vxa01234567_0 := SALT.Intrinsics.Neon.vsubl_s8 (va01234567_0) (va_zero_point_0)
  let vxb01234567_0 := SALT.Intrinsics.Neon.vsubl_s8 (vb01234567_0) (vb_zero_point_0)
  let call_0011 := (vxa01234567_0).take 4
  let call_0012 := (vxb01234567_0).take 4
  let vacc0123_0 := SALT.Intrinsics.Neon.vmull_s16 (call_0011) (call_0012)
  let call_0014 := (vxa01234567_0).drop 4
  let call_0015 := (vxb01234567_0).drop 4
  let vacc4567_0 := SALT.Intrinsics.Neon.vmull_s16 (call_0014) (call_0015)
  let vfpacc0123_0 := SALT.Intrinsics.Neon.vcvtq_f32_s32 (vacc0123_0)
  let vfpacc4567_0 := SALT.Intrinsics.Neon.vcvtq_f32_s32 (vacc4567_0)
  let vfpacc0123_1 := SALT.Intrinsics.Neon.vmulq_f32 (vfpacc0123_0) (vscale_0)
  let vfpacc4567_1 := SALT.Intrinsics.Neon.vmulq_f32 (vfpacc4567_0) (vscale_0)
  let call_0021 := SALT.Intrinsics.Neon.vaddq_f32 (vfpacc0123_1) (vmagic_bias_0)
  let vacc0123_1 := call_0021
  let call_0023 := SALT.Intrinsics.Neon.vaddq_f32 (vfpacc4567_1) (vmagic_bias_0)
  let vacc4567_1 := call_0023
  let vacc0123_2 := SALT.Intrinsics.Neon.vqsubq_s32 (vacc0123_1) (vmagic_bias_less_output_zero_point_0)
  let vacc4567_2 := SALT.Intrinsics.Neon.vqsubq_s32 (vacc4567_1) (vmagic_bias_less_output_zero_point_0)
  let call_0027 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc0123_2)
  let vacc01234567_0 := SALT.Intrinsics.Neon.vqmovn_high_s32 (call_0027) (vacc4567_2)
  let vout01234567_0 := SALT.Intrinsics.Neon.vqmovn_s16 (vacc01234567_0)
  let vout01234567_1 := SALT.Intrinsics.Neon.vmax_s8_vec (vout01234567_0) (voutput_min_0)
  let vout01234567_2 := SALT.Intrinsics.Neon.vmin_s8_vec (vout01234567_1) (voutput_max_0)
  (vout01234567_2)

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : qs8vmulminmaxfp32Params)
    (loadedA loadedB : List (BitVec 8)) (live : Nat) : List (BitVec 8) :=
  let va_zero_point_0 := List.replicate 8 ((p.a_zero_point).truncate 8)
  let vb_zero_point_0 := List.replicate 8 ((p.b_zero_point).truncate 8)
  let vscale_0 := List.replicate 4 ((p.scale).truncate 32)
  let vmagic_bias_0 := List.replicate 4 (1262485504)
  let vmagic_bias_less_output_zero_point_0 := List.replicate 4 ((BitVec.ofNat 32 1262485504) - ((p.output_zero_point).signExtend 32))
  let voutput_min_0 := List.replicate 8 ((p.output_min).truncate 8)
  let voutput_max_0 := List.replicate 8 ((p.output_max).truncate 8)
  let va01234567_1 := (loadedA).take 8
  let vb01234567_1 := (loadedB).take 8
  let vxa01234567_1 := SALT.Intrinsics.Neon.vsubl_s8 (va01234567_1) (va_zero_point_0)
  let vxb01234567_1 := SALT.Intrinsics.Neon.vsubl_s8 (vb01234567_1) (vb_zero_point_0)
  let call_0037 := (vxa01234567_1).take 4
  let call_0038 := (vxb01234567_1).take 4
  let vacc0123_3 := SALT.Intrinsics.Neon.vmull_s16 (call_0037) (call_0038)
  let call_0040 := (vxa01234567_1).drop 4
  let call_0041 := (vxb01234567_1).drop 4
  let vacc4567_3 := SALT.Intrinsics.Neon.vmull_s16 (call_0040) (call_0041)
  let vfpacc0123_2 := SALT.Intrinsics.Neon.vcvtq_f32_s32 (vacc0123_3)
  let vfpacc4567_2 := SALT.Intrinsics.Neon.vcvtq_f32_s32 (vacc4567_3)
  let vfpacc0123_3 := SALT.Intrinsics.Neon.vmulq_f32 (vfpacc0123_2) (vscale_0)
  let vfpacc4567_3 := SALT.Intrinsics.Neon.vmulq_f32 (vfpacc4567_2) (vscale_0)
  let call_0047 := SALT.Intrinsics.Neon.vaddq_f32 (vfpacc0123_3) (vmagic_bias_0)
  let vacc0123_4 := call_0047
  let call_0049 := SALT.Intrinsics.Neon.vaddq_f32 (vfpacc4567_3) (vmagic_bias_0)
  let vacc4567_4 := call_0049
  let vacc0123_5 := SALT.Intrinsics.Neon.vqsubq_s32 (vacc0123_4) (vmagic_bias_less_output_zero_point_0)
  let vacc4567_5 := SALT.Intrinsics.Neon.vqsubq_s32 (vacc4567_4) (vmagic_bias_less_output_zero_point_0)
  let call_0053 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc0123_5)
  let vacc01234567_1 := SALT.Intrinsics.Neon.vqmovn_high_s32 (call_0053) (vacc4567_5)
  let vout01234567_3 := SALT.Intrinsics.Neon.vqmovn_s16 (vacc01234567_1)
  let vout01234567_4 := SALT.Intrinsics.Neon.vmax_s8_vec (vout01234567_3) (voutput_min_0)
  let vout01234567_5 := SALT.Intrinsics.Neon.vmin_s8_vec (vout01234567_4) (voutput_max_0)
  let call_0058 := vout01234567_5
  let stored4 := if live.testBit 2 then (call_0058).take 4 else []
  let vout01234567_6 := ((vout01234567_5 ++ vout01234567_5).drop 4).take 8
  let after4 := if live.testBit 2 then vout01234567_6 else vout01234567_5
  let call_0061 := after4
  let stored2 := if live.testBit 1 then (call_0061).take 2 else []
  let vout01234567_7 := ((after4 ++ after4).drop 2).take 8
  let after2 := if live.testBit 1 then vout01234567_7 else after4
  let stored1 := if live.testBit 0 then (after2).take 1 else []
  (stored4) ++ (stored2) ++ (stored1)

/-- Generated value-only lifting of the validated 8/4/2/1 control shape.

`overreadA` and `overreadB` supply the bytes physically loaded beyond a nonempty short tail.
This definition does not establish that those bytes are legally readable.
-/
def neonValueLoopWithOverreadFromIntrinsics (p : qs8vmulminmaxfp32Params)
    (input_a input_b overreadA overreadB : List (BitVec 8))
    (sameLength : input_a.length = input_b.length) : List (BitVec 8) :=
  SALT.Kernel.Schedule.runFixedChunkTail2 8 (by decide)
    (neonBlock8FromIntrinsics p)
    (fun tailA tailB =>
      let loadedA := (tailA ++ overreadA).take 8
      let loadedB := (tailB ++ overreadB).take 8
      neonPartialTailLivePrefixFromIntrinsics p loadedA loadedB tailA.length)
    input_a input_b sameLength

/-- Zero-filled compatibility specialization of the explicit-overread model. -/
def neonValueLoopFromIntrinsics (p : qs8vmulminmaxfp32Params)
    (input_a input_b : List (BitVec 8))
    (sameLength : input_a.length = input_b.length) : List (BitVec 8) :=
  neonValueLoopWithOverreadFromIntrinsics p input_a input_b
    (List.replicate 7 (0 : BitVec 8))
    (List.replicate 7 (0 : BitVec 8)) sameLength

def rvvChunkFromIntrinsics (p : qs8vmulminmaxfp32Params)
    (input_a : List (BitVec 8))
    (input_b : List (BitVec 8)) : List (BitVec 8) :=
  let va_0 := input_a
  let vb_0 := input_b
  let call_0003 := SALT.Intrinsics.RVV.vsext_vf2_i16 (va_0)
  let vxa_0 := SALT.Intrinsics.RVV.vsub_vx_i16 (call_0003) (((p.a_zero_point).truncate 8).signExtend 16)
  let call_0005 := SALT.Intrinsics.RVV.vsext_vf2_i16 (vb_0)
  let vxb_0 := SALT.Intrinsics.RVV.vsub_vx_i16 (call_0005) (((p.b_zero_point).truncate 8).signExtend 16)
  let vacc_0 := SALT.Intrinsics.RVV.vwmul_vv_i32 (vxa_0) (vxb_0)
  let vfpacc_0 := SALT.Intrinsics.RVV.vfcvt_f_x_v_f32 (vacc_0)
  let vfpacc_1 := SALT.Intrinsics.RVV.vfmul_vf_f32 (vfpacc_0) ((p.scale).truncate 32)
  let vacc_1 := SALT.Intrinsics.RVV.vfcvt_x_f_v_i32_rne (vfpacc_1)
  let vacc_2 := SALT.Intrinsics.RVV.vadd_vx_i32 (vacc_1) (((p.output_zero_point).truncate 16).signExtend 32)
  let vout16_0 := SALT.Intrinsics.RVV.vnclip_wx_i16_mode (vacc_2) (0) (2)
  let vout_0 := SALT.Intrinsics.RVV.vnclip_wx_i8_mode (vout16_0) (0) (2)
  let vout_1 := SALT.Intrinsics.RVV.vmax_vx (vout_0) ((p.output_min).truncate 8)
  let vout_2 := SALT.Intrinsics.RVV.vmin_vx (vout_1) ((p.output_max).truncate 8)
  vout_2

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : qs8vmulminmaxfp32Params)
    (input_a input_b : List (BitVec 8))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length) :
    List (BitVec 8) :=
  SALT.Kernel.Schedule.processBlocks2 (rvvChunkFromIntrinsics p) input_a input_b sameLength schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : qs8vmulminmaxfp32Params) (x y : BitVec 8) : BitVec 8 :=
  (neonBlock8FromIntrinsics p (List.replicate 8 x) (List.replicate 8 y)).headD (0 : BitVec 8)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : qs8vmulminmaxfp32Params) (x y : BitVec 8) : BitVec 8 :=
  (rvvChunkFromIntrinsics p [x] [y]).headD (0 : BitVec 8)
end SALT.Corpus.qs8vmulminmaxfp32
