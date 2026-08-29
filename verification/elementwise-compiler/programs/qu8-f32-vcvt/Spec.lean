-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.qu8f32vcvt.Models

namespace SALT.Corpus.qu8f32vcvt

def manifestSha256InSpec : String := "ec18252625b26b03e34a3aabe7dc6d2b00d13b26297fea359974e330add71006"
def modelsSha256InSpec : String := "a29a0b210877dc71085f2a1bec9a681742313bfbf105c218986008913974f63e"
def sharedEntryContractSha256 : String := "d5e688ca1eeb2d70940f5f910cba36bee7c43f6c6da12c2fa80450d1e4b8102c"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : qu8f32vcvtParams) (input : List (BitVec 8)),
    input.length = 8 →
    neonBlock8FromIntrinsics p input = input.map (fNeon p)

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : qu8f32vcvtParams) (input : List (BitVec 8)),
    rvvChunkFromIntrinsics p input = input.map (fRvv p)

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : qu8f32vcvtParams) (x : BitVec 8), fNeon p x = fRvv p x

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : qu8f32vcvtParams) (input : List (BitVec 8))
    (overread0 : List (BitVec 8)),
    7 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 = input.map (fNeon p)

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : qu8f32vcvtParams) (input : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    rvvValueLoopFromIntrinsics p input schedule = input.map (fRvv p)

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : qu8f32vcvtParams) (input : List (BitVec 8))
    (overread0 : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    7 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 =
      rvvValueLoopFromIntrinsics p input schedule

end SALT.Corpus.qu8f32vcvt
