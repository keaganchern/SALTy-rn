-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.f32vmax.Models

namespace SALT.Corpus.f32vmax

def manifestSha256InSpec : String := "ae6ed0c051aa93ddfaea5a3aab217f6b20fab06bfcf1fbbe1788d90dd6c3f342"
def modelsSha256InSpec : String := "7ea10babd1d99233adb696763e5765cbdcc5592fe001b1ee8be1bf3403f86e2f"
def sharedEntryContractSha256 : String := "0ab3df2574043ef4fe473603e05786fd7c7a4fbf40737a4daf45d2eaae32c08e"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : f32vmaxParams) (input_a input_b : List (BitVec 32)),
    input_a.length = 4 →
    input_a.length = input_b.length →
    neonBlock4FromIntrinsics p input_a input_b = List.zipWith (fNeon p) input_a input_b

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : f32vmaxParams) (input_a input_b : List (BitVec 32)),
    input_a.length = input_b.length →
    rvvChunkFromIntrinsics p input_a input_b = List.zipWith (fRvv p) input_a input_b

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : f32vmaxParams) (x y : BitVec 32), fNeon p x y = fRvv p x y

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : f32vmaxParams) (input_a input_b : List (BitVec 32))
    (overread0 overread1 : List (BitVec 32))
    (sameLength : input_a.length = input_b.length),
    3 ≤ overread0.length ∧ 3 ≤ overread1.length →
    neonValueLoopWithOverreadFromIntrinsics p input_a input_b overread0 overread1 sameLength = List.zipWith (fNeon p) input_a input_b

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : f32vmaxParams) (input_a input_b : List (BitVec 32))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length),
    rvvValueLoopFromIntrinsics p input_a input_b sameLength schedule = List.zipWith (fRvv p) input_a input_b

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : f32vmaxParams) (input_a input_b : List (BitVec 32))
    (overread0 overread1 : List (BitVec 32))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length),
    3 ≤ overread0.length ∧ 3 ≤ overread1.length →
    neonValueLoopWithOverreadFromIntrinsics p input_a input_b overread0 overread1 sameLength =
      rvvValueLoopFromIntrinsics p input_a input_b sameLength schedule

end SALT.Corpus.f32vmax
