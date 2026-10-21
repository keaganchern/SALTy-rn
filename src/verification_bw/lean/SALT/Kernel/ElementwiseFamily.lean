import SALT.Kernel.Schedule

namespace SALT.Kernel.ElementwiseFamily

/-- Fixed-width loop with no tail. This is the schedule shape used when the C
    source asserts that the element count is divisible by `width`. -/
def runFixedNoTail {α β : Type} (width : Nat) (widthPositive : 0 < width)
    (block : List α -> List β) (input : List α) : List β :=
  SALT.Kernel.Schedule.runFixedChunkTail width widthPositive block (fun _ => []) input

/-- One family theorem: after this is proved once, every fixed-width
    element-wise kernel only needs to prove that one full block implements
    `List.map f`. -/
theorem runFixedNoTail_eq_map {α β : Type}
    (width : Nat) (widthPositive : 0 < width)
    (block : List α -> List β) (f : α -> β)
    (blockRefines : forall input, input.length = width -> block input = input.map f)
    (input : List α) (divisible : width ∣ input.length) :
    runFixedNoTail width widthPositive block input = input.map f := by
  suffices forall n (xs : List α), xs.length <= n -> width ∣ xs.length ->
      runFixedNoTail width widthPositive block xs = xs.map f from
    this input.length input (by omega) divisible
  intro n
  induction n with
  | zero =>
      intro xs hBound _
      have hEmpty : xs = [] := by cases xs <;> simp_all
      subst xs
      simp [runFixedNoTail, SALT.Kernel.Schedule.runFixedChunkTail]
  | succ n ih =>
      intro xs hBound hDivisible
      unfold runFixedNoTail SALT.Kernel.Schedule.runFixedChunkTail
      split <;> rename_i hEmpty
      · simp_all
      · split <;> rename_i hWidth
        · have hTake : (xs.take width).length = width := by
            simp [List.length_take, Nat.min_eq_left hWidth]
          rw [blockRefines _ hTake]
          have hDropDivisible : width ∣ (xs.drop width).length := by
            simpa only [List.length_drop] using
              (Nat.dvd_sub hDivisible (Nat.dvd_refl width))
          have hDropBound : (xs.drop width).length <= n := by
            simp only [List.length_drop]
            omega
          have hRecursive := ih (xs.drop width) hDropBound hDropDivisible
          change List.map f (xs.take width) ++
            runFixedNoTail width widthPositive block (xs.drop width) = xs.map f
          rw [hRecursive]
          rw [<- List.map_append, List.take_append_drop]
        · have hImpossible : False := by
            have hPositive : 0 < xs.length := by cases xs <;> simp_all
            have hLt : xs.length < width := Nat.lt_of_not_ge hWidth
            have hModSelf : xs.length % width = xs.length := Nat.mod_eq_of_lt hLt
            have hModZero : xs.length % width = 0 := Nat.mod_eq_zero_of_dvd hDivisible
            omega
          contradiction

end SALT.Kernel.ElementwiseFamily
