-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.f32vrndne.Models

namespace SALT.Corpus.f32vrndne

def manifestSha256InSpec : String := "1e400595e17fa95616bc24804e6b96d50e99231069a4c671d1085c64b2493054"
def modelsSha256InSpec : String := "8b460b9f61e0598cf0f2e9bd9b7e47e760ca1a5b69bc39efeb4c235e8c28447d"
def sharedEntryContractSha256 : String := "975d9a1465f41171800166191628db06656867d156777bfd7f02d7da40428d8d"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : f32vrndneParams) (input : List (BitVec 32)),
    input.length = 4 →
    neonBlock4FromIntrinsics p input = input.map (fNeon p)

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : f32vrndneParams) (input : List (BitVec 32)),
    rvvChunkFromIntrinsics p input = input.map (fRvv p)

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : f32vrndneParams) (x : BitVec 32), fNeon p x = fRvv p x

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : f32vrndneParams) (input : List (BitVec 32))
    (overread0 : List (BitVec 32)),
    3 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 = input.map (fNeon p)

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : f32vrndneParams) (input : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    rvvValueLoopFromIntrinsics p input schedule = input.map (fRvv p)

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : f32vrndneParams) (input : List (BitVec 32))
    (overread0 : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    3 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 =
      rvvValueLoopFromIntrinsics p input schedule

end SALT.Corpus.f32vrndne
