/- Shadow implementations for the differential harness: each mirrors a
   CoreOp primitive via an independent `Int`-arithmetic path so divergence
   exposes inconsistent edits. Not load-bearing for any proof. -/
import SALT.Basic

namespace SALT.Test.Ref

open SALT

/-- ARM VRSHL.S<w> with positive shift: widen, add `1 <<< (n-1)`, ashr,
    truncate. Expressed via floor division on `Int`. -/
def neonRoundingShiftRightRef {w : Nat} (x : BitVec w) (shift : Nat) : BitVec w :=
  if shift = 0 then x
  else
    let xi : Int := x.toInt
    let round_const : Int := Int.ofNat (1 <<< (shift - 1))
    let divisor : Int := Int.ofNat (1 <<< shift)
    BitVec.ofInt w (Int.fdiv (xi + round_const) divisor)

/-- VSSRA.VX at vxrm=RNU: ashr, then +1 if the highest shifted-out bit
    was set. Expressed via floor division and an explicit round-bit
    extraction. -/
def rvvRoundingShiftRightRef {w : Nat} (x : BitVec w) (shift : Nat) : BitVec w :=
  if shift = 0 then x
  else
    let xi : Int := x.toInt
    let divisor : Int := Int.ofNat (1 <<< shift)
    let floor_q : Int := Int.fdiv xi divisor
    let half_divisor : Int := Int.ofNat (1 <<< (shift - 1))
    let round_bit : Int := (Int.fdiv xi half_divisor).emod 2
    BitVec.ofInt w (floor_q + round_bit)

/-- Signed saturating add via `Int` clamp. -/
def signedSatAddRef {w : Nat} (a b : BitVec w) : BitVec w :=
  if w = 0 then a
  else
    let sum : Int := a.toInt + b.toInt
    let hi : Int := Int.ofNat (2 ^ (w - 1)) - 1
    let lo : Int := -(Int.ofNat (2 ^ (w - 1)))
    BitVec.ofInt w (if sum > hi then hi else if sum < lo then lo else sum)

/-- Signed saturating narrow via `Int` clamp to `[-2^(w'-1), 2^(w'-1)-1]`. -/
def signedClampRef {w w' : Nat} (x : BitVec w) : BitVec w' :=
  if w' = 0 then 0
  else
    let xi : Int := x.toInt
    let hi : Int := Int.ofNat (2 ^ (w' - 1)) - 1
    let lo : Int := -(Int.ofNat (2 ^ (w' - 1)))
    BitVec.ofInt w' (if xi > hi then hi else if xi < lo then lo else xi)

end SALT.Test.Ref
