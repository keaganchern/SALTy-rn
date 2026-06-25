/- Differential harness: random-sample audit of CoreOp ops against Int shadow
   implementations and cross-ISA equalities. -/
import SALT.Core.CoreOp
import SALT.Core.CrossISA
import SALT.Test.Rand
import SALT.Test.Ref
import SALT.FP.Basic

namespace SALT.Test.Differential

open SALT
open SALT.Core
open SALT.Test

/-- Cap on failure records per check; further failures are elided. -/
def maxFailuresPerCheck : Nat := 10

/-- ⌊2^64 · (φ - 1)⌋, mixed into the per-check sub-seed so checks never
    observe the same random sequence. -/
def subseedMixer : UInt64 := 0x9E3779B97F4A7C15

structure Failure where
  check : String
  input : String
  expected : String
  actual : String
  deriving Repr

structure CheckResult where
  name : String
  samples : Nat
  failures : List Failure
  deriving Repr

abbrev Check := (seed : UInt64) → (samples : Nat) → CheckResult

/-- Run one check: `samples` random draws plus explicit `edgeCases`. The
    `describe` thunk runs only when a sample diverges. -/
def runCheck {σ α : Type} [BEq α] [ToString α]
    (name : String)
    (sampler : Rand.Gen → σ × Rand.Gen)
    (describe : σ → String)
    (expected actual : σ → α)
    (edgeCases : List σ := []) : Check := fun seed samples =>
  let edgeFails := edgeCases.foldl record []
  let randomFails := loop (Rand.mk seed) samples edgeFails
  { name, samples := samples + edgeCases.length, failures := randomFails }
where
  record (fails : List Failure) (s : σ) : List Failure :=
    let exp := expected s
    let act := actual s
    if exp == act then fails
    else
      if fails.length ≥ maxFailuresPerCheck then fails
      else Failure.mk name (describe s) (toString exp) (toString act) :: fails
  loop (g : Rand.Gen) (n : Nat) (fails : List Failure) : List Failure :=
    match n with
    | 0 => fails
    | Nat.succ k =>
      if fails.length ≥ maxFailuresPerCheck then fails
      else
        let (s, g') := sampler g
        loop g' k (record fails s)

-- Sampler helpers

/-- 32-bit value × shift in `[0, 31]`. Shared by both rounding-shift checks. -/
def sampleBV32ShiftLE31 (g : Rand.Gen) : (BitVec 32 × Nat) × Rand.Gen :=
  let (x, g') := Rand.nextBitVec g 32
  let (shift, g'') := Rand.nextNatInRange g' 0 31
  ((x, shift), g'')

def sampleTwoBV32 (g : Rand.Gen) : (BitVec 32 × BitVec 32) × Rand.Gen :=
  let (a, g') := Rand.nextBitVec g 32
  let (b, g'') := Rand.nextBitVec g' 32
  ((a, b), g'')

def sampleBV (w : Nat) (g : Rand.Gen) : BitVec w × Rand.Gen :=
  Rand.nextBitVec g w

/-- `BitVec 32` sample that resamples past NaN bit-patterns (their reinterpret
    round-trip is unspecified). Bounded retry budget. -/
def sampleNonNanBits (g : Rand.Gen) : BitVec 32 × Rand.Gen :=
  go g 8
where
  isNan (bits : BitVec 32) : Bool :=
    ((bits.toNat >>> 23) &&& 0xFF) = 0xFF ∧ (bits.toNat &&& 0x7FFFFF) ≠ 0
  go (g : Rand.Gen) (budget : Nat) : BitVec 32 × Rand.Gen :=
    let (bits, g') := Rand.nextBitVec g 32
    match budget with
    | Nat.succ b => if isNan bits then go g' b else (bits, g')
    | 0 => (bits, g')

-- Display helpers. Runtime `Nat.toDigits 16` is unreliable here, so we ship
-- our own hex formatter.

def hexDigit (d : Nat) : Char :=
  if d < 10 then Char.ofNat ('0'.toNat + d)
  else Char.ofNat ('a'.toNat + (d - 10))

def natToHex (n : Nat) : String :=
  if n = 0 then "0"
  else go n ""
where
  go (n : Nat) (acc : String) : String :=
    if n = 0 then acc
    else go (n / 16) (String.singleton (hexDigit (n % 16)) ++ acc)
  termination_by n

def hexBV {w : Nat} (x : BitVec w) : String :=
  "0x" ++ natToHex x.toNat

-- Shared edge cases for 32-bit rounding shifts (exercised by both ISAs)
def roundShiftEdges_32 : List (BitVec 32 × Nat) :=
  let minInt : BitVec 32 := BitVec.ofInt 32 (-(2 ^ 31))
  let maxInt : BitVec 32 := BitVec.ofInt 32 (2 ^ 31 - 1)
  let neg1   : BitVec 32 := BitVec.ofInt 32 (-1)
  [ (0,      0), (0,      1), (0,      31),
    (1,      0), (1,      1), (1,      31),
    (minInt, 0), (minInt, 1), (minInt, 31),
    (maxInt, 0), (maxInt, 1), (maxInt, 31),
    (neg1,   1), (neg1,   31) ]

-- Registered checks

def checkNeonRoundingShift : Check :=
  runCheck
    (name := "neon_roundShr_vs_int_ref")
    (sampler := sampleBV32ShiftLE31)
    (describe := fun (x, shift) => s!"x={hexBV x}, shift={shift}")
    (expected := fun (x, shift) => Ref.neonRoundingShiftRightRef x shift)
    (actual := fun (x, shift) => (BVShiftOp.roundShr .neon).eval x shift)
    (edgeCases := roundShiftEdges_32)

def checkRvvRoundingShift : Check :=
  runCheck
    (name := "rvv_roundShr_vs_int_ref")
    (sampler := sampleBV32ShiftLE31)
    (describe := fun (x, shift) => s!"x={hexBV x}, shift={shift}")
    (expected := fun (x, shift) => Ref.rvvRoundingShiftRightRef x shift)
    (actual := fun (x, shift) => (BVShiftOp.roundShr .rvvRnu).eval x shift)
    (edgeCases := roundShiftEdges_32)

/-- Numeric re-audit of `roundShr .neon ≡ roundShr .rvvRnu` under `shift ≤ 31`
    (formally proved in `SALT.Core.CrossISA`). -/
def checkRoundingModesAgree : Check :=
  runCheck
    (name := "roundShr_modes_agree (cross-ISA)")
    (sampler := sampleBV32ShiftLE31)
    (describe := fun (x, shift) => s!"x={hexBV x}, shift={shift}")
    (expected := fun (x, shift) => (BVShiftOp.roundShr .neon).eval x shift)
    (actual := fun (x, shift) => (BVShiftOp.roundShr .rvvRnu).eval x shift)
    (edgeCases := roundShiftEdges_32)

def checkSignedSatAdd : Check :=
  runCheck
    (name := "sSatAdd_vs_int_ref_32")
    (sampler := sampleTwoBV32)
    (describe := fun (a, b) => s!"a={hexBV a}, b={hexBV b}")
    (expected := fun (a, b) => Ref.signedSatAddRef a b)
    (actual := fun (a, b) => BVBinOp.sSatAdd.eval a b)

def checkSignedClamp (srcWidth dstWidth : Nat)
    (hsrc : 0 < srcWidth := by decide) (hdst : dstWidth < srcWidth := by decide) :
    Check :=
  let _ := hsrc
  runCheck
    (name := s!"sSatNarrow_{srcWidth}_to_{dstWidth}_vs_int_ref")
    (sampler := sampleBV srcWidth)
    (describe := fun x => s!"x={hexBV x}")
    (expected := fun x => (Ref.signedClampRef x : BitVec dstWidth))
    (actual := fun x => BVNarrowOp.sSatNarrow.eval dstWidth x hdst)

def checkSextTruncate (srcWidth dstWidth : Nat)
    (h : srcWidth < dstWidth := by decide) : Check :=
  runCheck
    (name := s!"sExt_truncate_{srcWidth}_to_{dstWidth}_roundtrip")
    (sampler := sampleBV srcWidth)
    (describe := fun x => s!"x={hexBV x}")
    (expected := fun x => x)
    (actual := fun x => (BVExtOp.sExt.eval dstWidth x h).truncate srcWidth)

def checkReinterpretRoundtrip : Check :=
  runCheck
    (name := "reinterpret_roundtrip_non_nan")
    (sampler := sampleNonNanBits)
    (describe := fun bits => s!"bits={hexBV bits}")
    (expected := fun bits => bits)
    (actual := fun bits =>
      ReinterpretOp.f32ToBits.eval (ReinterpretOp.bitsToF32.eval bits))

def allChecks : List Check :=
  [ checkNeonRoundingShift
  , checkRvvRoundingShift
  , checkRoundingModesAgree
  , checkSignedSatAdd
  , checkSignedClamp 32 16
  , checkSignedClamp 16 8
  , checkSextTruncate 8 32
  , checkSextTruncate 16 32
  , checkReinterpretRoundtrip ]

-- Driver

def runAll (seed : UInt64 := 0xCAFEF00DBEEF) (samplesPerCheck : Nat := 512) :
    List CheckResult :=
  allChecks.mapIdx (fun i c => c (seed + i.toUInt64 * subseedMixer) samplesPerCheck)

def reportIO (seed : UInt64 := 0xCAFEF00DBEEF) (samplesPerCheck : Nat := 512) :
    IO UInt32 := do
  let results := runAll seed samplesPerCheck
  let totalSamples := results.foldl (init := 0) (fun acc r => acc + r.samples)
  let allFailures := results.foldl (init := []) (fun acc r => acc ++ r.failures)
  let passed := results.countP (fun r => r.failures.isEmpty)
  IO.println s!"SALT §15.4 differential harness"
  IO.println s!"  seed:             {seed}"
  IO.println s!"  samples/check:    {samplesPerCheck}"
  IO.println s!"  total samples:    {totalSamples}"
  IO.println s!"  passed checks:    {passed}/{results.length}"
  IO.println ""
  for r in results do
    let status := if r.failures.isEmpty then "ok  " else "FAIL"
    IO.println s!"  [{status}] {r.name}  ({r.samples} samples, {r.failures.length} failures)"
  if allFailures.isEmpty then
    IO.println ""
    IO.println "ALL CHECKS PASSED"
    return 0
  else
    IO.println ""
    IO.println s!"{allFailures.length} FAILURES (first {maxFailuresPerCheck} shown per check):"
    for f in allFailures do
      IO.println s!"  check:    {f.check}"
      IO.println s!"    input:    {f.input}"
      IO.println s!"    expected: {f.expected}"
      IO.println s!"    actual:   {f.actual}"
    return 1

end SALT.Test.Differential
