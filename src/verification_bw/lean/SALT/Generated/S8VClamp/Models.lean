-- This file is generated. Do not edit the models by hand.
import SALT.Intrinsics.Neon
import SALT.Intrinsics.RVV
import SALT.Kernel.Schedule

namespace SALT.Generated.S8VClamp

def neonSourceSha256 : String :=
  "4edb4d3c7d185bb0c969664c7408e7161b01a7d0f52cc651d2919c9d9e6bda7f"
def rvvSourceSha256 : String :=
  "109360a580298b5e412f3808356668b6511f40b5c9441967c2f060a03fc2ea4e"
def neonPreprocessedSha256 : String :=
  "0d64cd20afd30e11c70ba814b1f936eae6a91bbc691c8e577e4a088da3a2bf3c"
def rvvPreprocessedSha256 : String :=
  "4d33ed4acc9e139ec5efc58d2aafa22c6bb3b0c9e2f18afaa531b3a2228c7a65"
def parseFacadeSha256 : String :=
  "4634c40f29c8b24bf6a032a0d91e273f050111ff2db230a2c24358ef0a101da0"
def registrySha256 : String :=
  "dd7fde5214bde0ca34f9b9679644ee5c7d5cc33d9a5d40616fa45e9911dd08e6"

structure S8ClampParams where
  min : BitVec 32
  max : BitVec 32
  deriving Repr, DecidableEq

def neonBlock64FromIntrinsics (p : S8ClampParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let voutput_max_0 := List.replicate 16 ((p.max).truncate 8)
  let voutput_min_0 := List.replicate 16 ((p.min).truncate 8)
  let vacc0_0 := (input).take 16
  let vacc1_0 := ((input).drop 16).take 16
  let vacc2_0 := ((input).drop 32).take 16
  let vacc3_0 := ((input).drop 48).take 16
  let vacc0_1 := SALT.Intrinsics.Neon.vmaxq_s8 (vacc0_0) (voutput_min_0)
  let vacc1_1 := SALT.Intrinsics.Neon.vmaxq_s8 (vacc1_0) (voutput_min_0)
  let vacc2_1 := SALT.Intrinsics.Neon.vmaxq_s8 (vacc2_0) (voutput_min_0)
  let vacc3_1 := SALT.Intrinsics.Neon.vmaxq_s8 (vacc3_0) (voutput_min_0)
  let vacc0_2 := SALT.Intrinsics.Neon.vminq_s8 (vacc0_1) (voutput_max_0)
  let vacc1_2 := SALT.Intrinsics.Neon.vminq_s8 (vacc1_1) (voutput_max_0)
  let vacc2_2 := SALT.Intrinsics.Neon.vminq_s8 (vacc2_1) (voutput_max_0)
  let vacc3_2 := SALT.Intrinsics.Neon.vminq_s8 (vacc3_1) (voutput_max_0)
  (vacc0_2) ++ (vacc1_2) ++ (vacc2_2) ++ (vacc3_2)

/-- Generated value model of the source's reversed-order 8-lane block. -/
def neonBlock8FromIntrinsics (p : S8ClampParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vacc_0 := (input).take 8
  let call_0019 := (List.replicate 16 ((p.max).truncate 8)).take 8
  let vacc_1 := SALT.Intrinsics.Neon.vmin_s8_vec (vacc_0) (call_0019)
  let call_0021 := (List.replicate 16 ((p.min).truncate 8)).take 8
  let vacc_2 := SALT.Intrinsics.Neon.vmax_s8_vec (vacc_1) (call_0021)
  vacc_2

/-- Generated little-endian live-prefix value abstraction for the 4/2/1 stores.

This definition does not establish C memory, alignment, aliasing, or endian adequacy.
-/
def neonPartialTailLivePrefixFromIntrinsics (p : S8ClampParams)
    (loaded : List (BitVec 8)) (live : Nat) : List (BitVec 8) :=
  let vacc_3 := (loaded).take 8
  let call_0025 := (List.replicate 16 ((p.max).truncate 8)).take 8
  let vacc_4 := SALT.Intrinsics.Neon.vmin_s8_vec (vacc_3) (call_0025)
  let call_0027 := (List.replicate 16 ((p.min).truncate 8)).take 8
  let vacc_5 := SALT.Intrinsics.Neon.vmax_s8_vec (vacc_4) (call_0027)
  let call_0029 := vacc_5
  let stored4 := if live.testBit 2 then (call_0029).take 4 else []
  let vacc_6 := ((vacc_5 ++ vacc_5).drop 4).take 8
  let after4 := if live.testBit 2 then vacc_6 else vacc_5
  let call_0032 := after4
  let stored2 := if live.testBit 1 then (call_0032).take 2 else []
  let vacc_7 := ((after4 ++ after4).drop 2).take 8
  let after2 := if live.testBit 1 then vacc_7 else after4
  let stored1 := if live.testBit 0 then (after2).take 1 else []
  (stored4) ++ (stored2) ++ (stored1)

/-- Generated value-only lifting of the validated 64/8/4/2/1 control shape.

`overread` supplies the bytes physically loaded beyond a nonempty short tail.
This definition does not establish that those bytes are legally readable.
-/
def neonValueLoopWithOverreadFromIntrinsics (p : S8ClampParams)
    (input overread : List (BitVec 8)) : List (BitVec 8) :=
  SALT.Kernel.Schedule.runFixedChunkTail 64 (by decide)
    (neonBlock64FromIntrinsics p)
    (SALT.Kernel.Schedule.runFixedChunkTail 8 (by decide)
      (neonBlock8FromIntrinsics p)
      (fun tail =>
        let loaded := (tail ++ overread).take 8
        neonPartialTailLivePrefixFromIntrinsics p loaded tail.length))
    input

/-- Zero-filled compatibility specialization of the arbitrary-overread model. -/
def neonValueLoopFromIntrinsics (p : S8ClampParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  neonValueLoopWithOverreadFromIntrinsics p input
    (List.replicate 7 (0 : BitVec 8))

def rvvChunkFromIntrinsics (p : S8ClampParams)
    (input : List (BitVec 8)) : List (BitVec 8) :=
  let vacc_0 := input
  let vacc_1 := SALT.Intrinsics.RVV.vmax_vx (vacc_0) ((p.min).truncate 8)
  let vacc_2 := SALT.Intrinsics.RVV.vmin_vx (vacc_1) ((p.max).truncate 8)
  vacc_2

end SALT.Generated.S8VClamp
