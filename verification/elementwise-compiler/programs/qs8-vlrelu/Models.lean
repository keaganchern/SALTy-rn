-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.qs8vlrelu

def programManifestSha256 : String := "8c8fe6c60f2e5665ea775cd388a19e8930a6ae377a5ccccf1a6124fd7bba3c19"
def consumedEffectsSha256 : String := "d30399e898565c2d5a52ec29fc644b6a03bda52f527d97c7551bab5ad0e8afa5"

def neonSourceSha256 : String :=
  "b855a4d1ecc42155b81c2355ce28f221a884bf732625c53e1000ca596abf9d4f"
def rvvSourceSha256 : String :=
  "a6821a3561b7dc9d7be3d1d0ba5582840fac0fa88c4c821abc55b8a831c5f234"
def neonPreprocessedSha256 : String :=
  "653d57f9f3b2df7f5c776356f64a31bc5ca341aac4479eef71ea5509785bdf62"
def rvvPreprocessedSha256 : String :=
  "b6ed5a5a15625a37ad325c814810a91adc48407e178d056dce381b74d2d42289"
def parseFacadeSha256 : String :=
  "142f6d01509954ce78c98dc713664c26c9e1017ca79aa6eb2a25ee717f8b808b"
def registrySha256 : String :=
  "83638250ff25d398eead4c05ef26ba37b5ec7e067477fdc3ff6f0c526483efa6"

structure qs8vlreluParams where
  input_zero_point : BitVec 16
  negative_multiplier : BitVec 16
  output_zero_point : BitVec 16
  positive_multiplier : BitVec 16
  deriving Repr, DecidableEq

def neonBlock8FromIntrinsics (p : qs8vlreluParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vinput_zero_point_0 := List.replicate 8 ((p.input_zero_point).truncate 16)
  let vpositive_multiplier_0 := List.replicate 8 (-(p.positive_multiplier).truncate 16)
  let vnegative_multiplier_0 := List.replicate 8 (-(p.negative_multiplier).truncate 16)
  let voutput_zero_point_0 := List.replicate 8 ((p.output_zero_point).truncate 16)
  let vx_0 := (input).take 8
  let vacc_0 := SALT.Intrinsics.Neon.vsubw_s8 (vinput_zero_point_0) (vx_0)
  let call_0006 := List.replicate 8 (0)
  let vmask_0 := SALT.Intrinsics.Neon.vcltq_s16 (vacc_0) (call_0006)
  let vacc_1 := SALT.Intrinsics.Neon.vshlq_n_s16 (vacc_0) (7)
  let vmultiplier_0 := SALT.Intrinsics.Neon.vbslq_s16 (vmask_0) (vpositive_multiplier_0) (vnegative_multiplier_0)
  let vacc_2 := SALT.Intrinsics.Neon.vqrdmulhq_s16 (vacc_1) (vmultiplier_0)
  let vacc_3 := SALT.Intrinsics.Neon.vqaddq_s16 (vacc_2) ((p.output_zero_point).truncate 16)
  let vy_0 := SALT.Intrinsics.Neon.vqmovn_s16 (vacc_3)
  (vy_0)

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : qs8vlreluParams)
    (loaded : List (BitVec 8)) (live : Nat) : List (BitVec 8) :=
  let vinput_zero_point_0 := List.replicate 8 ((p.input_zero_point).truncate 16)
  let vpositive_multiplier_0 := List.replicate 8 (-(p.positive_multiplier).truncate 16)
  let vnegative_multiplier_0 := List.replicate 8 (-(p.negative_multiplier).truncate 16)
  let voutput_zero_point_0 := List.replicate 8 ((p.output_zero_point).truncate 16)
  let vx_1 := (loaded).take 8
  let vacc_4 := SALT.Intrinsics.Neon.vsubw_s8 (vinput_zero_point_0) (vx_1)
  let call_0016 := List.replicate 8 (0)
  let vmask_1 := SALT.Intrinsics.Neon.vcltq_s16 (vacc_4) (call_0016)
  let vacc_5 := SALT.Intrinsics.Neon.vshlq_n_s16 (vacc_4) (7)
  let vmultiplier_1 := SALT.Intrinsics.Neon.vbslq_s16 (vmask_1) (vpositive_multiplier_0) (vnegative_multiplier_0)
  let vacc_6 := SALT.Intrinsics.Neon.vqrdmulhq_s16 (vacc_5) (vmultiplier_1)
  let vacc_7 := SALT.Intrinsics.Neon.vqaddq_s16 (vacc_6) ((p.output_zero_point).truncate 16)
  let vy_1 := SALT.Intrinsics.Neon.vqmovn_s16 (vacc_7)
  let call_0023 := vy_1
  let stored4 := if live.testBit 2 then (call_0023).take 4 else []
  let vy_2 := ((vy_1 ++ vy_1).drop 4).take 8
  let after4 := if live.testBit 2 then vy_2 else vy_1
  let call_0026 := after4
  let stored2 := if live.testBit 1 then (call_0026).take 2 else []
  let vy_3 := ((after4 ++ after4).drop 2).take 8
  let after2 := if live.testBit 1 then vy_3 else after4
  let stored1 := if live.testBit 0 then (after2).take 1 else []
  (stored4) ++ (stored2) ++ (stored1)

/-- Generated value-only lifting of the validated 8/4/2/1 control shape.

`overread` supplies the bytes physically loaded beyond a nonempty short tail.
This definition does not establish that those bytes are legally readable.
-/
def neonValueLoopWithOverreadFromIntrinsics (p : qs8vlreluParams)
    (input overread : List (BitVec 8)) : List (BitVec 8) :=
  SALT.Kernel.Schedule.runFixedChunkTail 8 (by decide)
    (neonBlock8FromIntrinsics p)
    (fun tail =>
      let loaded := (tail ++ overread).take 8
      neonPartialTailLivePrefixFromIntrinsics p loaded tail.length)
    input

/-- Zero-filled compatibility specialization of the explicit-overread model. -/
def neonValueLoopFromIntrinsics (p : qs8vlreluParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  neonValueLoopWithOverreadFromIntrinsics p input
    (List.replicate 7 (0 : BitVec 8))

def rvvChunkFromIntrinsics (p : qs8vlreluParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vx_0 := input
  let vx_wide_0 := SALT.Intrinsics.RVV.vsext_vf2_i16 (vx_0)
  let vacc_0 := SALT.Intrinsics.RVV.vrsub_vx_i16 (vx_wide_0) ((p.input_zero_point).truncate 16)
  let vmask_0 := SALT.Intrinsics.RVV.vmslt_vx_i16 (vacc_0) (0)
  let vacc_1 := SALT.Intrinsics.RVV.vsll_vx_i16 (vacc_0) (7)
  let vneg_mult_0 := List.replicate input.length (((-p.negative_multiplier)).truncate 16)
  let vmultiplier_0 := SALT.Intrinsics.RVV.vmerge_vxm_i16 (vneg_mult_0) (((-p.positive_multiplier)).truncate 16) (vmask_0)
  let prod_0 := SALT.Intrinsics.RVV.vwmul_vv_i32 (vacc_1) (vmultiplier_0)
  let vacc_2 := SALT.Intrinsics.RVV.vnclip_wx_i16_mode (prod_0) (15) (0)
  let vacc_3 := SALT.Intrinsics.RVV.vsadd_vx (vacc_2) ((p.output_zero_point).truncate 16)
  let vy_0 := SALT.Intrinsics.RVV.vnclip_wx_i8_mode (vacc_3) (0) (2)
  vy_0

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : qs8vlreluParams)
    (input : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length) :
    List (BitVec 8) :=
  SALT.Kernel.Schedule.processBlocks (rvvChunkFromIntrinsics p) input schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : qs8vlreluParams) (x : BitVec 8) : BitVec 8 :=
  (neonBlock8FromIntrinsics p (List.replicate 8 x)).headD x

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : qs8vlreluParams) (x : BitVec 8) : BitVec 8 :=
  (rvvChunkFromIntrinsics p [x]).headD x
end SALT.Corpus.qs8vlrelu
