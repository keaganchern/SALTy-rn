-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.f32vlrelu

def programManifestSha256 : String := "7ebec620516835c5b5db35a335b1f6d6fdffd0e38120b7a96c65f075c85634e0"
def consumedEffectsSha256 : String := "5f9b0ffa4d7ddc26972dc0c9140860a6cff87e2f0aba85a8fe951b6080beb327"

def neonSourceSha256 : String :=
  "4c8689e540b354176daea7b00a01e854917c738f74ba4a3fcca01f944118e3b6"
def rvvSourceSha256 : String :=
  "682d136f5c7ac833199fcf0e5f9f83f8c169634de72cc55a0effa99676c5516e"
def neonPreprocessedSha256 : String :=
  "b1814538fd15b0b525535ed5e2085d76b3917a7368db6249f1ff794077766fb7"
def rvvPreprocessedSha256 : String :=
  "ec2ad64d76293d5a7102547fd0f214587e6409848a7ca811049d41fdf5751788"
def parseFacadeSha256 : String :=
  "829b8b0358b2a31d50a784422681ac9e821a4369619812194f800dc63287c4bc"
def registrySha256 : String :=
  "4614be47e76ea8df4f30903757cb1fe85627ebe2631c73550fe02cc0f68e749a"

structure f32vlreluParams where
  slope : BitVec 32
  deriving Repr, DecidableEq

def neonBlock4FromIntrinsics (p : f32vlreluParams)
    (input : List (BitVec 32)) : List (BitVec 32) :=
  let vslope_0 := List.replicate 4 ((p.slope).truncate 32)
  let vx0123_0 := (input).take 4
  let vacc0123_0 := SALT.Intrinsics.Neon.vmulq_f32 (vx0123_0) (vslope_0)
  let call_0003 := vx0123_0
  let call_0004 := List.replicate 4 (0)
  let vmask0123_0 := SALT.Intrinsics.Neon.vcltq_s32 (call_0003) (call_0004)
  let vacc0123_1 := SALT.Intrinsics.Neon.vbslq_f32 (vmask0123_0) (vacc0123_0) (vx0123_0)
  (vacc0123_1)

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : f32vlreluParams)
    (loaded : List (BitVec 32)) (live : Nat) : List (BitVec 32) :=
  let vslope_0 := List.replicate 4 ((p.slope).truncate 32)
  let vx_0 := (loaded).take 4
  let vacc_0 := SALT.Intrinsics.Neon.vmulq_f32 (vx_0) (vslope_0)
  let call_0010 := vx_0
  let call_0011 := List.replicate 4 (0)
  let vmask_0 := SALT.Intrinsics.Neon.vcltq_s32 (call_0010) (call_0011)
  let vacc_1 := SALT.Intrinsics.Neon.vbslq_f32 (vmask_0) (vacc_0) (vx_0)
  let vacc_lo_0 := (vacc_1).take 2
  let stored2 := if live.testBit 1 then (vacc_lo_0).take 2 else []
  let vacc_lo_1 := (vacc_1).drop 2
  let after2 := if live.testBit 1 then vacc_lo_1 else vacc_lo_0
  let stored1 := if live.testBit 0 then (after2).take 1 else []
  (stored2) ++ (stored1)

/-- Generated value-only lifting of the validated 4/2/1 control shape.

`overread` supplies the bytes physically loaded beyond a nonempty short tail.
This definition does not establish that those bytes are legally readable.
-/
def neonValueLoopWithOverreadFromIntrinsics (p : f32vlreluParams)
    (input overread : List (BitVec 32)) : List (BitVec 32) :=
  SALT.Kernel.Schedule.runFixedChunkTail 4 (by decide)
    (neonBlock4FromIntrinsics p)
    (fun tail =>
      let loaded := (tail ++ overread).take 4
      neonPartialTailLivePrefixFromIntrinsics p loaded tail.length)
    input

/-- Zero-filled compatibility specialization of the explicit-overread model. -/
def neonValueLoopFromIntrinsics (p : f32vlreluParams)
    (input : List (BitVec 32)) : List (BitVec 32) :=
  neonValueLoopWithOverreadFromIntrinsics p input
    (List.replicate 3 (0 : BitVec 32))

def rvvChunkFromIntrinsics (p : f32vlreluParams)
    (input : List (BitVec 32)) : List (BitVec 32) :=
  let vx_0 := input
  let vacc_0 := SALT.Intrinsics.RVV.vfmul_vf_f32 (vx_0) ((p.slope).truncate 32)
  let vx_i_0 := vx_0
  let mask_0 := SALT.Intrinsics.RVV.vmslt_vx_i32 (vx_i_0) (0)
  let vout_0 := SALT.Intrinsics.RVV.vmerge_vvm_f32 (vx_0) (vacc_0) (mask_0)
  vout_0

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : f32vlreluParams)
    (input : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length) :
    List (BitVec 32) :=
  SALT.Kernel.Schedule.processBlocks (rvvChunkFromIntrinsics p) input schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : f32vlreluParams) (x : BitVec 32) : BitVec 32 :=
  (neonBlock4FromIntrinsics p (List.replicate 4 x)).headD (0 : BitVec 32)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : f32vlreluParams) (x : BitVec 32) : BitVec 32 :=
  (rvvChunkFromIntrinsics p [x]).headD (0 : BitVec 32)
end SALT.Corpus.f32vlrelu
