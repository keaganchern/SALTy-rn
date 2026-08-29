import SALT.Corpus.f32vlrelu.Spec

namespace SALT.Corpus.f32vlrelu

private def laneValue (p : f32vlreluParams) (x : BitVec 32) : BitVec 32 :=
  if x.toInt < 0 then SALT.Intrinsics.FP32.mul x p.slope else x

private theorem select_eq_laneValue (p : f32vlreluParams) (x : BitVec 32) :
    ((if x.toInt < 0 then BitVec.allOnes 32 else 0) &&&
      SALT.Intrinsics.FP32.mul x p.slope) |||
      ((~~~(if x.toInt < 0 then BitVec.allOnes 32 else 0)) &&& x) =
        laneValue p x := by
  by_cases h : x.toInt < 0 <;>
    simp [laneValue, h]
  all_goals bv_decide

private theorem fNeon_eq_laneValue (p : f32vlreluParams) (x : BitVec 32) :
    fNeon p x = laneValue p x := by
  simpa [fNeon, neonBlock4FromIntrinsics,
    SALT.Intrinsics.Neon.vmulq_f32, SALT.Intrinsics.Neon.vcltq_s32,
    SALT.Intrinsics.Neon.vbslq_f32] using select_eq_laneValue p x

private theorem fRvv_eq_laneValue (p : f32vlreluParams) (x : BitVec 32) :
    fRvv p x = laneValue p x := by
  simp [fRvv, rvvChunkFromIntrinsics, SALT.Intrinsics.RVV.vfmul_vf_f32,
    SALT.Intrinsics.RVV.vmslt_vx_i32, SALT.Intrinsics.RVV.vmerge_vvm_f32,
    laneValue]

private theorem neonBlock4_eq_map (p : f32vlreluParams)
    (input : List (BitVec 32)) (hLength : input.length = 4) :
    neonBlock4FromIntrinsics p input = input.map (fNeon p) := by
  rcases input with _ | ⟨x0, input⟩
  · simp at hLength
  rcases input with _ | ⟨x1, input⟩
  · simp at hLength
  rcases input with _ | ⟨x2, input⟩
  · simp at hLength
  rcases input with _ | ⟨x3, input⟩
  · simp at hLength
  have hTail : input = [] := by cases input <;> simp_all
  subst input
  simp [neonBlock4FromIntrinsics, fNeon, SALT.Intrinsics.Neon.vmulq_f32,
    SALT.Intrinsics.Neon.vcltq_s32, SALT.Intrinsics.Neon.vbslq_f32]

private theorem rvvChunk_eq_map (p : f32vlreluParams)
    (input : List (BitVec 32)) :
    rvvChunkFromIntrinsics p input = input.map (fRvv p) := by
  have hLane : rvvChunkFromIntrinsics p input = input.map (laneValue p) := by
    induction input with
    | nil =>
        simp [rvvChunkFromIntrinsics, SALT.Intrinsics.RVV.vfmul_vf_f32,
          SALT.Intrinsics.RVV.vmslt_vx_i32, SALT.Intrinsics.RVV.vmerge_vvm_f32]
    | cons x xs ih =>
        simp [rvvChunkFromIntrinsics, SALT.Intrinsics.RVV.vfmul_vf_f32,
          SALT.Intrinsics.RVV.vmslt_vx_i32, SALT.Intrinsics.RVV.vmerge_vvm_f32,
          laneValue] at ih ⊢
        exact ih
  rw [hLane]
  exact List.map_congr_left (fun x _ => (fRvv_eq_laneValue p x).symm)

private theorem neonTail_eq_take_map (p : f32vlreluParams)
    (loaded : List (BitVec 32)) (hLoaded : loaded.length = 4)
    (live : Nat) (hLive : live < 4) :
    neonPartialTailLivePrefixFromIntrinsics p loaded live =
      (loaded.map (fNeon p)).take live := by
  rcases loaded with _ | ⟨x0, loaded⟩
  · simp at hLoaded
  rcases loaded with _ | ⟨x1, loaded⟩
  · simp at hLoaded
  rcases loaded with _ | ⟨x2, loaded⟩
  · simp at hLoaded
  rcases loaded with _ | ⟨x3, loaded⟩
  · simp at hLoaded
  have hTail : loaded = [] := by cases loaded <;> simp_all
  subst loaded
  have hCases : live = 0 ∨ live = 1 ∨ live = 2 ∨ live = 3 := by omega
  rcases hCases with h | h | h | h <;> subst live <;>
    simp [neonPartialTailLivePrefixFromIntrinsics, fNeon,
      neonBlock4FromIntrinsics, SALT.Intrinsics.Neon.vmulq_f32,
      SALT.Intrinsics.Neon.vcltq_s32, SALT.Intrinsics.Neon.vbslq_f32,
      Nat.testBit]

private theorem neonTailWithOverread_eq_map (p : f32vlreluParams)
    (input overread : List (BitVec 32)) (hLength : input.length < 4)
    (hOverread : 4 - input.length ≤ overread.length) :
    let loaded := (input ++ overread).take 4
    neonPartialTailLivePrefixFromIntrinsics p loaded input.length =
      input.map (fNeon p) := by
  dsimp only
  let loaded := (input ++ overread).take 4
  have hLoaded : loaded.length = 4 := by
    simp [loaded, List.length_take]
    omega
  rw [neonTail_eq_take_map p loaded hLoaded input.length hLength]
  rw [← List.map_take]
  have hPrefix : loaded.take input.length = input := by
    simp only [loaded, List.take_take]
    rw [show min input.length 4 = input.length by omega]
    simp
  rw [hPrefix]

theorem neonBlockEqualsMap : neonBlockEqualsMapClaim := by
  exact neonBlock4_eq_map

theorem rvvChunkEqualsMap : rvvChunkEqualsMapClaim := by
  exact rvvChunk_eq_map

theorem elementFunctionsEqual : elementFunctionsEqualClaim := by
  intro p x
  rw [fNeon_eq_laneValue, fRvv_eq_laneValue]

theorem neonLoopEqualsMap : neonLoopEqualsMapClaim := by
  intro p input overread hOverread
  unfold neonValueLoopWithOverreadFromIntrinsics
  apply SALT.Kernel.Schedule.runFixedChunkTail_eq_map 4 (by decide)
      (neonBlock4FromIntrinsics p) _ (fNeon p)
  · exact neonBlock4_eq_map p
  · intro tail _ hTail
    exact neonTailWithOverread_eq_map p tail overread hTail (by omega)

theorem rvvLoopEqualsMap : rvvLoopEqualsMapClaim := by
  intro p input schedule
  exact SALT.Kernel.Schedule.processBlocks_eq_map
    (rvvChunkFromIntrinsics p) (fRvv p) (rvvChunk_eq_map p) input schedule

theorem completeValueEquivalence : completeValueEquivalenceClaim := by
  intro p input overread schedule hOverread
  rw [neonLoopEqualsMap p input overread hOverread]
  rw [rvvLoopEqualsMap p input schedule]
  exact List.map_congr_left (fun x _ => elementFunctionsEqual p x)

end SALT.Corpus.f32vlrelu
