import SALT.Corpus.f32vsqrt.Spec

namespace SALT.Corpus.f32vsqrt

private theorem neonBlock4_eq_map (p : f32vsqrtParams)
    (input : List (BitVec 32)) (hLength : input.length = 4) :
    neonBlock4FromIntrinsics p input = input.map (fNeon p) := by
  have hTake : input.take 4 = input := by
    simpa only [hLength] using (List.take_length (l := input))
  have hFn : fNeon p = SALT.Intrinsics.FP32.sqrt := by
    funext x
    simp [fNeon, neonBlock4FromIntrinsics, SALT.Intrinsics.Neon.vsqrtq_f32]
  simp [neonBlock4FromIntrinsics, SALT.Intrinsics.Neon.vsqrtq_f32, hTake, hFn]

private theorem rvvChunk_eq_map (p : f32vsqrtParams)
    (input : List (BitVec 32)) :
    rvvChunkFromIntrinsics p input = input.map (fRvv p) := by
  have hFn : fRvv p = SALT.Intrinsics.FP32.sqrt := by
    funext x
    simp [fRvv, rvvChunkFromIntrinsics, SALT.Intrinsics.RVV.vfsqrt_v_f32]
  simp [rvvChunkFromIntrinsics, SALT.Intrinsics.RVV.vfsqrt_v_f32, hFn]

private theorem elementFunctionsEqual : elementFunctionsEqualClaim := by
  intro p x
  simp [fNeon, fRvv, neonBlock4FromIntrinsics, rvvChunkFromIntrinsics,
    SALT.Intrinsics.Neon.vsqrtq_f32, SALT.Intrinsics.RVV.vfsqrt_v_f32]

private theorem neonPartialTail_eq_take_map (p : f32vsqrtParams)
    (loaded : List (BitVec 32)) (hLength : loaded.length = 4)
    (live : Nat) (hLive : live < 4) :
    neonPartialTailLivePrefixFromIntrinsics p loaded live =
      (loaded.map (fNeon p)).take live := by
  rcases loaded with _ | ⟨x0, xs⟩
  · simp at hLength
  rcases xs with _ | ⟨x1, xs⟩
  · simp at hLength
  rcases xs with _ | ⟨x2, xs⟩
  · simp at hLength
  rcases xs with _ | ⟨x3, xs⟩
  · simp at hLength
  have hTail : xs = [] := by cases xs <;> simp_all
  subst xs
  have hCases : live = 0 ∨ live = 1 ∨ live = 2 ∨ live = 3 := by omega
  rcases hCases with h | h | h | h <;> subst live <;>
    simp [neonPartialTailLivePrefixFromIntrinsics, fNeon,
      neonBlock4FromIntrinsics, SALT.Intrinsics.Neon.vsqrtq_f32, Nat.testBit]

private theorem neonTailWithOverread_eq_map (p : f32vsqrtParams)
    (input overread : List (BitVec 32))
    (hPositive : 0 < input.length) (hLength : input.length < 4)
    (hOverread : 3 ≤ overread.length) :
    let loaded := (input ++ overread).take 4
    neonPartialTailLivePrefixFromIntrinsics p loaded input.length =
      input.map (fNeon p) := by
  dsimp only
  let loaded := (input ++ overread).take 4
  have hLoaded : loaded.length = 4 := by
    simp [loaded, List.length_take]
    omega
  rw [neonPartialTail_eq_take_map p loaded hLoaded input.length hLength]
  have hPrefix : loaded.take input.length = input := by
    simp only [loaded, List.take_take]
    rw [show min input.length 4 = input.length by omega]
    simp
  rw [<- List.map_take, hPrefix]

private theorem neonLoopEqualsMap : neonLoopEqualsMapClaim := by
  intro p input overread hOverread
  unfold neonValueLoopWithOverreadFromIntrinsics
  apply SALT.Kernel.Schedule.runFixedChunkTail_eq_map 4 (by decide)
      (neonBlock4FromIntrinsics p) _ (fNeon p)
  · exact neonBlock4_eq_map p
  · intro tail hPositive hLength
    exact neonTailWithOverread_eq_map p tail overread hPositive hLength hOverread

private theorem rvvLoopEqualsMap : rvvLoopEqualsMapClaim := by
  intro p input schedule
  exact SALT.Kernel.Schedule.processBlocks_eq_map _ _
    (rvvChunk_eq_map p) input schedule

theorem completeValueEquivalence : completeValueEquivalenceClaim := by
  intro p input overread schedule hOverread
  rw [neonLoopEqualsMap p input overread hOverread]
  rw [rvvLoopEqualsMap p input schedule]
  have hFunctions : fNeon p = fRvv p := by
    funext x
    exact elementFunctionsEqual p x
  rw [hFunctions]

end SALT.Corpus.f32vsqrt
