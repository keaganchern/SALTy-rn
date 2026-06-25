/- Deterministic LCG for the differential harness: pure, reproducible per
   seed, and wide enough to span `BitVec 32`. Not cryptographic. -/

namespace SALT.Test.Rand

/-- LCG state = a 64-bit seed, iterated by `seed ↦ a·seed + c (mod 2^64)`. -/
structure Gen where
  seed : UInt64
  deriving Repr

/-- Numerical Recipes constants (Knuth's preferred MMIX). -/
def step (g : Gen) : Gen :=
  { seed := g.seed * 6364136223846793005 + 1442695040888963407 }

/-- Advance the generator and return the next 32 bits of its state. -/
def nextU32 (g : Gen) : UInt32 × Gen :=
  let g' := step g
  -- top 32 bits give better uniformity
  let u32 : UInt32 := (g'.seed >>> 32).toUInt32
  (u32, g')

/-- Sample a `BitVec w` uniformly by drawing 32 bits at a time and composing. -/
def nextBitVec (g : Gen) (w : Nat) : BitVec w × Gen :=
  go g w 0
where
  go (g : Gen) (remaining : Nat) (acc : Nat) : BitVec w × Gen :=
    match remaining with
    | 0 => (BitVec.ofNat w acc, g)
    | Nat.succ k =>
      let (chunk, g') := nextU32 g
      let take := Nat.min (Nat.succ k) 32
      let mask : Nat := if take = 32 then 0xFFFFFFFF else (1 <<< take) - 1
      let acc' := (acc <<< take) ||| (chunk.toNat &&& mask)
      have htake : take ≥ 1 := by
        simp only [take, Nat.min_def]
        split <;> omega
      go g' (Nat.succ k - take) acc'
  termination_by remaining
  decreasing_by
    simp_wf
    have h1 : Nat.min (Nat.succ k) 32 ≥ 1 := by
      rcases Nat.lt_or_ge (Nat.succ k) 32 with h | h
      · simp [Nat.min_eq_left (Nat.le_of_lt h)]
      · simp [Nat.min_eq_right h]
    exact Nat.sub_lt (Nat.succ_pos k) h1

/-- Sample a `Nat` in `[0, upper)`. Uses the low 32 bits of one draw. -/
def nextNatLt (g : Gen) (upper : Nat) : Nat × Gen :=
  if upper = 0 then (0, g)
  else
    let (u, g') := nextU32 g
    (u.toNat % upper, g')

/-- Sample a `Nat` in `[lo, hi]` (inclusive on both ends, `lo ≤ hi`). -/
def nextNatInRange (g : Gen) (lo hi : Nat) : Nat × Gen :=
  let (k, g') := nextNatLt g (hi + 1 - lo)
  (lo + k, g')

/-- Initialise a generator from a seed. A zero seed is valid. -/
def mk (seed : UInt64) : Gen := { seed }

end SALT.Test.Rand
