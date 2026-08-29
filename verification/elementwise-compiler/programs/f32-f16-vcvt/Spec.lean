-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.f32f16vcvt.Models

namespace SALT.Corpus.f32f16vcvt

def manifestSha256InSpec : String := "7647eaa746ee3c581018299115152e121cf5ed7eb0856befff124468a53ba739"
def modelsSha256InSpec : String := "fe1271d24ca8531fb2d3ae45bd6c06c3ec25ccbe16115f0f810ebe28556a421a"
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
