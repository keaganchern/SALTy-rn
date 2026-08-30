-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.f32vrndne

def programManifestSha256 : String := "2c33b8521de83e8c732a4b39165bc657a2295431fe098fc8d1005ff249d1ee8d"
def consumedEffectsSha256 : String := "d6e528a833d4f429085678111bc7dc52b984d8d996f06dcf3e882c62838d89d1"

def neonSourceSha256 : String :=
  "b02a27bfc9953ba14c6a43c583a566ebf6c41966beebdaa7143042fd4cf319fe"
def rvvSourceSha256 : String :=
  "29488445db06359d64d9aef2c5477f2fc6ef750733287ca5c75f553f8ea1b530"
def neonPreprocessedSha256 : String :=
  "6ce6a4600cf1058b50cfa380f48d0b75803210a8cd45f5574daae89c0cc95469"
def rvvPreprocessedSha256 : String :=
  "c9860d1fc6b19252920a117896c8876349682fcf1206b913ad583f0dc4cc73bd"
def parseFacadeSha256 : String :=
  "829b8b0358b2a31d50a784422681ac9e821a4369619812194f800dc63287c4bc"
def registrySha256 : String :=
  "f64aaa61d4d7f9edd610818e6e7c73890717eb93e65aabc16c949a773bbe8388"

structure f32vrndneParams where
  deriving Repr, DecidableEq

def neonBlock4FromIntrinsics (p : f32vrndneParams)
    (input : List (BitVec 32)) : List (BitVec 32) :=
  let call_0000 := List.replicate 4 (1258291200)
  let vmagic_number_0 := call_0000
  let vx0123_0 := (input).take 4
  let vabsx0123_0 := SALT.Intrinsics.Neon.vabsq_f32 (vx0123_0)
  let vrndmask0123_0 := SALT.Intrinsics.Neon.vcaltq_f32 (vmagic_number_0) (vx0123_0)
  let vrndabsx0123_0 := SALT.Intrinsics.Neon.vaddq_f32 (vabsx0123_0) (vmagic_number_0)
  let call_0006 := List.replicate 4 (2147483648)
  let vrndmask0123_1 := SALT.Intrinsics.Neon.vorrq_u32 (vrndmask0123_0) (call_0006)
  let vrndabsx0123_1 := SALT.Intrinsics.Neon.vsubq_f32 (vrndabsx0123_0) (vmagic_number_0)
  let vy0123_0 := SALT.Intrinsics.Neon.vbslq_f32 (vrndmask0123_1) (vx0123_0) (vrndabsx0123_1)
  (vy0123_0)

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : f32vrndneParams)
    (loaded : List (BitVec 32)) (live : Nat) : List (BitVec 32) :=
  let call_0000 := List.replicate 4 (1258291200)
  let vmagic_number_0 := call_0000
  let vx_0 := (loaded).take 4
  let vabsx_0 := SALT.Intrinsics.Neon.vabsq_f32 (vx_0)
  let vrndmask_0 := SALT.Intrinsics.Neon.vcaltq_f32 (vmagic_number_0) (vx_0)
  let vrndabsx_0 := SALT.Intrinsics.Neon.vaddq_f32 (vabsx_0) (vmagic_number_0)
  let call_0015 := List.replicate 4 (2147483648)
  let vrndmask_1 := SALT.Intrinsics.Neon.vorrq_u32 (vrndmask_0) (call_0015)
  let vrndabsx_1 := SALT.Intrinsics.Neon.vsubq_f32 (vrndabsx_0) (vmagic_number_0)
  let vy_0 := SALT.Intrinsics.Neon.vbslq_f32 (vrndmask_1) (vx_0) (vrndabsx_1)
  let vy_lo_0 := (vy_0).take 2
  let stored2 := if live.testBit 1 then (vy_lo_0).take 2 else []
  let vy_lo_1 := (vy_0).drop 2
  let after2 := if live.testBit 1 then vy_lo_1 else vy_lo_0
  let stored1 := if live.testBit 0 then (after2).take 1 else []
  (stored2) ++ (stored1)

/-- Generated value-only lifting of the validated 4/2/1 control shape.

`overread` supplies the bytes physically loaded beyond a nonempty short tail.
This definition does not establish that those bytes are legally readable.
-/
def neonValueLoopWithOverreadFromIntrinsics (p : f32vrndneParams)
    (input overread : List (BitVec 32)) : List (BitVec 32) :=
  SALT.Kernel.Schedule.runFixedChunkTail 4 (by decide)
    (neonBlock4FromIntrinsics p)
    (fun tail =>
      let loaded := (tail ++ overread).take 4
      neonPartialTailLivePrefixFromIntrinsics p loaded tail.length)
    input

/-- Zero-filled compatibility specialization of the explicit-overread model. -/
def neonValueLoopFromIntrinsics (p : f32vrndneParams)
    (input : List (BitVec 32)) : List (BitVec 32) :=
  neonValueLoopWithOverreadFromIntrinsics p input
    (List.replicate 3 (0 : BitVec 32))

def rvvChunkFromIntrinsics (p : f32vrndneParams)
    (input : List (BitVec 32)) : List (BitVec 32) :=
  let vx_0 := input
  let vabsx_0 := SALT.Intrinsics.RVV.vfabs_v_f32 (vx_0)
  let cmp_0 := SALT.Intrinsics.RVV.vmfgt_vf_f32 (vabsx_0) (1258291200)
  let vrndabsx_0 := SALT.Intrinsics.RVV.vfadd_vf_f32 (vabsx_0) (1258291200)
  let vrndabsx_1 := SALT.Intrinsics.RVV.vfsub_vf_f32 (vrndabsx_0) (1258291200)
  let vrnd_signed_0 := SALT.Intrinsics.RVV.vfsgnj_vv_f32 (vrndabsx_1) (vx_0)
  let vy_0 := SALT.Intrinsics.RVV.vmerge_vvm_f32 (vrnd_signed_0) (vx_0) (cmp_0)
  let is_nan_0 := SALT.Intrinsics.RVV.vmfne_vv_f32 (vx_0) (vx_0)
  let vx_u32_0 := vx_0
  let vx_quiet_0 := SALT.Intrinsics.RVV.vor_vx_u32 (vx_u32_0) (4194304)
  let vx_qnan_0 := vx_quiet_0
  let vy_1 := SALT.Intrinsics.RVV.vmerge_vvm_f32 (vy_0) (vx_qnan_0) (is_nan_0)
  vy_1

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : f32vrndneParams)
    (input : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length) :
    List (BitVec 32) :=
  SALT.Kernel.Schedule.processBlocks (rvvChunkFromIntrinsics p) input schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : f32vrndneParams) (x : BitVec 32) : BitVec 32 :=
  (neonBlock4FromIntrinsics p (List.replicate 4 x)).headD (0 : BitVec 32)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : f32vrndneParams) (x : BitVec 32) : BitVec 32 :=
  (rvvChunkFromIntrinsics p [x]).headD (0 : BitVec 32)
end SALT.Corpus.f32vrndne
