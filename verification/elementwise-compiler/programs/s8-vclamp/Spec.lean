-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.s8vclamp.Models

namespace SALT.Corpus.s8vclamp

def manifestSha256InSpec : String := "04e6e93a8da52863b8a0f336ffdff4d6d466c93c077dc37d997652f4162595f8"
def modelsSha256InSpec : String := "0089ef8332cf40e76f53f91ffe87549f9109ab7f9a6c2db4ec504159e5c80c37"
def sharedEntryContractSha256 : String := "d3451fad1964124247d8f6f7c65b8c38cb60dd2b873b45589dc153cba6644130"
def externalConditionSha256InSpec : String := "490a7cade552bd3a2d41e3e0ad1a0c87bac72e4f266d03998c2c973ea3531104"

/-- Candidate only: this is not available to proofs while evidence is unresolved. -/
def candidateExternalCondition (p : s8vclampParams) : Prop :=
  ((p.min).toInt ≤ (p.max).toInt)

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : s8vclampParams) (input : List (BitVec 8)),
    input.length = 64 →
    neonBlock64FromIntrinsics p input = input.map (fNeon p)

def neonSecondaryBlockEqualsMapClaim : Prop :=
  ∀ (p : s8vclampParams) (input : List (BitVec 8)),
    input.length = 8 →
    neonBlock8FromIntrinsics p input = input.map (fNeonSecondary p)

def neonPhaseFunctionsEqualClaim : Prop :=
  ∀ (p : s8vclampParams) (x : BitVec 8),
    fNeon p x = fNeonSecondary p x

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : s8vclampParams) (input : List (BitVec 8)),
    rvvChunkFromIntrinsics p input = input.map (fRvv p)

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : s8vclampParams) (x : BitVec 8), fNeon p x = fRvv p x

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : s8vclampParams) (input : List (BitVec 8))
    (overread0 : List (BitVec 8)),
    7 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 = input.map (fNeon p)

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : s8vclampParams) (input : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    rvvValueLoopFromIntrinsics p input schedule = input.map (fRvv p)

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : s8vclampParams) (input : List (BitVec 8))
    (overread0 : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    7 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 =
      rvvValueLoopFromIntrinsics p input schedule

/-- Diagnostic theorem shape; not selected until ExternalCondition is resolved. -/
def completeValueEquivalenceUnderCandidateConditionClaim : Prop :=
  ∀ (p : s8vclampParams) (input : List (BitVec 8))
    (overread0 : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    candidateExternalCondition p →
    7 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 =
      rvvValueLoopFromIntrinsics p input schedule

end SALT.Corpus.s8vclamp
