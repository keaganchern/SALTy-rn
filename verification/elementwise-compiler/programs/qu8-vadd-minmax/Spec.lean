-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.qu8vaddminmax.Models

namespace SALT.Corpus.qu8vaddminmax

def manifestSha256InSpec : String := "5b87af7efafd01e3cacadfc326ce92111c8f9757898ea42a03ca73c358bfceec"
def modelsSha256InSpec : String := "6796c3e424518747f1b4211e515b0e2010550f7f4a3a52aa5ce92685e2fe9595"
def sharedEntryContractSha256 : String := "2fd911f182e3dbecfc6a43a791044cd1ec6af4c8d2e1acdf1d76e62b9276d1d7"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : qu8vaddminmaxParams) (input_a input_b : List (BitVec 8)),
    input_a.length = 8 →
    input_a.length = input_b.length →
    neonBlock8FromIntrinsics p input_a input_b = List.zipWith (fNeon p) input_a input_b

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : qu8vaddminmaxParams) (input_a input_b : List (BitVec 8)),
    input_a.length = input_b.length →
    rvvChunkFromIntrinsics p input_a input_b = List.zipWith (fRvv p) input_a input_b

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : qu8vaddminmaxParams) (x y : BitVec 8), fNeon p x y = fRvv p x y

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : qu8vaddminmaxParams) (input_a input_b : List (BitVec 8))
    (overread0 overread1 : List (BitVec 8))
    (sameLength : input_a.length = input_b.length),
    7 ≤ overread0.length ∧ 7 ≤ overread1.length →
    neonValueLoopWithOverreadFromIntrinsics p input_a input_b overread0 overread1 sameLength = List.zipWith (fNeon p) input_a input_b

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : qu8vaddminmaxParams) (input_a input_b : List (BitVec 8))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length),
    rvvValueLoopFromIntrinsics p input_a input_b sameLength schedule = List.zipWith (fRvv p) input_a input_b

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : qu8vaddminmaxParams) (input_a input_b : List (BitVec 8))
    (overread0 overread1 : List (BitVec 8))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length),
    7 ≤ overread0.length ∧ 7 ≤ overread1.length →
    neonValueLoopWithOverreadFromIntrinsics p input_a input_b overread0 overread1 sameLength =
      rvvValueLoopFromIntrinsics p input_a input_b sameLength schedule

end SALT.Corpus.qu8vaddminmax
