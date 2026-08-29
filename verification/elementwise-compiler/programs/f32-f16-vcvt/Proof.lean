import SALT.Corpus.f32f16vcvt.Spec

namespace SALT.Corpus.f32f16vcvt

private theorem selectTruncatedMask (condition : Prop) [Decidable condition]
    (onTrue onFalse : BitVec 16) :
    (BitVec.setWidth 16
        (if condition then (4294967295 : BitVec 32) else 0) &&& onTrue) |||
      ((~~~BitVec.setWidth 16
        (if condition then (4294967295 : BitVec 32) else 0)) &&& onFalse) =
        if condition then onTrue else onFalse := by
  by_cases h : condition <;> simp [h]
  all_goals bv_decide

private def conversionBase (x : BitVec 32) : BitVec 16 :=
  let absolute := SALT.Intrinsics.FP32.abs x
  let biasMasked := (absolute + 125829120) &&& 2139095040
  let bias := if biasMasked.toNat ≥ 1073741824 then biasMasked else 1073741824
  let value := SALT.Intrinsics.FP32.add
    (SALT.Intrinsics.FP32.mul
      (SALT.Intrinsics.FP32.mul absolute 2004877312) 142606336) bias
  (value.truncate 16 &&& 4095) + ((value.ushiftRight 13).truncate 16 &&& 31744)

private def conversionBaseRvv (x : BitVec 32) : BitVec 16 :=
  let absolute := SALT.Intrinsics.FP32.abs x
  let biasMasked := (absolute + 125829120) &&& 2139095040
  let bias := if biasMasked.toNat ≥ 1073741824 then biasMasked else 1073741824
  let value := SALT.Intrinsics.FP32.add
    (SALT.Intrinsics.FP32.mul
      (SALT.Intrinsics.FP32.mul absolute 2004877312) 142606336) bias
  ((value.ushiftRight 0).truncate 16 &&& 4095) +
    ((value.ushiftRight 13).truncate 16 &&& 31744)

private def conversionSign (x : BitVec 32) : BitVec 16 :=
  (x.ushiftRight 16).truncate 16 &&& 32768

private abbrev conversionIsNaN (x : BitVec 32) : Prop :=
  (SALT.Intrinsics.FP32.abs x).toNat > 2139095040

private abbrev conversionIsNaNBool (x : BitVec 32) : Bool :=
  decide (conversionIsNaN x)

private theorem fNeonUnfold (p : f32f16vcvtParams) (x : BitVec 32) :
    fNeon p x =
      (((BitVec.setWidth 16
          (if conversionIsNaN x then (4294967295 : BitVec 32) else 0) &&& 32256) |||
        ((~~~BitVec.setWidth 16
          (if conversionIsNaN x then (4294967295 : BitVec 32) else 0)) &&&
            conversionBase x)) ||| conversionSign x) := by
  rfl

private theorem fRvvUnfold (p : f32f16vcvtParams) (x : BitVec 32) :
    fRvv p x =
      ((if conversionIsNaNBool x then 32256 else conversionBaseRvv x) |||
        conversionSign x) := by
  rfl

private theorem conversionBaseRvv_eq_conversionBase (x : BitVec 32) :
    conversionBaseRvv x = conversionBase x := by
  rfl

set_option maxRecDepth 100000 in
private theorem elementFunctionsEqualCore (p : f32f16vcvtParams) (x : BitVec 32) :
    fNeon p x = fRvv p x := by
  rw [fNeonUnfold, fRvvUnfold]
  rw [selectTruncatedMask]
  rw [conversionBaseRvv_eq_conversionBase]
  by_cases hNaN : conversionIsNaN x
  · simp [conversionIsNaNBool, hNaN]
  · simp [conversionIsNaNBool, hNaN]

set_option maxRecDepth 100000 in
private theorem neonBlock8_eq_map (p : f32f16vcvtParams)
    (input : List (BitVec 32)) (hLength : input.length = 8) :
    neonBlock8FromIntrinsics p input = input.map (fNeon p) := by
  rcases input with _ | ⟨x0, input⟩
  · simp at hLength
  rcases input with _ | ⟨x1, input⟩
  · simp at hLength
  rcases input with _ | ⟨x2, input⟩
  · simp at hLength
  rcases input with _ | ⟨x3, input⟩
  · simp at hLength
  rcases input with _ | ⟨x4, input⟩
  · simp at hLength
  rcases input with _ | ⟨x5, input⟩
  · simp at hLength
  rcases input with _ | ⟨x6, input⟩
  · simp at hLength
  rcases input with _ | ⟨x7, input⟩
  · simp at hLength
  have hTail : input = [] := by cases input <;> simp_all
  subst input
  rfl

set_option maxRecDepth 100000 in
private theorem neonBlock4_eq_map (p : f32f16vcvtParams)
    (input : List (BitVec 32)) (hLength : input.length = 4) :
    neonBlock4FromIntrinsics p input = input.map (fNeonSecondary p) := by
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
  rfl

private theorem phaseFunctionsEqualCore (p : f32f16vcvtParams) (x : BitVec 32) :
    fNeon p x = fNeonSecondary p x := by
  rfl

private theorem rvvChunk_eq_map (p : f32f16vcvtParams)
    (input : List (BitVec 32)) :
    rvvChunkFromIntrinsics p input = input.map (fRvv p) := by
  induction input with
  | nil => rfl
  | cons x xs ih =>
      change fRvv p x :: rvvChunkFromIntrinsics p xs =
        fRvv p x :: xs.map (fRvv p)
      rw [ih]

set_option maxRecDepth 100000 in
private theorem neonTail_eq_take_map (p : f32f16vcvtParams)
    (loaded : List (BitVec 32)) (hLoaded : loaded.length = 4)
    (live : Nat) (hLive : live < 4) :
    neonPartialTailLivePrefixFromIntrinsics p loaded live =
      (loaded.map (fNeonSecondary p)).take live := by
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
  rcases hCases with h | h | h | h <;> subst live <;> rfl

private theorem neonTailWithOverread_eq_map (p : f32f16vcvtParams)
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
  exact List.map_congr_left (fun x _ => (phaseFunctionsEqualCore p x).symm)

theorem neonBlockEqualsMap : neonBlockEqualsMapClaim := neonBlock8_eq_map

theorem neonSecondaryBlockEqualsMap : neonSecondaryBlockEqualsMapClaim :=
  neonBlock4_eq_map

theorem neonPhaseFunctionsEqual : neonPhaseFunctionsEqualClaim := by
  exact phaseFunctionsEqualCore

theorem rvvChunkEqualsMap : rvvChunkEqualsMapClaim := rvvChunk_eq_map

theorem elementFunctionsEqual : elementFunctionsEqualClaim := by
  exact elementFunctionsEqualCore

theorem neonLoopEqualsMap : neonLoopEqualsMapClaim := by
  intro p input overread hOverread
  unfold neonValueLoopWithOverreadFromIntrinsics
  apply SALT.Kernel.Schedule.runTwoPhaseTail_eq_map 8 4 (by decide) (by decide)
      (neonBlock8FromIntrinsics p) (neonBlock4FromIntrinsics p) _ (fNeon p)
  · exact neonBlock8_eq_map p
  · intro block hLength
    rw [neonBlock4_eq_map p block hLength]
    exact List.map_congr_left (fun x _ => (phaseFunctionsEqualCore p x).symm)
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
  exact List.map_congr_left (fun x _ => elementFunctionsEqualCore p x)

end SALT.Corpus.f32f16vcvt
