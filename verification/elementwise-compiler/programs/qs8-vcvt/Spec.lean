-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.qs8vcvt.Models

namespace SALT.Corpus.qs8vcvt

def manifestSha256InSpec : String := "0e087e9285d5654a263330d2c12c5890c90850c23283648d2a2e590a68c2cb15"
def modelsSha256InSpec : String := "6f7c09edbce6e63ad6dc5309d79dd61b97bbd8262b038d94108060843464a64a"
def sharedEntryContractSha256 : String := "d3451fad1964124247d8f6f7c65b8c38cb60dd2b873b45589dc153cba6644130"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : qs8vcvtParams) (input : List (BitVec 8)),
    input.length = 8 →
    neonBlock8FromIntrinsics p input = input.map (fNeon p)

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : qs8vcvtParams) (input : List (BitVec 8)),
    rvvChunkFromIntrinsics p input = input.map (fRvv p)

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : qs8vcvtParams) (x : BitVec 8), fNeon p x = fRvv p x

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : qs8vcvtParams) (input : List (BitVec 8))
    (overread0 : List (BitVec 8)),
    7 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 = input.map (fNeon p)

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : qs8vcvtParams) (input : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    rvvValueLoopFromIntrinsics p input schedule = input.map (fRvv p)

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : qs8vcvtParams) (input : List (BitVec 8))
    (overread0 : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    7 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 =
      rvvValueLoopFromIntrinsics p input schedule

end SALT.Corpus.qs8vcvt
