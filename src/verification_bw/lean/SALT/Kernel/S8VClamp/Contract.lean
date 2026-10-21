import SALT.Generated.S8VClamp.Models

namespace SALT.Kernel.S8VClamp

open SALT.Generated.S8VClamp

/-- The effective signed-byte bounds consumed by both kernels are ordered.

The C parameter fields are converted to signed bytes before the vector min/max
operations. The value theorem therefore constrains the converted values rather
than the original 32-bit representations.
-/
def WellFormedParams (p : S8ClampParams) : Prop :=
  (p.min.truncate 8).toInt <= (p.max.truncate 8).toInt

end SALT.Kernel.S8VClamp
