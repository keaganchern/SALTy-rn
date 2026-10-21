-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.f32vsqrt.Models

namespace SALT.Corpus.f32vsqrt

def manifestSha256InSpec : String := "506ce7b4637f7ca28ad84fea7adfb88522b823ff6844a17fa43c48620c5cb830"
def modelsSha256InSpec : String := "39414291d3f1234a37f3cf5709b8b976b23aa81db96c0ebd5933c34c5542ea99"
def sharedEntryContractSha256 : String := "975d9a1465f41171800166191628db06656867d156777bfd7f02d7da40428d8d"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : f32vsqrtParams) (input : List (BitVec 32)),
    input.length = 4 →
    neonBlock4FromIntrinsics p input = input.map (fNeon p)

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : f32vsqrtParams) (input : List (BitVec 32)),
    rvvChunkFromIntrinsics p input = input.map (fRvv p)

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : f32vsqrtParams) (x : BitVec 32), fNeon p x = fRvv p x

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : f32vsqrtParams) (input : List (BitVec 32))
    (overread0 : List (BitVec 32)),
    3 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 = input.map (fNeon p)

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : f32vsqrtParams) (input : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    rvvValueLoopFromIntrinsics p input schedule = input.map (fRvv p)

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : f32vsqrtParams) (input : List (BitVec 32))
    (overread0 : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    3 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 =
      rvvValueLoopFromIntrinsics p input schedule

end SALT.Corpus.f32vsqrt
