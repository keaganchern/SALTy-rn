-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.f32vmax

def programManifestSha256 : String := "d61afc01a052de9bedf4527db3e062b9451eba9c5d3e57e8e823390acdd04875"
def consumedEffectsSha256 : String := "9adc3f28c7f4e91df2e091678e3cd8384556c28daec147cfcbd33d63dfe31734"

def neonSourceSha256 : String :=
  "09e27c12a074f0ebac6fb78c055dc8244be915827771359afa16f70527360552"
def rvvSourceSha256 : String :=
  "29040b9201bb2a4150f6fc2d1c69fceda44b60ad683f813a02dc83ac69ec3af6"
def neonPreprocessedSha256 : String :=
  "30be5307d46c5d3c1a6169675d6c37967a260fd43f2cc99313ea73c0e1dbaec1"
def rvvPreprocessedSha256 : String :=
  "a4672d624e7a199db66df0e3b0769d24b783856d28a7fd5f5a3628a684f552aa"
def parseFacadeSha256 : String :=
  "829b8b0358b2a31d50a784422681ac9e821a4369619812194f800dc63287c4bc"
def registrySha256 : String :=
  "cd7768cc5c1270ca0d91d3520c949a2055a10be9a4b9596fc1d7c1ce7bce3a2e"

structure f32vmaxParams where
  deriving Repr, DecidableEq

def neonBlock4FromIntrinsics (p : f32vmaxParams)
    (input_a : List (BitVec 32))
    (input_b : List (BitVec 32)) : List (BitVec 32) :=
  let va_0 := (input_a).take 4
  let vb_0 := (input_b).take 4
  let vacc_0 := SALT.Intrinsics.Neon.vmaxq_f32 (va_0) (vb_0)
  (vacc_0)

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : f32vmaxParams)
    (loadedA loadedB : List (BitVec 32)) (live : Nat) : List (BitVec 32) :=
  let va_1 := (loadedA).take 4
  let vb_1 := (loadedB).take 4
  let vacc_1 := SALT.Intrinsics.Neon.vmaxq_f32 (va_1) (vb_1)
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
def neonValueLoopWithOverreadFromIntrinsics (p : f32vmaxParams)
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
def neonValueLoopFromIntrinsics (p : f32vmaxParams)
    (input_a input_b : List (BitVec 32))
    (sameLength : input_a.length = input_b.length) : List (BitVec 32) :=
  neonValueLoopWithOverreadFromIntrinsics p input_a input_b
    (List.replicate 3 (0 : BitVec 32))
    (List.replicate 3 (0 : BitVec 32)) sameLength

def rvvChunkFromIntrinsics (p : f32vmaxParams)
    (input_a : List (BitVec 32))
    (input_b : List (BitVec 32)) : List (BitVec 32) :=
  let va_0 := input_a
  let vb_0 := input_b
  let vacc_0 := SALT.Intrinsics.RVV.vfmax_vv_f32 (va_0) (vb_0)
  vacc_0

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : f32vmaxParams)
    (input_a input_b : List (BitVec 32))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length) :
    List (BitVec 32) :=
  SALT.Kernel.Schedule.processBlocks2 (rvvChunkFromIntrinsics p) input_a input_b sameLength schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : f32vmaxParams) (x y : BitVec 32) : BitVec 32 :=
  (neonBlock4FromIntrinsics p (List.replicate 4 x) (List.replicate 4 y)).headD (0 : BitVec 32)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : f32vmaxParams) (x y : BitVec 32) : BitVec 32 :=
  (rvvChunkFromIntrinsics p [x] [y]).headD (0 : BitVec 32)
end SALT.Corpus.f32vmax
