-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.f32vsqrt

def programManifestSha256 : String := "282c7aefde48b60c175785ac9edd423fbfe0d757f2d55f7591ad59dbd5dcbffc"
def consumedEffectsSha256 : String := "55261d5b187e54fab121fd1a3c9040d9013c66678796158dc0b02870de60e1eb"

def neonSourceSha256 : String :=
  "b4970661c787e642b8428f213a4b60bd894f4a63704ffc31ec96087beab4ef3e"
def rvvSourceSha256 : String :=
  "b09b69f0e4b7de2a839b71c1207f21ac2f024a7aa173e7ca1b4c19cca5b06012"
def neonPreprocessedSha256 : String :=
  "db99b57ef9eaae68bf21ec9d33eb3613963dc0ae023a3220f5f75b4352465265"
def rvvPreprocessedSha256 : String :=
  "b27eff4dc3dc81e328a7a49c70a30dc30bbc9873308a1827078da1a08a13a785"
def parseFacadeSha256 : String :=
  "829b8b0358b2a31d50a784422681ac9e821a4369619812194f800dc63287c4bc"
def registrySha256 : String :=
  "09f4f1028172c33deff3584e85e1bbd3ba218e3b5c79c4e3921b3ecc437ecd3d"

structure f32vsqrtParams where
  deriving Repr, DecidableEq

def neonBlock4FromIntrinsics (p : f32vsqrtParams)
    (input : List (BitVec 32)) : List (BitVec 32) :=
  let vx_0 := (input).take 4
  let vy_0 := SALT.Intrinsics.Neon.vsqrtq_f32 (vx_0)
  (vy_0)

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : f32vsqrtParams)
    (loaded : List (BitVec 32)) (live : Nat) : List (BitVec 32) :=
  let vx_1 := (loaded).take 4
  let vy_1 := SALT.Intrinsics.Neon.vsqrtq_f32 (vx_1)
  let vy_lo_0 := (vy_1).take 2
  let stored2 := if live.testBit 1 then (vy_lo_0).take 2 else []
  let vy_lo_1 := (vy_1).drop 2
  let after2 := if live.testBit 1 then vy_lo_1 else vy_lo_0
  let stored1 := if live.testBit 0 then (after2).take 1 else []
  (stored2) ++ (stored1)

/-- Generated value-only lifting of the validated 4/2/1 control shape.

`overread` supplies the bytes physically loaded beyond a nonempty short tail.
This definition does not establish that those bytes are legally readable.
-/
def neonValueLoopWithOverreadFromIntrinsics (p : f32vsqrtParams)
    (input overread : List (BitVec 32)) : List (BitVec 32) :=
  SALT.Kernel.Schedule.runFixedChunkTail 4 (by decide)
    (neonBlock4FromIntrinsics p)
    (fun tail =>
      let loaded := (tail ++ overread).take 4
      neonPartialTailLivePrefixFromIntrinsics p loaded tail.length)
    input

/-- Zero-filled compatibility specialization of the explicit-overread model. -/
def neonValueLoopFromIntrinsics (p : f32vsqrtParams)
    (input : List (BitVec 32)) : List (BitVec 32) :=
  neonValueLoopWithOverreadFromIntrinsics p input
    (List.replicate 3 (0 : BitVec 32))

def rvvChunkFromIntrinsics (p : f32vsqrtParams)
    (input : List (BitVec 32)) : List (BitVec 32) :=
  let vx_0 := input
  let vy_0 := SALT.Intrinsics.RVV.vfsqrt_v_f32 (vx_0)
  vy_0

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : f32vsqrtParams)
    (input : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length) :
    List (BitVec 32) :=
  SALT.Kernel.Schedule.processBlocks (rvvChunkFromIntrinsics p) input schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : f32vsqrtParams) (x : BitVec 32) : BitVec 32 :=
  (neonBlock4FromIntrinsics p (List.replicate 4 x)).headD (0 : BitVec 32)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : f32vsqrtParams) (x : BitVec 32) : BitVec 32 :=
  (rvvChunkFromIntrinsics p [x]).headD (0 : BitVec 32)
end SALT.Corpus.f32vsqrt
