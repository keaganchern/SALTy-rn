-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.qs8f32vcvt

def programManifestSha256 : String := "d16bae448447d02be239c530a0faef7e653372cfa036f211850c88bf4aa9043c"
def consumedEffectsSha256 : String := "98b1e6067a0c4391f6c25e6ba4376c5503b51bc3e8bc623dc9dbbf41529390ba"

def neonSourceSha256 : String :=
  "d8dbc84351f0154858b2bd940ea42a1e3031ec75a03640a4842a164e219a4063"
def rvvSourceSha256 : String :=
  "407dd1c3b927c122de70ce9709cb8aa419d70c7aec219996baa0132723f7534a"
def neonPreprocessedSha256 : String :=
  "8bfe7e2616190ed7d284a81d2f04ce71c9e5cafc838f585dd33808b9690ed4cb"
def rvvPreprocessedSha256 : String :=
  "ff4be1735a7aba3113702d9c540140a405ea8037672bdda2c931d142989aa8f4"
def parseFacadeSha256 : String :=
  "829b8b0358b2a31d50a784422681ac9e821a4369619812194f800dc63287c4bc"
def registrySha256 : String :=
  "b0bd45831a269f727fc050d9bad873602cbdcbe12717f6026f79bfc6872cd970"

structure qs8f32vcvtParams where
  scale : BitVec 32
  zero_point : BitVec 32
  deriving Repr, DecidableEq

def neonBlock8FromIntrinsics (p : qs8f32vcvtParams)
    (input : List (BitVec 8)) : List (BitVec 32) :=
  let vminus_zero_point_0 := List.replicate 8 (-(p.zero_point).truncate 16)
  let vscale_0 := List.replicate 4 ((p.scale).truncate 32)
  let vx_0 := (input).take 8
  let vhx_0 := SALT.Intrinsics.Neon.vaddw_s8 (vminus_zero_point_0) (vx_0)
  let call_0004 := (vhx_0).take 4
  let vwx_lo_0 := SALT.Intrinsics.Neon.vmovl_s16 (call_0004)
  let call_0006 := (vhx_0).drop 4
  let vwx_hi_0 := SALT.Intrinsics.Neon.vmovl_s16 (call_0006)
  let vy_lo_0 := SALT.Intrinsics.Neon.vcvtq_f32_s32 (vwx_lo_0)
  let vy_hi_0 := SALT.Intrinsics.Neon.vcvtq_f32_s32 (vwx_hi_0)
  let vy_lo_1 := SALT.Intrinsics.Neon.vmulq_f32 (vy_lo_0) (vscale_0)
  let vy_hi_1 := SALT.Intrinsics.Neon.vmulq_f32 (vy_hi_0) (vscale_0)
  (vy_lo_1) ++ (vy_hi_1)

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : qs8f32vcvtParams)
    (loaded : List (BitVec 8)) (live : Nat) : List (BitVec 32) :=
  let vminus_zero_point_0 := List.replicate 8 (-(p.zero_point).truncate 16)
  let vscale_0 := List.replicate 4 ((p.scale).truncate 32)
  let vx_1 := (loaded).take 8
  let vhx_1 := SALT.Intrinsics.Neon.vaddw_s8 (vminus_zero_point_0) (vx_1)
  let call_0016 := (vhx_1).take 4
  let vwx_lo_1 := SALT.Intrinsics.Neon.vmovl_s16 (call_0016)
  let call_0018 := (vhx_1).drop 4
  let vwx_hi_1 := SALT.Intrinsics.Neon.vmovl_s16 (call_0018)
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
def neonValueLoopWithOverreadFromIntrinsics (p : qs8f32vcvtParams)
    (input overread : List (BitVec 8)) : List (BitVec 32) :=
  SALT.Kernel.Schedule.runFixedChunkTail 8 (by decide)
    (neonBlock8FromIntrinsics p)
    (fun tail =>
      let loaded := (tail ++ overread).take 8
      neonPartialTailLivePrefixFromIntrinsics p loaded tail.length)
    input

/-- Zero-filled compatibility specialization of the explicit-overread model. -/
def neonValueLoopFromIntrinsics (p : qs8f32vcvtParams)
    (input : List (BitVec 8)) : List (BitVec 32) :=
  neonValueLoopWithOverreadFromIntrinsics p input
    (List.replicate 7 (0 : BitVec 8))

def rvvChunkFromIntrinsics (p : qs8f32vcvtParams)
    (input : List (BitVec 8)) : List (BitVec 32) :=
  let vx_0 := input
  let vhx_0 := SALT.Intrinsics.RVV.vsext_vf2_i16 (vx_0)
  let vhx_1 := SALT.Intrinsics.RVV.vsub_vx_i16 (vhx_0) ((p.zero_point).truncate 16)
  let vwx_0 := SALT.Intrinsics.RVV.vsext_vf2 (vhx_1)
  let vy_0 := SALT.Intrinsics.RVV.vfcvt_f_x_v_f32 (vwx_0)
  let vy_1 := SALT.Intrinsics.RVV.vfmul_vf_f32 (vy_0) ((p.scale).truncate 32)
  vy_1

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : qs8f32vcvtParams)
    (input : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length) :
    List (BitVec 32) :=
  SALT.Kernel.Schedule.processBlocks (rvvChunkFromIntrinsics p) input schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : qs8f32vcvtParams) (x : BitVec 8) : BitVec 32 :=
  (neonBlock8FromIntrinsics p (List.replicate 8 x)).headD (0 : BitVec 32)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : qs8f32vcvtParams) (x : BitVec 8) : BitVec 32 :=
  (rvvChunkFromIntrinsics p [x]).headD (0 : BitVec 32)
end SALT.Corpus.qs8f32vcvt
