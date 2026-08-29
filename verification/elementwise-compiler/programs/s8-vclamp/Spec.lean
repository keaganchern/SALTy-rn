-- This file is generated and proof-free. Proof search must not edit it.
import SALT.Corpus.s8vclamp.Models

namespace SALT.Corpus.s8vclamp

def manifestSha256InSpec : String := "f76fd1f9b2838348f46c922a84e011306a3f0465843d1a305bfad5cc77571e9d"
def modelsSha256InSpec : String := "0a58329b012687edc365fb94c2339c825e6dd21bab9ba789032a8688ed41decb"
def sharedEntryContractSha256 : String := "d3451fad1964124247d8f6f7c65b8c38cb60dd2b873b45589dc153cba6644130"

def neonBlockEqualsMapClaim : Prop :=
  ∀ (p : s8vclampParams) (input : List (BitVec 8)),
    input.length = 64 →
    neonBlock64FromIntrinsics p input = input.map (fNeon p)

def neonSecondaryBlockEqualsMapClaim : Prop :=
  ∀ (p : s8vclampParams) (input : List (BitVec 8)),
    input.length = 8 →
    neonBlock8FromIntrinsics p input = input.map (fNeon p)

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

end SALT.Corpus.s8vclamp
