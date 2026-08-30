-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.qs8f32vcvt.Models

namespace SALT.Corpus.qs8f32vcvt

def manifestSha256InSpec : String := "c3d6e9ad61ad147462df3101a7deb1a27164ff4df412d3055dc85aa1aa19d32c"
def modelsSha256InSpec : String := "7734e486198859ec602ae4aacf976919e299180627008b6e1937b138d1280e15"
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
