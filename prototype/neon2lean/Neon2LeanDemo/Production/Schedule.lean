namespace Neon2LeanDemo.Production

/--
Each chunk is positive, fits in the current remainder, and together the chunks
consume the input exactly. This is a progress model, not an ISA-level
characterization of legal RVV `vsetvl` traces.
-/
def PositivePartition : Nat -> List Nat -> Prop
  | remaining, [] => remaining = 0
  | remaining, chunk :: chunks =>
      0 < chunk /\ chunk <= remaining /\
        PositivePartition (remaining - chunk) chunks

end Neon2LeanDemo.Production
