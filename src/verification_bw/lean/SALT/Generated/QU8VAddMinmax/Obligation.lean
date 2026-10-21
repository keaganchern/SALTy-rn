import SALT.Generated.QU8VAddMinmax.Models
import SALT.Kernel.QU8VAddMinmax.Contract

namespace SALT.Generated.QU8VAddMinmax

open SALT.Kernel.QU8VAddMinmax

/-- Protected arbitrary-length value claim for the generated QU8 VAdd Minmax models.

This claim does not establish C-memory validity, legal Neon overread, or RVV ISA
schedule adequacy. -/
def allLengthsValueEqualWithOverreadClaim
    (p : QU8AddMinmaxParams)
    (_hwf : WellFormedParams p)
    (inputA inputB overreadA overreadB : List (BitVec 8))
    (sameLength : inputA.length = inputB.length)
    (_hOverreadA : 7 <= overreadA.length)
    (_hOverreadB : 7 <= overreadB.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition inputA.length) : Prop :=
  neonValueLoopWithOverreadFromIntrinsics p inputA inputB overreadA overreadB
      sameLength =
    rvvValueLoopFromIntrinsics p inputA inputB sameLength schedule

end SALT.Generated.QU8VAddMinmax
