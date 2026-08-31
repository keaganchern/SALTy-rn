-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.qu8f32vcvt

def programManifestSha256 : String := "0f6bee399ba4096f338305997faf543b55e5e4f35bab449c60938b925889cc8d"
def consumedEffectsSha256 : String := "064295cb9c4344ed2388b69e6a6f01c8c59dc75c34df2ca2172556117ca4105b"

def neonSourceSha256 : String :=
  "eaeb29597359201f0e2e13a964c0e883f08af9120ae4ee95360a96cadfbe8fd1"
def rvvSourceSha256 : String :=
  "9b46b2e5c245b3305d75e5228f8891b45709665356206e8481d51dd63164b720"
def neonPreprocessedSha256 : String :=
  "73e67f28895aa55cd6022ebdf59c86283ceb39ac3c723810e58631a4c6d49f37"
def rvvPreprocessedSha256 : String :=
  "fddee8efd34984d7f6beda6c283c8e3d2fe4da2ee7d7d4d6da3815978256a275"
def parseFacadeSha256 : String :=
  "829b8b0358b2a31d50a784422681ac9e821a4369619812194f800dc63287c4bc"
def registrySha256 : String :=
  "89040c0c8f8a365e501a6c449c4a1a15def3993bb1a891dcdc8c6b876a7675a6"

structure qu8f32vcvtParams where
  scale : BitVec 32
  zero_point : BitVec 32
  deriving Repr, DecidableEq

def neonBlock8FromIntrinsics (p : qu8f32vcvtParams)
    (input : List (BitVec 8)) : List (BitVec 32) :=
  let vminus_zero_point_0 := List.replicate 8 (-(p.zero_point).truncate 16)
  let vscale_0 := List.replicate 4 ((p.scale).truncate 32)
  let vx_0 := (input).take 8
  let call_0003 := vminus_zero_point_0
  let call_0004 := SALT.Intrinsics.Neon.vaddw_u8 (call_0003) (vx_0)
  let vhx_0 := call_0004
  let call_0006 := (vhx_0).take 4
  let vwx_lo_0 := SALT.Intrinsics.Neon.vmovl_s16 (call_0006)
  let call_0008 := (vhx_0).drop 4
  let vwx_hi_0 := SALT.Intrinsics.Neon.vmovl_s16 (call_0008)
  let vy_lo_0 := SALT.Intrinsics.Neon.vcvtq_f32_s32 (vwx_lo_0)
  let vy_hi_0 := SALT.Intrinsics.Neon.vcvtq_f32_s32 (vwx_hi_0)
  let vy_lo_1 := SALT.Intrinsics.Neon.vmulq_f32 (vy_lo_0) (vscale_0)
  let vy_hi_1 := SALT.Intrinsics.Neon.vmulq_f32 (vy_hi_0) (vscale_0)
  (vy_lo_1) ++ (vy_hi_1)

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : qu8f32vcvtParams)
    (loaded : List (BitVec 8)) (live : Nat) : List (BitVec 32) :=
  let vminus_zero_point_0 := List.replicate 8 (-(p.zero_point).truncate 16)
  let vscale_0 := List.replicate 4 ((p.scale).truncate 32)
  let vx_1 := (loaded).take 8
  let call_0017 := vminus_zero_point_0
  let call_0018 := SALT.Intrinsics.Neon.vaddw_u8 (call_0017) (vx_1)
  let vhx_1 := call_0018
  let call_0020 := (vhx_1).take 4
  let vwx_lo_1 := SALT.Intrinsics.Neon.vmovl_s16 (call_0020)
  let call_0022 := (vhx_1).drop 4
  let vwx_hi_1 := SALT.Intrinsics.Neon.vmovl_s16 (call_0022)
  let vy_0 := SALT.Intrinsics.Neon.vcvtq_f32_s32 (vwx_lo_1)
  let vy_1 := SALT.Intrinsics.Neon.vmulq_f32 (vy_0) (vscale_0)
  let stored4 := if live.testBit 2 then (vy_1).take 4 else []
  let vy_2 := SALT.Intrinsics.Neon.vcvtq_f32_s32 (vwx_hi_1)
  let vy_3 := SALT.Intrinsics.Neon.vmulq_f32 (vy_2) (vscale_0)
  let after4 := if live.testBit 2 then vy_3 else vy_1
  let vy_lo_2 := (after4).take 2
  let stored2 := if live.testBit 1 then (vy_lo_2).take 2 else []
  let vy_lo_3 := (after4).drop 2
  let after2 := if live.testBit 1 then vy_lo_3 else vy_lo_2
  let stored1 := if live.testBit 0 then (after2).take 1 else []
  (stored4) ++ (stored2) ++ (stored1)

/-- Generated value-only lifting of the validated 8/4/2/1 control shape.

`overread` supplies the bytes physically loaded beyond a nonempty short tail.
This definition does not establish that those bytes are legally readable.
-/
def neonValueLoopWithOverreadFromIntrinsics (p : qu8f32vcvtParams)
    (input overread : List (BitVec 8)) : List (BitVec 32) :=
  SALT.Kernel.Schedule.runFixedChunkTail 8 (by decide)
    (neonBlock8FromIntrinsics p)
    (fun tail =>
      let loaded := (tail ++ overread).take 8
      neonPartialTailLivePrefixFromIntrinsics p loaded tail.length)
    input

/-- Zero-filled compatibility specialization of the explicit-overread model. -/
def neonValueLoopFromIntrinsics (p : qu8f32vcvtParams)
    (input : List (BitVec 8)) : List (BitVec 32) :=
  neonValueLoopWithOverreadFromIntrinsics p input
    (List.replicate 7 (0 : BitVec 8))

def rvvChunkFromIntrinsics (p : qu8f32vcvtParams)
    (input : List (BitVec 8)) : List (BitVec 32) :=
  let vx_0 := input
  let vx_u16_0 := SALT.Intrinsics.RVV.vzext_vf2_u16 (vx_0)
  let vhx_u16_0 := SALT.Intrinsics.RVV.vadd_vx_u16 (vx_u16_0) ((-((p.zero_point).truncate 32)).truncate 16)
  let vhx_0 := vhx_u16_0
  let vwx_0 := SALT.Intrinsics.RVV.vsext_vf2 (vhx_0)
  let vy_0 := SALT.Intrinsics.RVV.vfcvt_f_x_v_f32 (vwx_0)
  let vy_1 := SALT.Intrinsics.RVV.vfmul_vf_f32 (vy_0) ((p.scale).truncate 32)
  vy_1

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : qu8f32vcvtParams)
    (input : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length) :
    List (BitVec 32) :=
  SALT.Kernel.Schedule.processBlocks (rvvChunkFromIntrinsics p) input schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : qu8f32vcvtParams) (x : BitVec 8) : BitVec 32 :=
  (neonBlock8FromIntrinsics p (List.replicate 8 x)).headD (0 : BitVec 32)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : qu8f32vcvtParams) (x : BitVec 8) : BitVec 32 :=
  (rvvChunkFromIntrinsics p [x]).headD (0 : BitVec 32)
end SALT.Corpus.qu8f32vcvt
