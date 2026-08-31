-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.qs8vaddminmax.Models

namespace SALT.Corpus.qs8vaddminmax

def manifestSha256InSpec : String := "6ca35dfdb06a8329cb2a1b8985ce9f2ea803787b82ba014631ec621d25925963"
def modelsSha256InSpec : String := "d3351385ab855dda9de1205b4706df018df2a7a0d9bd8185a76eccbcf610ee33"
def sharedEntryContractSha256 : String := "f4c1fb073c05d935abf44acc38855469baf021962e556ee32751bae19a50d1f0"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : qs8vaddminmaxParams) (input_a input_b : List (BitVec 8)),
    input_a.length = 16 →
    input_a.length = input_b.length →
    neonBlock16FromIntrinsics p input_a input_b = List.zipWith (fNeon p) input_a input_b

def neonSecondaryBlockEqualsMapClaim : Prop :=
  ∀ (p : qs8vaddminmaxParams) (input_a input_b : List (BitVec 8)),
    input_a.length = 8 →
    input_a.length = input_b.length →
    neonBlock8FromIntrinsics p input_a input_b = List.zipWith (fNeonSecondary p) input_a input_b

def neonPhaseFunctionsEqualClaim : Prop :=
  ∀ (p : qs8vaddminmaxParams) (x y : BitVec 8),
    fNeon p x y = fNeonSecondary p x y

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : qs8vaddminmaxParams) (input_a input_b : List (BitVec 8)),
    input_a.length = input_b.length →
    rvvChunkFromIntrinsics p input_a input_b = List.zipWith (fRvv p) input_a input_b

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : qs8vaddminmaxParams) (x y : BitVec 8), fNeon p x y = fRvv p x y

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : qs8vaddminmaxParams) (input_a input_b : List (BitVec 8))
    (overread0 overread1 : List (BitVec 8))
    (sameLength : input_a.length = input_b.length),
    7 ≤ overread0.length ∧ 7 ≤ overread1.length →
    neonValueLoopWithOverreadFromIntrinsics p input_a input_b overread0 overread1 sameLength = List.zipWith (fNeon p) input_a input_b

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : qs8vaddminmaxParams) (input_a input_b : List (BitVec 8))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length),
    rvvValueLoopFromIntrinsics p input_a input_b sameLength schedule = List.zipWith (fRvv p) input_a input_b

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : qs8vaddminmaxParams) (input_a input_b : List (BitVec 8))
    (overread0 overread1 : List (BitVec 8))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length),
    7 ≤ overread0.length ∧ 7 ≤ overread1.length →
    neonValueLoopWithOverreadFromIntrinsics p input_a input_b overread0 overread1 sameLength =
      rvvValueLoopFromIntrinsics p input_a input_b sameLength schedule

end SALT.Corpus.qs8vaddminmax
