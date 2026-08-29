-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.f32vadd.Models

namespace SALT.Corpus.f32vadd

def manifestSha256InSpec : String := "5fa99c082f77b0769fa1539c27ecc13aa577ea17236b5ab3b9cd42813ee1d106"
def modelsSha256InSpec : String := "f5fcd1bcfaa2ef21fdb6c6427a4e094573625870fede61a39d9a6565377735a0"
def sharedEntryContractSha256 : String := "0ab3df2574043ef4fe473603e05786fd7c7a4fbf40737a4daf45d2eaae32c08e"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : f32vaddParams) (input_a input_b : List (BitVec 32)),
    input_a.length = 4 →
    input_a.length = input_b.length →
    neonBlock4FromIntrinsics p input_a input_b = List.zipWith (fNeon p) input_a input_b

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : f32vaddParams) (input_a input_b : List (BitVec 32)),
    input_a.length = input_b.length →
    rvvChunkFromIntrinsics p input_a input_b = List.zipWith (fRvv p) input_a input_b

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : f32vaddParams) (x y : BitVec 32), fNeon p x y = fRvv p x y

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : f32vaddParams) (input_a input_b : List (BitVec 32))
    (overread0 overread1 : List (BitVec 32))
    (sameLength : input_a.length = input_b.length),
    3 ≤ overread0.length ∧ 3 ≤ overread1.length →
    neonValueLoopWithOverreadFromIntrinsics p input_a input_b overread0 overread1 sameLength = List.zipWith (fNeon p) input_a input_b

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : f32vaddParams) (input_a input_b : List (BitVec 32))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length),
    rvvValueLoopFromIntrinsics p input_a input_b sameLength schedule = List.zipWith (fRvv p) input_a input_b

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : f32vaddParams) (input_a input_b : List (BitVec 32))
    (overread0 overread1 : List (BitVec 32))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length),
    3 ≤ overread0.length ∧ 3 ≤ overread1.length →
    neonValueLoopWithOverreadFromIntrinsics p input_a input_b overread0 overread1 sameLength =
      rvvValueLoopFromIntrinsics p input_a input_b sameLength schedule

end SALT.Corpus.f32vadd
