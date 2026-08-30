-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule
import SALT.Kernel.ElementwiseFamily

namespace SALT.Corpus.qs8vcvt

def programManifestSha256 : String := "e7ebafcc61b316ad165d7d8f7332e35fea184571d529b779f7e213cd7b2a2951"
def consumedEffectsSha256 : String := "42f6ee6e9d155f5e5ce6ec28cc078b562bdfff34581e44f6082c5a83392cfb6f"

def neonSourceSha256 : String :=
  "715bd7cd48e9241c1a56b287cbfc2c7e2fbbc100e22226abea93d438b137530d"
def rvvSourceSha256 : String :=
  "19da29a3dd0c32ac1a44ad5cec73b0e25d81ecd765a60e9a01e6a128c21f4b76"
def neonPreprocessedSha256 : String :=
  "ef12c4fd0f90356e272f514099e669fd748c97d9740f4f3ddc22d59595723e28"
def rvvPreprocessedSha256 : String :=
  "733efa4bed1f4f407b6d51e0dcffe04b28be27cb0e40c1d534ccb1a4e17f8972"
def parseFacadeSha256 : String :=
  "6e8a1a41f53ecd88abdff17e8a4ca08aa47199a189155d4a7bbc551f4891fa54"
def registrySha256 : String :=
  "9ef23b4587fe752956d0c21de0b4c2e1538b7e9b4f5ee3437d2db34f2a5f2641"

structure qs8vcvtParams where
  input_zero_point : BitVec 16
  multiplier : BitVec 32
  output_zero_point : BitVec 16
  deriving Repr, DecidableEq

def neonBlock8FromIntrinsics (p : qs8vcvtParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vinput_zero_point_0 := List.replicate 8 ((p.input_zero_point).truncate 16)
  let vmultiplier_0 := List.replicate 8 (-(p.multiplier).truncate 16)
  let voutput_zero_point_0 := List.replicate 8 ((p.output_zero_point).truncate 16)
  let vx_0 := (input).take 8
  let vacc_0 := SALT.Intrinsics.Neon.vsubw_s8 (vinput_zero_point_0) (vx_0)
  let vacc_1 := SALT.Intrinsics.Neon.vshlq_n_s16 (vacc_0) (7)
  let vacc_2 := SALT.Intrinsics.Neon.vqrdmulhq_s16 (vacc_1) (vmultiplier_0)
  let vacc_3 := SALT.Intrinsics.Neon.vqaddq_s16 (vacc_2) ((p.output_zero_point).truncate 16)
  let vy_0 := SALT.Intrinsics.Neon.vqmovn_s16 (vacc_3)
  (vy_0)

/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : qs8vcvtParams)
    (loaded : List (BitVec 8)) (live : Nat) : List (BitVec 8) :=
  let vinput_zero_point_0 := List.replicate 8 ((p.input_zero_point).truncate 16)
  let vmultiplier_0 := List.replicate 8 (-(p.multiplier).truncate 16)
  let voutput_zero_point_0 := List.replicate 8 ((p.output_zero_point).truncate 16)
  let vx_1 := (loaded).take 8
  let vacc_4 := SALT.Intrinsics.Neon.vsubw_s8 (vinput_zero_point_0) (vx_1)
  let vacc_5 := SALT.Intrinsics.Neon.vshlq_n_s16 (vacc_4) (7)
  let vacc_6 := SALT.Intrinsics.Neon.vqrdmulhq_s16 (vacc_5) (vmultiplier_0)
  let vacc_7 := SALT.Intrinsics.Neon.vqaddq_s16 (vacc_6) ((p.output_zero_point).truncate 16)
  let vy_1 := SALT.Intrinsics.Neon.vqmovn_s16 (vacc_7)
  let call_0016 := vy_1
  let stored4 := if live.testBit 2 then (call_0016).take 4 else []
  let vy_2 := ((vy_1 ++ vy_1).drop 4).take 8
  let after4 := if live.testBit 2 then vy_2 else vy_1
  let call_0019 := after4
  let stored2 := if live.testBit 1 then (call_0019).take 2 else []
  let vy_3 := ((after4 ++ after4).drop 2).take 8
  let after2 := if live.testBit 1 then vy_3 else after4
  let stored1 := if live.testBit 0 then (after2).take 1 else []
  (stored4) ++ (stored2) ++ (stored1)

/-- Generated value-only lifting of the validated 8/4/2/1 control shape.

`overread` supplies the bytes physically loaded beyond a nonempty short tail.
This definition does not establish that those bytes are legally readable.
-/
def neonValueLoopWithOverreadFromIntrinsics (p : qs8vcvtParams)
    (input overread : List (BitVec 8)) : List (BitVec 8) :=
  SALT.Kernel.Schedule.runFixedChunkTail 8 (by decide)
    (neonBlock8FromIntrinsics p)
    (fun tail =>
      let loaded := (tail ++ overread).take 8
      neonPartialTailLivePrefixFromIntrinsics p loaded tail.length)
    input

/-- Zero-filled compatibility specialization of the explicit-overread model. -/
def neonValueLoopFromIntrinsics (p : qs8vcvtParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  neonValueLoopWithOverreadFromIntrinsics p input
    (List.replicate 7 (0 : BitVec 8))

def rvvChunkFromIntrinsics (p : qs8vcvtParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vx_0 := input
  let vx_w_0 := SALT.Intrinsics.RVV.vsext_vf2_i16 (vx_0)
  let vacc_0 := SALT.Intrinsics.RVV.vrsub_vx_i16 (vx_w_0) ((p.input_zero_point).truncate 16)
  let vacc_1 := SALT.Intrinsics.RVV.vsll_vx_i16 (vacc_0) (7)
  let prod_0 := SALT.Intrinsics.RVV.vwmul_vx_i32 (vacc_1) (((-p.multiplier)).truncate 16)
  let prod_1 := SALT.Intrinsics.RVV.vsll_vx_i32 (prod_0) (1)
  let vacc_2 := SALT.Intrinsics.RVV.vnclip_wx_i16_mode (prod_1) (16) (0)
  let vacc_3 := SALT.Intrinsics.RVV.vsadd_vx (vacc_2) ((p.output_zero_point).truncate 16)
  let vy_0 := SALT.Intrinsics.RVV.vnclip_wx_i8_mode (vacc_3) (0) (2)
  vy_0

/-- Generated value-only lifting of the validated RVV strip-mined loop.

A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.
-/
def rvvValueLoopFromIntrinsics (p : qs8vcvtParams)
    (input : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length) :
    List (BitVec 8) :=
  SALT.Kernel.Schedule.processBlocks (rvvChunkFromIntrinsics p) input schedule


/-- Scalar action independently projected from the parsed Neon block. -/
def fNeon (p : qs8vcvtParams) (x : BitVec 8) : BitVec 8 :=
  (neonBlock8FromIntrinsics p (List.replicate 8 x)).headD (0 : BitVec 8)

/-- Scalar action independently projected from the parsed RVV chunk. -/
def fRvv (p : qs8vcvtParams) (x : BitVec 8) : BitVec 8 :=
  (rvvChunkFromIntrinsics p [x]).headD (0 : BitVec 8)
end SALT.Corpus.qs8vcvt
