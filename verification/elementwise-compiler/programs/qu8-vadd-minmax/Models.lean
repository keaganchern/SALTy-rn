-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.qu8vaddminmax

def programManifestSha256 : String := "2c994efdaee21b1118801123275d69c05d71e3db3a890cd4c1999b7268c936cb"
def consumedEffectsSha256 : String := "76280bda1a4a1930a02761132ea4327cae7e05c9f5521044eb111d3af4032921"

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
  "bd66878aecb12c9755f9d1b77004ff371a173d8aaf779501e6aa384861fea386"

structure qu8vaddminmaxParams where
  a_multiplier : BitVec 32
  a_zero_point : BitVec 8
  b_multiplier : BitVec 32
  b_zero_point : BitVec 8
  output_max : BitVec 8
  output_min : BitVec 8
  output_zero_point : BitVec 16
  shift : BitVec 32
  deriving Repr, DecidableEq

def neonBlock8FromIntrinsics (p : qu8vaddminmaxParams)
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

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : qu8vaddminmaxParams)
    (loadedA loadedB : List (BitVec 8)) (live : Nat) : List (BitVec 8) :=
  let va_zero_point_0 := List.replicate 8 ((p.a_zero_point).truncate 8)
  let vb_zero_point_0 := List.replicate 8 ((p.b_zero_point).truncate 8)
  let va_multiplier_0 := List.replicate 4 ((p.a_multiplier).truncate 32)
  let vb_multiplier_0 := List.replicate 4 ((p.b_multiplier).truncate 32)
  let vright_shift_0 := List.replicate 4 (-(p.shift).truncate 32)
  let voutput_zero_point_0 := List.replicate 8 ((p.output_zero_point).truncate 16)
  let voutput_min_0 := List.replicate 8 ((p.output_min).truncate 8)
  let voutput_max_0 := List.replicate 8 ((p.output_max).truncate 8)
  let va01234567_1 := (loadedA).take 8
  let vb01234567_1 := (loadedB).take 8
  let call_0038 := SALT.Intrinsics.Neon.vsubl_u8 (va01234567_1) (va_zero_point_0)
  let vxa01234567_1 := call_0038
  let call_0040 := SALT.Intrinsics.Neon.vsubl_u8 (vb01234567_1) (vb_zero_point_0)
  let vxb01234567_1 := call_0040
  let call_0042 := (vxa01234567_1).take 4
  let call_0043 := SALT.Intrinsics.Neon.vmovl_s16 (call_0042)
  let vacc0123_3 := SALT.Intrinsics.Neon.vmulq_s32 (call_0043) ((p.a_multiplier).truncate 32)
  let call_0045 := (vxa01234567_1).drop 4
  let call_0046 := SALT.Intrinsics.Neon.vmovl_s16 (call_0045)
  let vacc4567_3 := SALT.Intrinsics.Neon.vmulq_s32 (call_0046) ((p.a_multiplier).truncate 32)
  let call_0048 := (vxb01234567_1).take 4
  let call_0049 := SALT.Intrinsics.Neon.vmovl_s16 (call_0048)
  let vacc0123_4 := SALT.Intrinsics.Neon.vmlaq_s32 (vacc0123_3) (call_0049) ((p.b_multiplier).truncate 32)
  let call_0051 := (vxb01234567_1).drop 4
  let call_0052 := SALT.Intrinsics.Neon.vmovl_s16 (call_0051)
  let vacc4567_4 := SALT.Intrinsics.Neon.vmlaq_s32 (vacc4567_3) (call_0052) ((p.b_multiplier).truncate 32)
  let vacc0123_5 := SALT.Intrinsics.Neon.vrshlq_s32_vec (vacc0123_4) (vright_shift_0)
  let vacc4567_5 := SALT.Intrinsics.Neon.vrshlq_s32_vec (vacc4567_4) (vright_shift_0)
  let call_0056 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc0123_5)
  let call_0057 := SALT.Intrinsics.Neon.vqmovn_s32 (vacc4567_5)
  let call_0058 := call_0056 ++ call_0057
  let vacc01234567_1 := SALT.Intrinsics.Neon.vqaddq_s16 (call_0058) ((p.output_zero_point).truncate 16)
  let vout01234567_3 := SALT.Intrinsics.Neon.vqmovun_s16 (vacc01234567_1)
  let vout01234567_4 := SALT.Intrinsics.Neon.vmax_u8 (vout01234567_3) (voutput_min_0)
  let vout01234567_5 := SALT.Intrinsics.Neon.vmin_u8 (vout01234567_4) (voutput_max_0)
  let call_0063 := vout01234567_5
  let stored4 := if live.testBit 2 then (call_0063).take 4 else []
  let vout01234567_6 := ((vout01234567_5 ++ vout01234567_5).drop 4).take 8
  let after4 := if live.testBit 2 then vout01234567_6 else vout01234567_5
  let call_0066 := after4
  let stored2 := if live.testBit 1 then (call_0066).take 2 else []
  let vout01234567_7 := ((after4 ++ after4).drop 2).take 8
  let after2 := if live.testBit 1 then vout01234567_7 else after4
  let stored1 := if live.testBit 0 then (after2).take 1 else []
  (stored4) ++ (stored2) ++ (stored1)

/-- Generated value-only lifting of the validated 8/4/2/1 control shape.

`overreadA` and `overreadB` supply the bytes physically loaded beyond a nonempty short tail.
This definition does not establish that those bytes are legally readable.
-/
def neonValueLoopWithOverreadFromIntrinsics (p : qu8vaddminmaxParams)
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
def neonValueLoopFromIntrinsics (p : qu8vaddminmaxParams)
    (input_a input_b : List (BitVec 8))
    (sameLength : input_a.length = input_b.length) : List (BitVec 8) :=
  neonValueLoopWithOverreadFromIntrinsics p input_a input_b
    (List.replicate 7 (0 : BitVec 8))
    (List.replicate 7 (0 : BitVec 8)) sameLength

def rvvChunkFromIntrinsics (p : qu8vaddminmaxParams)
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

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : qu8vaddminmaxParams)
    (input_a input_b : List (BitVec 8))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length) :
    List (BitVec 8) :=
  SALT.Kernel.Schedule.processBlocks2 (rvvChunkFromIntrinsics p) input_a input_b sameLength schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : qu8vaddminmaxParams) (x y : BitVec 8) : BitVec 8 :=
  (neonBlock8FromIntrinsics p (List.replicate 8 x) (List.replicate 8 y)).headD (0 : BitVec 8)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : qu8vaddminmaxParams) (x y : BitVec 8) : BitVec 8 :=
  (rvvChunkFromIntrinsics p [x] [y]).headD (0 : BitVec 8)
end SALT.Corpus.qu8vaddminmax
