-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.f32vdiv

def programManifestSha256 : String := "294bfa78bbf0569c2b05ac71d0bef075d0ab516af0de143ee6592fc9edda1cbe"
def consumedEffectsSha256 : String := "07c045c96062c052aaba7ea2d8f8a1b96db745092455d305cf1144af7589494e"

def neonSourceSha256 : String :=
  "164726f8a2ec091ab058ee19dbdd943d89d0a0eb7b7a72b5a8aa646f83c53aa0"
def rvvSourceSha256 : String :=
  "5637c46cc781ada609567f65a010b3d698a010e090834e36c587873ede1e1f3d"
def neonPreprocessedSha256 : String :=
  "c2aa70a6c49e69347c0e3fe221235ea60d51ebc510084a593ce00163b7cc4b39"
def rvvPreprocessedSha256 : String :=
  "c763d11357451b57ce51820b7aa29dbff35fa3b739e1ce53711120bf8ec9c3fb"
def parseFacadeSha256 : String :=
  "829b8b0358b2a31d50a784422681ac9e821a4369619812194f800dc63287c4bc"
def registrySha256 : String :=
  "96f136af221b165552c52f2360f5e0be39d27721c66473f546752159315fce97"

structure f32vdivParams where
  deriving Repr, DecidableEq

def neonBlock4FromIntrinsics (p : f32vdivParams)
    (input_a : List (BitVec 32))
    (input_b : List (BitVec 32)) : List (BitVec 32) :=
  let va_0 := (input_a).take 4
  let vb_0 := (input_b).take 4
  let vacc_0 := SALT.Intrinsics.Neon.vdivq_f32 (va_0) (vb_0)
  (vacc_0)

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : f32vdivParams)
    (loadedA loadedB : List (BitVec 32)) (live : Nat) : List (BitVec 32) :=
  let va_1 := (loadedA).take 4
  let vb_1 := (loadedB).take 4
  let vacc_1 := SALT.Intrinsics.Neon.vdivq_f32 (va_1) (vb_1)
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
def neonValueLoopWithOverreadFromIntrinsics (p : f32vdivParams)
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
def neonValueLoopFromIntrinsics (p : f32vdivParams)
    (input_a input_b : List (BitVec 32))
    (sameLength : input_a.length = input_b.length) : List (BitVec 32) :=
  neonValueLoopWithOverreadFromIntrinsics p input_a input_b
    (List.replicate 3 (0 : BitVec 32))
    (List.replicate 3 (0 : BitVec 32)) sameLength

def rvvChunkFromIntrinsics (p : f32vdivParams)
    (input_a : List (BitVec 32))
    (input_b : List (BitVec 32)) : List (BitVec 32) :=
  let va_0 := input_a
  let vb_0 := input_b
  let vacc_0 := SALT.Intrinsics.RVV.vfdiv_vv_f32 (va_0) (vb_0)
  vacc_0

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : f32vdivParams)
    (input_a input_b : List (BitVec 32))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length) :
    List (BitVec 32) :=
  SALT.Kernel.Schedule.processBlocks2 (rvvChunkFromIntrinsics p) input_a input_b sameLength schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : f32vdivParams) (x y : BitVec 32) : BitVec 32 :=
  (neonBlock4FromIntrinsics p (List.replicate 4 x) (List.replicate 4 y)).headD (0 : BitVec 32)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : f32vdivParams) (x y : BitVec 32) : BitVec 32 :=
  (rvvChunkFromIntrinsics p [x] [y]).headD (0 : BitVec 32)
end SALT.Corpus.f32vdiv
