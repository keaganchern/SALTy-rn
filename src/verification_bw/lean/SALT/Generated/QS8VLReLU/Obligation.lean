import SALT.Generated.QS8VLReLU.Models
import SALT.Kernel.QS8VLReLU.Contract

namespace SALT.Generated.QS8VLReLU

open SALT.Kernel.QS8VLReLU

/-- Protected arbitrary-length value claim for the generated QS8 LReLU models.

This claim does not establish C-memory validity, legal Neon overread, or RVV ISA
schedule adequacy. -/
def allLengthsValueEqualWithOverreadClaim
    (p : QS8LReLUParams)
    (_hwf : WellFormedParams p)
    (input overread : List (BitVec 8))
    (_hOverread : 7 <= overread.length)
    (schedule : SALT.Kernel.Schedule.PositivePartition input.length) : Prop :=
  neonValueLoopWithOverreadFromIntrinsics p input overread =
    rvvValueLoopFromIntrinsics p input schedule

end SALT.Generated.QS8VLReLU
