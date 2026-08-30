-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.f32vsub

def programManifestSha256 : String := "33fedafa4fc5a975f06882912670aeb2372a741568c69722524ecd0bb7243ede"
def consumedEffectsSha256 : String := "988e3265d3bf6375055454e4b3b2f8b1b35fc84e6cb82e554c0b9faaa3db06ae"

def neonSourceSha256 : String :=
  "35f7b6696edf0f22cad1375a3033484f400cf40a8c26d25c163b3bce8c722e2d"
def rvvSourceSha256 : String :=
  "5f343f76accfc791373012fbc3f309c08883d1dc6cd2c59c658a4582739bd18c"
def neonPreprocessedSha256 : String :=
  "87e3b8ff3d5032de35ff21b13d23190ccbdab7eacf5e90fb070319f6f4b72614"
def rvvPreprocessedSha256 : String :=
  "43882d4ed411c9bc994f728e09fa66571286f2e8ded5af9d03991d98b8057453"
def parseFacadeSha256 : String :=
  "829b8b0358b2a31d50a784422681ac9e821a4369619812194f800dc63287c4bc"
def registrySha256 : String :=
  "7d1fd6d5788558c511dd0d429a1767cf0b73c74f7ae4cfbbffd6f4529c063071"

structure f32vsubParams where
  deriving Repr, DecidableEq

def neonBlock4FromIntrinsics (p : f32vsubParams)
    (input_a : List (BitVec 32))
    (input_b : List (BitVec 32)) : List (BitVec 32) :=
  let va_0 := (input_a).take 4
  let vb_0 := (input_b).take 4
  let vacc_0 := SALT.Intrinsics.Neon.vsubq_f32 (va_0) (vb_0)
  (vacc_0)

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : f32vsubParams)
    (loadedA loadedB : List (BitVec 32)) (live : Nat) : List (BitVec 32) :=
  let va_1 := (loadedA).take 4
  let vb_1 := (loadedB).take 4
  let vacc_1 := SALT.Intrinsics.Neon.vsubq_f32 (va_1) (vb_1)
  let vacc_lo_0 := (vacc_1).take 2
  let stored2 := if live.testBit 1 then (vacc_lo_0).take 2 else []
  let vacc_lo_1 := (vacc_1).drop 2
  let after2 := if live.testBit 1 then vacc_lo_1 else vacc_lo_0
  let stored1 := if live.testBit 0 then (after2).take 1 else []
  (stored2) ++ (stored1)

/-- Generated value-only lifting of the validated 4/2/1 control shape.

`overreadA` and `overreadB` supply the bytes physically loaded beyond a nonempty short tail.
This definition does not establish that those bytes are legally readable.
-/
def neonValueLoopWithOverreadFromIntrinsics (p : f32vsubParams)
    (input_a input_b overreadA overreadB : List (BitVec 32))
    (sameLength : input_a.length = input_b.length) : List (BitVec 32) :=
  SALT.Kernel.Schedule.runFixedChunkTail2 4 (by decide)
    (neonBlock4FromIntrinsics p)
    (fun tailA tailB =>
      let loadedA := (tailA ++ overreadA).take 4
      let loadedB := (tailB ++ overreadB).take 4
      neonPartialTailLivePrefixFromIntrinsics p loadedA loadedB tailA.length)
    input_a input_b sameLength

/-- Zero-filled compatibility specialization of the explicit-overread model. -/
def neonValueLoopFromIntrinsics (p : f32vsubParams)
    (input_a input_b : List (BitVec 32))
    (sameLength : input_a.length = input_b.length) : List (BitVec 32) :=
  neonValueLoopWithOverreadFromIntrinsics p input_a input_b
    (List.replicate 3 (0 : BitVec 32))
    (List.replicate 3 (0 : BitVec 32)) sameLength

def rvvChunkFromIntrinsics (p : f32vsubParams)
    (input_a : List (BitVec 32))
    (input_b : List (BitVec 32)) : List (BitVec 32) :=
  let va_0 := input_a
  let vb_0 := input_b
  let vacc_0 := SALT.Intrinsics.RVV.vfsub_vv_f32 (va_0) (vb_0)
  vacc_0

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : f32vsubParams)
    (input_a input_b : List (BitVec 32))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length) :
    List (BitVec 32) :=
  SALT.Kernel.Schedule.processBlocks2 (rvvChunkFromIntrinsics p) input_a input_b sameLength schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : f32vsubParams) (x y : BitVec 32) : BitVec 32 :=
  (neonBlock4FromIntrinsics p (List.replicate 4 x) (List.replicate 4 y)).headD (0 : BitVec 32)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : f32vsubParams) (x y : BitVec 32) : BitVec 32 :=
  (rvvChunkFromIntrinsics p [x] [y]).headD (0 : BitVec 32)
end SALT.Corpus.f32vsub
