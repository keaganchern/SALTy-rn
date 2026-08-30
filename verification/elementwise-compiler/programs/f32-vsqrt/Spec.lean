-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.f32vsqrt.Models

namespace SALT.Corpus.f32vsqrt

def manifestSha256InSpec : String := "0f7eaccba0cc25483ab6a3fb9df2eb1e8df5578be59093ae02a2ea40885e87bf"
def modelsSha256InSpec : String := "6d098c7e9b0b970024983b82e9a601dca094aad171e31b0c6f0e9d504352e147"
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
