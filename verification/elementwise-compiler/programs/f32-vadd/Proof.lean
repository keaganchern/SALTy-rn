import SALT.Corpus.f32vadd.Spec

namespace SALT.Corpus.f32vadd

private theorem neonBlock4_eq_zipWith (p : f32vaddParams)
    (inputA inputB : List (BitVec 32)) (hLength : inputA.length = 4)
    (sameLength : inputA.length = inputB.length) :
    neonBlock4FromIntrinsics p inputA inputB =
      List.zipWith (fNeon p) inputA inputB := by
  have hLengthB : inputB.length = 4 := by omega
  have hTakeA : inputA.take 4 = inputA := by
    simpa only [hLength] using (List.take_length (l := inputA))
  have hTakeB : inputB.take 4 = inputB := by
    simpa only [hLengthB] using (List.take_length (l := inputB))
  have hFn : fNeon p = SALT.Intrinsics.FP32.add := by
    funext x y
    simp [fNeon, neonBlock4FromIntrinsics, SALT.Intrinsics.Neon.vaddq_f32]
  simp [neonBlock4FromIntrinsics, SALT.Intrinsics.Neon.vaddq_f32,
    hTakeA, hTakeB, hFn]

private theorem rvvChunk_eq_zipWith (p : f32vaddParams)
    (inputA inputB : List (BitVec 32)) :
    rvvChunkFromIntrinsics p inputA inputB =
      List.zipWith (fRvv p) inputA inputB := by
  have hFn : fRvv p = SALT.Intrinsics.FP32.add := by
    funext x y
    simp [fRvv, rvvChunkFromIntrinsics, SALT.Intrinsics.RVV.vfadd_vv_f32]
  simp [rvvChunkFromIntrinsics, SALT.Intrinsics.RVV.vfadd_vv_f32, hFn]

private theorem elementFunctionsEqual : elementFunctionsEqualClaim := by
  intro p x y
  simp [fNeon, fRvv, neonBlock4FromIntrinsics, rvvChunkFromIntrinsics,
    SALT.Intrinsics.Neon.vaddq_f32, SALT.Intrinsics.RVV.vfadd_vv_f32]

private theorem neonPartialTail_eq_take_zipWith (p : f32vaddParams)
    (loadedA loadedB : List (BitVec 32))
    (hLengthA : loadedA.length = 4) (hLengthB : loadedB.length = 4)
    (live : Nat) (hLive : live < 4) :
    neonPartialTailLivePrefixFromIntrinsics p loadedA loadedB live =
      (List.zipWith (fNeon p) loadedA loadedB).take live := by
  rcases loadedA with _ | ⟨a0, as⟩
  · simp at hLengthA
  rcases as with _ | ⟨a1, as⟩
  · simp at hLengthA
  rcases as with _ | ⟨a2, as⟩
  · simp at hLengthA
  rcases as with _ | ⟨a3, as⟩
  · simp at hLengthA
  have hTailA : as = [] := by cases as <;> simp_all
  subst as
  rcases loadedB with _ | ⟨b0, bs⟩
  · simp at hLengthB
  rcases bs with _ | ⟨b1, bs⟩
  · simp at hLengthB
  rcases bs with _ | ⟨b2, bs⟩
  · simp at hLengthB
  rcases bs with _ | ⟨b3, bs⟩
  · simp at hLengthB
  have hTailB : bs = [] := by cases bs <;> simp_all
  subst bs
  have hCases : live = 0 ∨ live = 1 ∨ live = 2 ∨ live = 3 := by omega
  rcases hCases with h | h | h | h <;> subst live <;>
    simp [neonPartialTailLivePrefixFromIntrinsics, fNeon,
      neonBlock4FromIntrinsics, SALT.Intrinsics.Neon.vaddq_f32, Nat.testBit]

private theorem neonTailWithOverread_eq_zipWith (p : f32vaddParams)
    (inputA inputB overreadA overreadB : List (BitVec 32))
    (sameLength : inputA.length = inputB.length)
    (hPositive : 0 < inputA.length) (hLength : inputA.length < 4)
    (hOverreadA : 3 ≤ overreadA.length) (hOverreadB : 3 ≤ overreadB.length) :
    let loadedA := (inputA ++ overreadA).take 4
    let loadedB := (inputB ++ overreadB).take 4
    neonPartialTailLivePrefixFromIntrinsics p loadedA loadedB inputA.length =
      List.zipWith (fNeon p) inputA inputB := by
  dsimp only
  let loadedA := (inputA ++ overreadA).take 4
  let loadedB := (inputB ++ overreadB).take 4
  have hLoadedA : loadedA.length = 4 := by
    simp [loadedA, List.length_take]
    omega
  have hLoadedB : loadedB.length = 4 := by
    simp [loadedB, List.length_take, sameLength]
    omega
  rw [neonPartialTail_eq_take_zipWith p loadedA loadedB hLoadedA hLoadedB
    inputA.length hLength]
  rw [List.take_zipWith]
  have hPrefixA : loadedA.take inputA.length = inputA := by
    simp only [loadedA, List.take_take]
    rw [show min inputA.length 4 = inputA.length by omega]
    simp
  have hPrefixB : loadedB.take inputA.length = inputB := by
    simp only [loadedB, List.take_take]
    rw [show min inputA.length 4 = inputA.length by omega]
    rw [sameLength]
    simp
  rw [hPrefixA, hPrefixB]

private theorem neonLoopEqualsMap : neonLoopEqualsMapClaim := by
  intro p inputA inputB overreadA overreadB sameLength hOverread
  unfold neonValueLoopWithOverreadFromIntrinsics
  apply SALT.Kernel.Schedule.runFixedChunkTail2_eq_zipWith 4 (by decide)
      (neonBlock4FromIntrinsics p) _ (fNeon p)
  · intro blockA blockB hSame hLength
    exact neonBlock4_eq_zipWith p blockA blockB hLength hSame
  · intro tailA tailB hSame hPositive hLength
    exact neonTailWithOverread_eq_zipWith p tailA tailB overreadA overreadB
      hSame hPositive hLength hOverread.1 hOverread.2

private theorem rvvLoopEqualsMap : rvvLoopEqualsMapClaim := by
  intro p inputA inputB sameLength schedule
  exact SALT.Kernel.Schedule.processBlocks2_eq_zipWith _ _
    (fun blockA blockB _ => rvvChunk_eq_zipWith p blockA blockB)
    inputA inputB sameLength schedule

theorem completeValueEquivalence : completeValueEquivalenceClaim := by
  intro p inputA inputB overreadA overreadB sameLength schedule hOverread
  rw [neonLoopEqualsMap p inputA inputB overreadA overreadB sameLength hOverread]
  rw [rvvLoopEqualsMap p inputA inputB sameLength schedule]
  have hFunctions : fNeon p = fRvv p := by
    funext x y
    exact elementFunctionsEqual p x y
  rw [hFunctions]

end SALT.Corpus.f32vadd
