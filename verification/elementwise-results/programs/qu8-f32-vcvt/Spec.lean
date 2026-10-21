-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.qu8f32vcvt.Models

namespace SALT.Corpus.qu8f32vcvt

def manifestSha256InSpec : String := "0f6bee399ba4096f338305997faf543b55e5e4f35bab449c60938b925889cc8d"
def modelsSha256InSpec : String := "086b565d3aee9c8cbd5031d5ec66eaff01e7810757b42ff04bdad2f50788a1ce"
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
