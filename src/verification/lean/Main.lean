/-
  `lake exe diff-test` driver: diff-test [SEED] [SAMPLES].
  Exits 0 if every check agrees with its reference, non-zero on divergence.
-/
import SALT.Test.Differential

/-- Parse a `Nat` in decimal or `0x...` hex. -/
def parseNat? (s : String) : Option Nat :=
  if s.startsWith "0x" ∨ s.startsWith "0X" then
    let chars : List Char := (s.toList).drop 2
    chars.foldl (init := some 0) (fun (acc : Option Nat) c =>
      match acc with
      | none => none
      | some n =>
        let d : Option Nat :=
          if '0' ≤ c ∧ c ≤ '9' then some (c.toNat - '0'.toNat)
          else if 'a' ≤ c ∧ c ≤ 'f' then some (10 + c.toNat - 'a'.toNat)
          else if 'A' ≤ c ∧ c ≤ 'F' then some (10 + c.toNat - 'A'.toNat)
          else none
        d.map (fun d => n * 16 + d))
  else
    s.toNat?

def main (args : List String) : IO UInt32 := do
  let seed : UInt64 := match args with
    | s :: _ => ((parseNat? s).getD 0xCAFEF00DBEEF).toUInt64
    | []     => 0xCAFEF00DBEEF
  let samples : Nat := match args with
    | _ :: n :: _ => (parseNat? n).getD 512
    | _           => 512
  SALT.Test.Differential.reportIO seed samples
