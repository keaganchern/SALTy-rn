-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.qs8vlrelu.Models

namespace SALT.Corpus.qs8vlrelu

def manifestSha256InSpec : String := "c85a9c943ccfd52e3ac2818d4aa082a04a8ea673494de71c72105a0840f1f490"
def modelsSha256InSpec : String := "8aced392b7534b17fd9bd3dd71a571be4dec43bf3aeab7ad4420fc1d394007b0"
def sharedEntryContractSha256 : String := "d3451fad1964124247d8f6f7c65b8c38cb60dd2b873b45589dc153cba6644130"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : qs8vlreluParams) (input : List (BitVec 8)),
    input.length = 8 →
    neonBlock8FromIntrinsics p input = input.map (fNeon p)

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : qs8vlreluParams) (input : List (BitVec 8)),
    rvvChunkFromIntrinsics p input = input.map (fRvv p)

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : qs8vlreluParams) (x : BitVec 8), fNeon p x = fRvv p x

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : qs8vlreluParams) (input : List (BitVec 8))
    (overread0 : List (BitVec 8)),
    7 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 = input.map (fNeon p)

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : qs8vlreluParams) (input : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    rvvValueLoopFromIntrinsics p input schedule = input.map (fRvv p)

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : qs8vlreluParams) (input : List (BitVec 8))
    (overread0 : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    7 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 =
      rvvValueLoopFromIntrinsics p input schedule

end SALT.Corpus.qs8vlrelu
