-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.f32vmax.Models

namespace SALT.Corpus.f32vmax

def manifestSha256InSpec : String := "cf37284ee93f0195ce97e044aa651550043dd41aadf57368623a98e94099486d"
def modelsSha256InSpec : String := "4ee5242fcef6f02d0855e2e797ee9198fd6ec08f13815699fa92ffb0ce8f6406"
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
