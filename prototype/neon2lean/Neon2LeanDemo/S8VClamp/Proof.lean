import Neon2LeanDemo.S8VClamp.Model

namespace Neon2LeanDemo.S8VClamp

/-- Opposite clamp orders agree when the signed bounds are ordered. -/
theorem tailClamp_eq_clamp (lo hi x : Byte) (hBounds : lo.toInt ≤ hi.toInt) :
    tailClamp lo hi x = clamp lo hi x := by
  by_cases hLow : x.toInt < lo.toInt
  · have hxhi : x.toInt ≤ hi.toInt := by omega
    have hMinXHi : signedMin x hi = x := by simp [signedMin, hxhi]
    have hMaxXLo : signedMax x lo = lo := by simp [signedMax]; omega
    have hMinLoHi : signedMin lo hi = lo := by simp [signedMin, hBounds]
    simp [tailClamp, clamp, hMinXHi, hMaxXLo, hMinLoHi]
  · by_cases hHigh : hi.toInt < x.toInt
    · have hxlo : lo.toInt ≤ x.toInt := by omega
      have hMinXHi : signedMin x hi = hi := by simp [signedMin]; omega
      have hMaxHiLo : signedMax hi lo = hi := by simp [signedMax, hBounds]
      have hMaxXLo : signedMax x lo = x := by simp [signedMax, hxlo]
      simp [tailClamp, clamp, hMinXHi, hMaxHiLo, hMaxXLo]
    · have hxlo : lo.toInt ≤ x.toInt := by omega
      have hxhi : x.toInt ≤ hi.toInt := by omega
      have hMinXHi : signedMin x hi = x := by simp [signedMin, hxhi]
      have hMaxXLo : signedMax x lo = x := by simp [signedMax, hxlo]
      simp [tailClamp, clamp, hMinXHi, hMaxXLo]

/-- A legal chunk execution is just `List.map` when every chunk step implements `f`. -/
theorem processChunks_eq_map (step : Nat → Byte → Byte) (f : Byte → Byte)
    (chunks : List Nat) (input : List Byte)
    (hLegal : PositivePartition input.length chunks)
    (hStep : ∀ chunk x, step chunk x = f x) :
    processChunks step chunks input = input.map f := by
  induction chunks generalizing input with
  | nil =>
      have hLength : input.length = 0 := hLegal
      have hInput : input = [] := List.length_eq_zero_iff.mp hLength
      simp [processChunks, hInput]
  | cons chunk chunks ih =>
      rcases hLegal with ⟨_hPositive, _hFits, hRest⟩
      have hHead : (input.take chunk).map (step chunk) = (input.take chunk).map f := by
        apply List.map_congr_left
        intro x _hx
        exact hStep chunk x
      have hDropLegal : PositivePartition (input.drop chunk).length chunks := by
        simpa [List.length_drop] using hRest
      calc
        processChunks step (chunk :: chunks) input =
            (input.take chunk).map (step chunk) ++
              processChunks step chunks (input.drop chunk) := rfl
        _ = (input.take chunk).map f ++ processChunks step chunks (input.drop chunk) := by
          rw [hHead]
        _ = (input.take chunk).map f ++ (input.drop chunk).map f := by
          rw [ih (input.drop chunk) hDropLegal]
        _ = ((input.take chunk) ++ input.drop chunk).map f := by
          rw [List.map_append]
        _ = input.map f := by rw [List.take_append_drop]

/-- The concrete Neon schedule consumes exactly the requested number of bytes. -/
theorem neonSchedule_partition (remaining : Nat) :
    PositivePartition remaining (neonSchedule remaining) := by
  induction remaining using neonSchedule.induct with
  | case1 remaining h64 ih =>
      rw [neonSchedule]
      simp only [h64, ↓reduceDIte]
      exact ⟨by omega, h64, ih⟩
  | case2 remaining hNot64 h8 ih =>
      rw [neonSchedule]
      simp only [hNot64, h8, ↓reduceDIte]
      exact ⟨by omega, h8, ih⟩
  | case3 hNot64 hNot8 =>
      simp [neonSchedule, hNot64, hNot8, PositivePartition]
  | case4 remaining hNot64 hNot8 hNonzero =>
      simp [neonSchedule, hNot64, hNot8, hNonzero, PositivePartition]
      omega

/-- Every progress policy terminates and produces a positive partition. -/
theorem RVVProgressPolicy.schedule_partition (policy : RVVProgressPolicy)
    (remaining : Nat) : PositivePartition remaining (policy.schedule remaining) := by
  induction remaining using Nat.strongRecOn with
  | ind remaining ih =>
      rw [RVVProgressPolicy.schedule]
      split <;> rename_i hzero
      · subst remaining
        simp [PositivePartition]
      · have hpositive : 0 < remaining := Nat.pos_of_ne_zero hzero
        have hlegal := policy.legal remaining hpositive
        simp only [PositivePartition]
        exact ⟨hlegal.1, hlegal.2.1, ih (remaining - policy.choose remaining) (by omega)⟩

/-- Every Neon chunk is one main iteration, one 8-byte iteration, or the 1--7 tail. -/
theorem neonSchedule_chunk_shape (remaining chunk : Nat)
    (hMember : chunk ∈ neonSchedule remaining) :
    chunk = 64 ∨ chunk = 8 ∨ (0 < chunk ∧ chunk < 8) := by
  induction remaining using neonSchedule.induct with
  | case1 remaining h64 ih =>
      rw [neonSchedule] at hMember
      simp only [h64, ↓reduceDIte, List.mem_cons] at hMember
      rcases hMember with hChunk | hMember
      · exact Or.inl hChunk
      · exact ih hMember
  | case2 remaining hNot64 h8 ih =>
      rw [neonSchedule] at hMember
      simp only [hNot64, h8, ↓reduceDIte, List.mem_cons] at hMember
      rcases hMember with hChunk | hMember
      · exact Or.inr (Or.inl hChunk)
      · exact ih hMember
  | case3 hNot64 hNot8 =>
      simp [neonSchedule, hNot64, hNot8] at hMember
  | case4 remaining hNot64 hNot8 hNonzero =>
      simp [neonSchedule, hNot64, hNot8, hNonzero] at hMember
      subst chunk
      exact Or.inr (Or.inr ⟨by omega, by omega⟩)

theorem neonStep_eq_clamp (lo hi : Byte) (hBounds : lo.toInt ≤ hi.toInt)
    (chunk : Nat) (x : Byte) :
    neonStep lo hi chunk x = clamp lo hi x := by
  by_cases hMain : chunk = 64
  · simp [neonStep, hMain]
  · simp [neonStep, hMain, tailClamp_eq_clamp lo hi x hBounds]

/-- The complete 64/8/tail Neon schedule refines pointwise signed clamp. -/
theorem runNeon_refines (lo hi : Byte) (input : List Byte)
    (hBounds : lo.toInt ≤ hi.toInt) :
    runNeon lo hi input = input.map (clamp lo hi) := by
  apply processChunks_eq_map
  · exact neonSchedule_partition input.length
  · exact neonStep_eq_clamp lo hi hBounds

/-- Every positive partition refines pointwise signed clamp at the value level. -/
theorem runPartitioned_refines (lo hi : Byte) (chunks : List Nat) (input : List Byte)
    (hLegal : PositivePartition input.length chunks) :
    runPartitioned lo hi chunks input = input.map (clamp lo hi) := by
  apply processChunks_eq_map
  · exact hLegal
  · intro _chunk _x
    rfl

/-- A progress policy supplies termination instead of assuming a completed partition. -/
theorem runRVVPolicy_refines (policy : RVVProgressPolicy) (lo hi : Byte)
    (input : List Byte) :
    runRVVPolicy policy lo hi input = input.map (clamp lo hi) := by
  apply runPartitioned_refines
  exact policy.schedule_partition input.length

/--
The Neon value schedule agrees with every positive partition. This is an auxiliary
lemma, not the artifact-bound C/Neon-to-C/RVV equivalence theorem.
-/
theorem neon_partition_value_equiv (lo hi : Byte) (chunks : List Nat) (input : List Byte)
    (hBounds : lo.toInt ≤ hi.toInt)
    (hLegal : PositivePartition input.length chunks) :
    runNeon lo hi input = runPartitioned lo hi chunks input := by
  rw [runNeon_refines lo hi input hBounds,
      runPartitioned_refines lo hi chunks input hLegal]

/-- Value-level equivalence for any policy satisfying the explicit progress interface. -/
theorem neon_rvv_policy_value_equiv (policy : RVVProgressPolicy) (lo hi : Byte)
    (input : List Byte) (hBounds : lo.toInt ≤ hi.toInt) :
    runNeon lo hi input = runRVVPolicy policy lo hi input := by
  rw [runNeon_refines lo hi input hBounds, runRVVPolicy_refines policy lo hi input]

end Neon2LeanDemo.S8VClamp
