-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.f32vmul

def programManifestSha256 : String := "7dd1088c01782333dc85e2c93d0a7834c45ab595cdb5920d3204c7908db47327"
def consumedEffectsSha256 : String := "778a3c95a69a32064325e308b2762010f0d4132971b0b5dd7315a7e94220e284"

def neonSourceSha256 : String :=
  "260f2fefce97565f686fe95b968688d9be83c9fe8c6724d9cbab30632df8df6c"
def rvvSourceSha256 : String :=
  "6f2acd553de265d3b8304d47009bb725dde8118539acf948cbdf0f7de79f235c"
def neonPreprocessedSha256 : String :=
  "0190b144668cff69bc7c1ecd0388ee9d622bb0f144528a6435b30dd6e13ffcc0"
def rvvPreprocessedSha256 : String :=
  "efe70cf7d6ac77a716e648e33ce2058e5872450fb334dbbb6764ef19c387a508"
def parseFacadeSha256 : String :=
  "829b8b0358b2a31d50a784422681ac9e821a4369619812194f800dc63287c4bc"
def registrySha256 : String :=
  "c02810c995532002967a7b67fcb880c4f1b10f62c268bc3c369901aa5246bc51"

structure f32vmulParams where
  deriving Repr, DecidableEq

def neonBlock4FromIntrinsics (p : f32vmulParams)
    (input_a : List (BitVec 32))
    (input_b : List (BitVec 32)) : List (BitVec 32) :=
  let va_0 := (input_a).take 4
  let vb_0 := (input_b).take 4
  let vacc_0 := SALT.Intrinsics.Neon.vmulq_f32 (va_0) (vb_0)
  (vacc_0)

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : f32vmulParams)
    (loadedA loadedB : List (BitVec 32)) (live : Nat) : List (BitVec 32) :=
  let va_1 := (loadedA).take 4
  let vb_1 := (loadedB).take 4
  let vacc_1 := SALT.Intrinsics.Neon.vmulq_f32 (va_1) (vb_1)
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
def neonValueLoopWithOverreadFromIntrinsics (p : f32vmulParams)
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
def neonValueLoopFromIntrinsics (p : f32vmulParams)
    (input_a input_b : List (BitVec 32))
    (sameLength : input_a.length = input_b.length) : List (BitVec 32) :=
  neonValueLoopWithOverreadFromIntrinsics p input_a input_b
    (List.replicate 3 (0 : BitVec 32))
    (List.replicate 3 (0 : BitVec 32)) sameLength

def rvvChunkFromIntrinsics (p : f32vmulParams)
    (input_a : List (BitVec 32))
    (input_b : List (BitVec 32)) : List (BitVec 32) :=
  let va_0 := input_a
  let vb_0 := input_b
  let vacc_0 := SALT.Intrinsics.RVV.vfmul_vv_f32 (va_0) (vb_0)
  vacc_0

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : f32vmulParams)
    (input_a input_b : List (BitVec 32))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length) :
    List (BitVec 32) :=
  SALT.Kernel.Schedule.processBlocks2 (rvvChunkFromIntrinsics p) input_a input_b sameLength schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : f32vmulParams) (x y : BitVec 32) : BitVec 32 :=
  (neonBlock4FromIntrinsics p (List.replicate 4 x) (List.replicate 4 y)).headD (0 : BitVec 32)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : f32vmulParams) (x y : BitVec 32) : BitVec 32 :=
  (rvvChunkFromIntrinsics p [x] [y]).headD (0 : BitVec 32)
end SALT.Corpus.f32vmul
