import SALT.Corpus.f32vsub.Spec

namespace SALT.Corpus.f32vsub

def counterexampleParams : f32vsubParams := ({  } : f32vsubParams)
def counterexampleInput0 : List (BitVec 32) := [0]
def counterexampleInput1 : List (BitVec 32) := [2141192193]
def counterexampleOverread0 : List (BitVec 32) := List.replicate 3 0
def counterexampleOverread1 : List (BitVec 32) := List.replicate 3 0
def counterexampleSchedule :
    SALT.Kernel.Schedule.PositivePartition counterexampleInput0.length :=
  SALT.Kernel.Schedule.PositivePartition.singleton 1 (by decide)

example : ((neonValueLoopWithOverreadFromIntrinsics counterexampleParams counterexampleInput0 counterexampleInput1 counterexampleOverread0 counterexampleOverread1 (by decide : counterexampleInput0.length = counterexampleInput1.length)).headD 0).toNat = 2145386497 := by
  native_decide
example : ((rvvValueLoopFromIntrinsics counterexampleParams counterexampleInput0 counterexampleInput1 (by decide : counterexampleInput0.length = counterexampleInput1.length) counterexampleSchedule).headD 0).toNat = 2143289344 := by
  native_decide
theorem completeValueEquivalenceCounterexample : Not completeValueEquivalenceClaim := by
  intro claim
  have impossible := claim counterexampleParams counterexampleInput0 counterexampleInput1 counterexampleOverread0 counterexampleOverread1 (by decide : counterexampleInput0.length = counterexampleInput1.length) counterexampleSchedule (by decide)
  exact (by native_decide : neonValueLoopWithOverreadFromIntrinsics counterexampleParams counterexampleInput0 counterexampleInput1 counterexampleOverread0 counterexampleOverread1 (by decide : counterexampleInput0.length = counterexampleInput1.length) ≠ rvvValueLoopFromIntrinsics counterexampleParams counterexampleInput0 counterexampleInput1 (by decide : counterexampleInput0.length = counterexampleInput1.length) counterexampleSchedule) impossible

end SALT.Corpus.f32vsub
