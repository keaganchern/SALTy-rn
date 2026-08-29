-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.f32f16vcvt.Models

namespace SALT.Corpus.f32f16vcvt

def manifestSha256InSpec : String := "16e7bc8cfd91a507d1512915c774d25d49ae12be57f110178686ac9ffd094906"
def modelsSha256InSpec : String := "aa22ab129eccc75a6abdb59d6c156da4a8249759af9e53406931cda3ada4f5ca"
def sharedEntryContractSha256 : String := "351ba38119185f21a3382e2df12ed4c3f903ac0830b606ab06bf119670ef8d2c"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : f32f16vcvtParams) (input : List (BitVec 32)),
    input.length = 8 →
    neonBlock8FromIntrinsics p input = input.map (fNeon p)

def neonSecondaryBlockEqualsMapClaim : Prop :=
  ∀ (p : f32f16vcvtParams) (input : List (BitVec 32)),
    input.length = 4 →
    neonBlock4FromIntrinsics p input = input.map (fNeonSecondary p)

def neonPhaseFunctionsEqualClaim : Prop :=
  ∀ (p : f32f16vcvtParams) (x : BitVec 32),
    fNeon p x = fNeonSecondary p x

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : f32f16vcvtParams) (input : List (BitVec 32)),
    rvvChunkFromIntrinsics p input = input.map (fRvv p)

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : f32f16vcvtParams) (x : BitVec 32), fNeon p x = fRvv p x

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : f32f16vcvtParams) (input : List (BitVec 32))
    (overread0 : List (BitVec 32)),
    3 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 = input.map (fNeon p)

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : f32f16vcvtParams) (input : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    rvvValueLoopFromIntrinsics p input schedule = input.map (fRvv p)

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : f32f16vcvtParams) (input : List (BitVec 32))
    (overread0 : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    3 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 =
      rvvValueLoopFromIntrinsics p input schedule

end SALT.Corpus.f32f16vcvt
