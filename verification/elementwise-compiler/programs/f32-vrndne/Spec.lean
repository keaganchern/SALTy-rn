-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.f32vrndne.Models

namespace SALT.Corpus.f32vrndne

def manifestSha256InSpec : String := "a05df807d0f8bf00ffe54a85ac3a0916d702228e319bb2025e10d94be14505e4"
def modelsSha256InSpec : String := "f59701e36c452db34bae4f8d779b05699595a9bf9af642fc207a937176122905"
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
