import SALT.Corpus.f32vlrelu.Spec

namespace SALT.Corpus.f32vlrelu

def counterexampleParams : f32vlreluParams := ({ slope := (2141192193 : BitVec 32) } : f32vlreluParams)
def counterexampleInput0 : List (BitVec 32) := [2147483648]
def counterexampleOverread0 : List (BitVec 32) := List.replicate 3 0
def counterexampleSchedule :
    SALT.Kernel.Schedule.PositivePartition counterexampleInput0.length :=
  SALT.Kernel.Schedule.PositivePartition.singleton 1 (by decide)

example : ((neonValueLoopWithOverreadFromIntrinsics counterexampleParams counterexampleInput0 counterexampleOverread0).headD 0).toNat = 2145386497 := by
  native_decide
example : ((rvvValueLoopFromIntrinsics counterexampleParams counterexampleInput0 counterexampleSchedule).headD 0).toNat = 2143289344 := by
  native_decide
theorem completeValueEquivalenceCounterexample : Not completeValueEquivalenceClaim := by
  intro claim
  have impossible := claim counterexampleParams counterexampleInput0 counterexampleOverread0 counterexampleSchedule (by decide)
  exact (by native_decide : neonValueLoopWithOverreadFromIntrinsics counterexampleParams counterexampleInput0 counterexampleOverread0 ≠ rvvValueLoopFromIntrinsics counterexampleParams counterexampleInput0 counterexampleSchedule) impossible

end SALT.Corpus.f32vlrelu
