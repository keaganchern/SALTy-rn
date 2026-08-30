-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.f32vmin

def programManifestSha256 : String := "aef34a24be7416667f9c9f5fc44decd34e9587d8834e8795531f04fedc18cb84"
def consumedEffectsSha256 : String := "44847c40899255878012daef75c8571441d6ce2e09d3ca35e05c54f08bd30869"

def neonSourceSha256 : String :=
  "e7c9e8d03d5bd59bcb91167285c54565a571a406eae8fb9554e86a639a1e7be1"
def rvvSourceSha256 : String :=
  "76fd6aefcbf9f82bf36ead665072d3a24285c1dc63e87ec17e66efa8af39949e"
def neonPreprocessedSha256 : String :=
  "107077e8a90fc8da6f0a50272090a8ac68472c7ed729168c4aa3d0c1a406b8d3"
def rvvPreprocessedSha256 : String :=
  "84208884d23d852a4eb3d41c6f179557e2e48537ae04cb4146352214e83acefe"
def parseFacadeSha256 : String :=
  "829b8b0358b2a31d50a784422681ac9e821a4369619812194f800dc63287c4bc"
def registrySha256 : String :=
  "f4330d2300fcbcc45d3b97f7db741ff980bf558e8a7f135cd64499c2a166c492"

structure f32vminParams where
  deriving Repr, DecidableEq

def neonBlock4FromIntrinsics (p : f32vminParams)
    (input_a : List (BitVec 32))
    (input_b : List (BitVec 32)) : List (BitVec 32) :=
  let va_0 := (input_a).take 4
  let vb_0 := (input_b).take 4
  let vacc_0 := SALT.Intrinsics.Neon.vminq_f32 (va_0) (vb_0)
  (vacc_0)

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : f32vminParams)
    (loadedA loadedB : List (BitVec 32)) (live : Nat) : List (BitVec 32) :=
  let va_1 := (loadedA).take 4
  let vb_1 := (loadedB).take 4
  let vacc_1 := SALT.Intrinsics.Neon.vminq_f32 (va_1) (vb_1)
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
def neonValueLoopWithOverreadFromIntrinsics (p : f32vminParams)
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
def neonValueLoopFromIntrinsics (p : f32vminParams)
    (input_a input_b : List (BitVec 32))
    (sameLength : input_a.length = input_b.length) : List (BitVec 32) :=
  neonValueLoopWithOverreadFromIntrinsics p input_a input_b
    (List.replicate 3 (0 : BitVec 32))
    (List.replicate 3 (0 : BitVec 32)) sameLength

def rvvChunkFromIntrinsics (p : f32vminParams)
    (input_a : List (BitVec 32))
    (input_b : List (BitVec 32)) : List (BitVec 32) :=
  let va_0 := input_a
  let vb_0 := input_b
  let vacc_0 := SALT.Intrinsics.RVV.vfmin_vv_f32 (va_0) (vb_0)
  vacc_0

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : f32vminParams)
    (input_a input_b : List (BitVec 32))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length) :
    List (BitVec 32) :=
  SALT.Kernel.Schedule.processBlocks2 (rvvChunkFromIntrinsics p) input_a input_b sameLength schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : f32vminParams) (x y : BitVec 32) : BitVec 32 :=
  (neonBlock4FromIntrinsics p (List.replicate 4 x) (List.replicate 4 y)).headD (0 : BitVec 32)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : f32vminParams) (x y : BitVec 32) : BitVec 32 :=
  (rvvChunkFromIntrinsics p [x] [y]).headD (0 : BitVec 32)
end SALT.Corpus.f32vmin
