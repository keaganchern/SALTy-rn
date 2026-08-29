-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.f32vsqrt.Models

namespace SALT.Corpus.f32vsqrt

def manifestSha256InSpec : String := "5b3d9938a12592e445971dcc0d6a2e44cc657b5214c277276c98b634065c1839"
def modelsSha256InSpec : String := "6fe4b19fd2f2e076c5758073c96906643aacecb105f98e6b55e7661d1228eaf2"
def sharedEntryContractSha256 : String := "975d9a1465f41171800166191628db06656867d156777bfd7f02d7da40428d8d"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : f32vsqrtParams) (input : List (BitVec 32)),
    input.length = 4 →
    neonBlock4FromIntrinsics p input = input.map (fNeon p)

def rvvChunkEqualsMapClaim : Prop :=
  ∀ (p : f32vsqrtParams) (input : List (BitVec 32)),
    rvvChunkFromIntrinsics p input = input.map (fRvv p)

def elementFunctionsEqualClaim : Prop :=
  ∀ (p : f32vsqrtParams) (x : BitVec 32), fNeon p x = fRvv p x

def neonLoopEqualsMapClaim : Prop :=
  ∀ (p : f32vsqrtParams) (input : List (BitVec 32))
    (overread0 : List (BitVec 32)),
    3 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 = input.map (fNeon p)

def rvvLoopEqualsMapClaim : Prop :=
  ∀ (p : f32vsqrtParams) (input : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    rvvValueLoopFromIntrinsics p input schedule = input.map (fRvv p)

def completeValueEquivalenceClaim : Prop :=
  ∀ (p : f32vsqrtParams) (input : List (BitVec 32))
    (overread0 : List (BitVec 32))
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length),
    3 ≤ overread0.length →
    neonValueLoopWithOverreadFromIntrinsics p input overread0 =
      rvvValueLoopFromIntrinsics p input schedule

end SALT.Corpus.f32vsqrt
