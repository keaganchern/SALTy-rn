-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.qs8f32vcvt.Models

namespace SALT.Corpus.qs8f32vcvt

def manifestSha256InSpec : String := "2ac3c160b9e294dbc642ff502c5114134768e23be42f7bd5512c5d48652288ee"
def modelsSha256InSpec : String := "6347a72fbe66f0354666698ad88889c6f0627706da892f04aa3ba10fd6b1ae4a"
def sharedEntryContractSha256 : String := "7ad05ee1382d87fedbda7050365ea4763d5926e3606f1e0f1fcaaadf94c46011"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : qs8f32vcvtParams) (input : List (BitVec 8)),
    input.length = 8 →
    neonBlock8FromIntrinsics p input = input.map (fNeon p)

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : qs8f32vcvtParams) (input : List (BitVec 8)),
    rvvChunkFromIntrinsics p input = input.map (fRvv p)

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : qs8f32vcvtParams) (x : BitVec 8), fNeon p x = fRvv p x

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : qs8f32vcvtParams) (input : List (BitVec 8))
    (overread0 : List (BitVec 8)),
    7 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 = input.map (fNeon p)

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : qs8f32vcvtParams) (input : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    rvvValueLoopFromIntrinsics p input schedule = input.map (fRvv p)

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : qs8f32vcvtParams) (input : List (BitVec 8))
    (overread0 : List (BitVec 8))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    7 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 =
      rvvValueLoopFromIntrinsics p input schedule

end SALT.Corpus.qs8f32vcvt
