-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.f32vmulc

def programManifestSha256 : String := "1692d7ccfff9543490396d8b861901a344b5fdb174d0573c2cef6ca9ee71e0e2"
def consumedEffectsSha256 : String := "192e065b57288e6dc09132d66b8f210e041e59f71d9f2f8b507affefbcbf2400"

def neonSourceSha256 : String :=
  "6d44346474e9925f74ff0243cb4fb4e3111afedfb0db976972f5f19ab7419bdb"
def rvvSourceSha256 : String :=
  "0e0d5032af61f2766859b4f0f71dc87007613d49c99b199cce227345b536522a"
def neonPreprocessedSha256 : String :=
  "c933bb333479b76955f2076fd31d4feea4e7fbc2f2f0cef31cb01d82b212f246"
def rvvPreprocessedSha256 : String :=
  "f005b26a183283af9deb9a7f66ae9b720af992798855b9b065c7e8c6fe022d16"
def parseFacadeSha256 : String :=
  "829b8b0358b2a31d50a784422681ac9e821a4369619812194f800dc63287c4bc"
def registrySha256 : String :=
  "14cf8d28874f5cc79bf93824d939bb6291dda50feb5c97cc061a959da5fe4769"

structure f32vmulcParams where
  broadcast_input_b : BitVec 32
  deriving Repr, DecidableEq

def neonBlock4FromIntrinsics (p : f32vmulcParams)
    (input_a : List (BitVec 32)) : List (BitVec 32) :=
  let vb_0 := List.replicate 4 (p.broadcast_input_b)
  let va_0 := (input_a).take 4
  let vacc_0 := SALT.Intrinsics.Neon.vmulq_f32 (va_0) (vb_0)
  (vacc_0)

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : f32vmulcParams)
    (loaded : List (BitVec 32)) (live : Nat) : List (BitVec 32) :=
  let vb_0 := List.replicate 4 (p.broadcast_input_b)
  let va_1 := (loaded).take 4
  let vacc_1 := SALT.Intrinsics.Neon.vmulq_f32 (va_1) (vb_0)
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
def neonValueLoopWithOverreadFromIntrinsics (p : f32vmulcParams)
    (input_a overread : List (BitVec 32)) : List (BitVec 32) :=
  SALT.Kernel.Schedule.runFixedChunkTail 4 (by decide)
    (neonBlock4FromIntrinsics p)
    (fun tail =>
      let loaded := (tail ++ overread).take 4
      neonPartialTailLivePrefixFromIntrinsics p loaded tail.length)
    input_a

/-- Zero-filled compatibility specialization of the explicit-overread model. -/
def neonValueLoopFromIntrinsics (p : f32vmulcParams)
    (input_a : List (BitVec 32)) : List (BitVec 32) :=
  neonValueLoopWithOverreadFromIntrinsics p input_a
    (List.replicate 3 (0 : BitVec 32))

def rvvChunkFromIntrinsics (p : f32vmulcParams)
    (input_a : List (BitVec 32)) : List (BitVec 32) :=
  let va_0 := input_a
  let vacc_0 := SALT.Intrinsics.RVV.vfmul_vf_f32 (va_0) (p.broadcast_input_b)
  vacc_0

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : f32vmulcParams)
    (input_a : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length) :
    List (BitVec 32) :=
  SALT.Kernel.Schedule.processBlocks (rvvChunkFromIntrinsics p) input_a schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : f32vmulcParams) (x : BitVec 32) : BitVec 32 :=
  (neonBlock4FromIntrinsics p (List.replicate 4 x)).headD (0 : BitVec 32)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : f32vmulcParams) (x : BitVec 32) : BitVec 32 :=
  (rvvChunkFromIntrinsics p [x]).headD (0 : BitVec 32)
end SALT.Corpus.f32vmulc
