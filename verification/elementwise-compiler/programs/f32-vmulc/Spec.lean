-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.f32vmulc.Models

namespace SALT.Corpus.f32vmulc

def manifestSha256InSpec : String := "1692d7ccfff9543490396d8b861901a344b5fdb174d0573c2cef6ca9ee71e0e2"
def modelsSha256InSpec : String := "91591e924b8771121772542b8448c90578639e6c6b70904871d7146ac467f1f9"
def sharedEntryContractSha256 : String := "0ab3df2574043ef4fe473603e05786fd7c7a4fbf40737a4daf45d2eaae32c08e"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : f32vmulcParams) (input_a : List (BitVec 32)),
    input_a.length = 4 →
    neonBlock4FromIntrinsics p input_a = input_a.map (fNeon p)

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : f32vmulcParams) (input_a : List (BitVec 32)),
    rvvChunkFromIntrinsics p input_a = input_a.map (fRvv p)

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : f32vmulcParams) (x : BitVec 32), fNeon p x = fRvv p x

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : f32vmulcParams) (input_a : List (BitVec 32))
    (overread0 : List (BitVec 32)),
    3 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input_a overread0 = input_a.map (fNeon p)

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : f32vmulcParams) (input_a : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length),
    rvvValueLoopFromIntrinsics p input_a schedule = input_a.map (fRvv p)

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : f32vmulcParams) (input_a : List (BitVec 32))
    (overread0 : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length),
    3 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input_a overread0 =
      rvvValueLoopFromIntrinsics p input_a schedule

end SALT.Corpus.f32vmulc
