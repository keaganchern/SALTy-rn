-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.qs8vmulminmaxfp32.Models

namespace SALT.Corpus.qs8vmulminmaxfp32

def manifestSha256InSpec : String := "b602d7a5556d81579a231638fa9bc509cc2556bdade79be098000fb875e98293"
def modelsSha256InSpec : String := "0b5b04d3f448a4296d95d99b62027a2c9e45fd2b9d9887de72f14d9684d79216"
def sharedEntryContractSha256 : String := "f4c1fb073c05d935abf44acc38855469baf021962e556ee32751bae19a50d1f0"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : qs8vmulminmaxfp32Params) (input_a input_b : List (BitVec 8)),
    input_a.length = 8 →
    input_a.length = input_b.length →
    neonBlock8FromIntrinsics p input_a input_b = List.zipWith (fNeon p) input_a input_b

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : qs8vmulminmaxfp32Params) (input_a input_b : List (BitVec 8)),
    input_a.length = input_b.length →
    rvvChunkFromIntrinsics p input_a input_b = List.zipWith (fRvv p) input_a input_b

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : qs8vmulminmaxfp32Params) (x y : BitVec 8), fNeon p x y = fRvv p x y

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : qs8vmulminmaxfp32Params) (input_a input_b : List (BitVec 8))
    (overread0 overread1 : List (BitVec 8))
    (sameLength : input_a.length = input_b.length),
    7 ≤ overread0.length ∧ 7 ≤ overread1.length →
    neonValueLoopWithOverreadFromIntrinsics p input_a input_b overread0 overread1 sameLength = List.zipWith (fNeon p) input_a input_b

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : qs8vmulminmaxfp32Params) (input_a input_b : List (BitVec 8))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length),
    rvvValueLoopFromIntrinsics p input_a input_b sameLength schedule = List.zipWith (fRvv p) input_a input_b

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : qs8vmulminmaxfp32Params) (input_a input_b : List (BitVec 8))
    (overread0 overread1 : List (BitVec 8))
    (sameLength : input_a.length = input_b.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input_a.length),
    7 ≤ overread0.length ∧ 7 ≤ overread1.length →
    neonValueLoopWithOverreadFromIntrinsics p input_a input_b overread0 overread1 sameLength =
      rvvValueLoopFromIntrinsics p input_a input_b sameLength schedule

end SALT.Corpus.qs8vmulminmaxfp32
