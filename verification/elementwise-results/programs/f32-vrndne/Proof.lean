import SALT.Corpus.f32vrndne.Spec

namespace SALT.Corpus.f32vrndne

private theorem selectMaskFalse (x round : BitVec 32) :
    (2147483648#32 &&& x) ||| (~~~2147483648#32 &&& round) =
      (round &&& 2147483647#32) ||| (x &&& 2147483648#32) := by
  have hNot : ~~~2147483648#32 = 2147483647#32 := by decide
  rw [hNot]
  ac_rfl

private theorem selectMaskTrue (x round : BitVec 32) :
    ((4294967295#32 ||| 2147483648#32) &&& x) |||
        (~~~(4294967295#32 ||| 2147483648#32) &&& round) = x := by
  have hMask : (4294967295#32 ||| 2147483648#32) = BitVec.allOnes 32 := by decide
  rw [hMask]
  rw [BitVec.allOnes_and, BitVec.not_allOnes, BitVec.zero_and, BitVec.or_zero]

private theorem allOnesMask_and (x : BitVec 32) :
    4294967295#32 &&& x = x := by
  change BitVec.allOnes 32 &&& x = x
  exact BitVec.allOnes_and

private theorem selectQuietAbs (x : BitVec 32) :
    (2147483648#32 &&& x) |||
        (~~~2147483648#32 &&&
          SALT.Intrinsics.FP32.quietNaN (SALT.Intrinsics.FP32.abs x)) =
      SALT.Intrinsics.FP32.quietNaN x := by
  have partition (sign value quiet : BitVec 32)
      (hDisjoint : quiet &&& sign = 0#32) :
      (sign &&& value) |||
          (~~~sign &&& ((value &&& ~~~sign) ||| quiet)) = value ||| quiet := by
    ext i
    have hBit := congrArg (fun v : BitVec 32 => v[i]) hDisjoint
    simp only [BitVec.getElem_and, BitVec.getElem_zero] at hBit
    simp only [BitVec.getElem_or, BitVec.getElem_and, BitVec.getElem_not]
    cases hs : sign[i] <;> cases hv : value[i] <;>
      cases hq : quiet[i] <;> simp_all
  unfold SALT.Intrinsics.FP32.quietNaN SALT.Intrinsics.FP32.abs
  have hNot : ~~~(2147483648 : BitVec 32) = 2147483647 := by decide
  have hDisjoint : (4194304 : BitVec 32) &&& 2147483648 = 0 := by decide
  rw [← hNot]
  exact partition 2147483648#32 x 4194304#32 hDisjoint

private theorem armAddSub_eq (a magic : BitVec 32)
    (hA : SALT.Intrinsics.FP32.isNaN a = false)
    (hMagic : SALT.Intrinsics.FP32.isNaN magic = false) :
    SALT.Intrinsics.FP32.armSubDN0AH0
        (SALT.Intrinsics.FP32.armAddDN0AH0 a magic) magic =
      SALT.Intrinsics.FP32.sub (SALT.Intrinsics.FP32.add a magic) magic := by
  rw [SALT.Intrinsics.FP32.armAdd_eq_add_of_not_nan a magic hA hMagic]
  by_cases hResult : SALT.Intrinsics.FP32.isNaN
      (SALT.Intrinsics.FP32.add a magic) = true
  · rw [SALT.Intrinsics.FP32.add_eq_canonicalNaN_of_isNaN a magic hResult]
    rw [SALT.Intrinsics.FP32.armSub_canonicalNaN_left magic hMagic]
    rw [SALT.Intrinsics.FP32.sub_canonicalNaN_left magic]
  · have hResultFalse : SALT.Intrinsics.FP32.isNaN
        (SALT.Intrinsics.FP32.add a magic) = false := by
      cases h : SALT.Intrinsics.FP32.isNaN (SALT.Intrinsics.FP32.add a magic)
      · rfl
      · exact False.elim (hResult h)
    exact SALT.Intrinsics.FP32.armSub_eq_sub_of_not_nan
      _ _ hResultFalse hMagic

private theorem elementFunctionsEqualCore (p : f32vrndneParams) (x : BitVec 32) :
    fNeon p x = fRvv p x := by
  simp [fNeon, fRvv, neonBlock4FromIntrinsics, rvvChunkFromIntrinsics,
    SALT.Intrinsics.Neon.vabsq_f32, SALT.Intrinsics.Neon.vcaltq_f32,
    SALT.Intrinsics.Neon.vaddq_f32, SALT.Intrinsics.Neon.vsubq_f32,
    SALT.Intrinsics.Neon.vorrq_u32, SALT.Intrinsics.Neon.vbslq_f32,
    SALT.Intrinsics.RVV.vfabs_v_f32, SALT.Intrinsics.RVV.vmfgt_vf_f32,
    SALT.Intrinsics.RVV.vfadd_vf_f32, SALT.Intrinsics.RVV.vfsub_vf_f32,
    SALT.Intrinsics.RVV.vfsgnj_vv_f32, SALT.Intrinsics.RVV.vmerge_vvm_f32,
    SALT.Intrinsics.RVV.vmfne_vv_f32, SALT.Intrinsics.RVV.vor_vx_u32]
  by_cases hNaN : SALT.Intrinsics.FP32.isNaN x = true
  · have hAbs : SALT.Intrinsics.FP32.isNaN
        (SALT.Intrinsics.FP32.abs x) = true := by
      rw [SALT.Intrinsics.FP32.isNaN_abs, hNaN]
    have hMagic : SALT.Intrinsics.FP32.isNaN
        1258291200#32 = false := by decide
    have hAdd := SALT.Intrinsics.FP32.armAdd_nan_left
      (SALT.Intrinsics.FP32.abs x) 1258291200#32 hAbs hMagic
    have hQuietNaN := SALT.Intrinsics.FP32.isNaN_quietNaN_of_isNaN
      (SALT.Intrinsics.FP32.abs x) hAbs
    have hSub := SALT.Intrinsics.FP32.armSub_nan_left
      (SALT.Intrinsics.FP32.quietNaN (SALT.Intrinsics.FP32.abs x))
      1258291200#32 hQuietNaN hMagic
    have hRound : SALT.Intrinsics.FP32.armSubDN0AH0
        (SALT.Intrinsics.FP32.armAddDN0AH0
          (SALT.Intrinsics.FP32.abs x) 1258291200#32)
        1258291200#32 =
        SALT.Intrinsics.FP32.quietNaN (SALT.Intrinsics.FP32.abs x) := by
      rw [hAdd, hSub, SALT.Intrinsics.FP32.quietNaN_idem]
    rw [hRound, SALT.Intrinsics.FP32.ne_self x, hNaN]
    have hAbsMagic : SALT.Intrinsics.FP32.abs 1258291200#32 =
        1258291200#32 := by decide
    have hCompare : SALT.Intrinsics.FP32.lt
        (SALT.Intrinsics.FP32.abs 1258291200#32)
        (SALT.Intrinsics.FP32.abs x) = false := by
      simp [SALT.Intrinsics.FP32.lt, hAbsMagic, hMagic, hAbs]
    rw [hCompare]
    simp only [Bool.false_eq_true, if_false]
    exact selectQuietAbs x
  · have hNaNFalse : SALT.Intrinsics.FP32.isNaN x = false := by
      cases h : SALT.Intrinsics.FP32.isNaN x
      · rfl
      · exact False.elim (hNaN h)
    have hAbs : SALT.Intrinsics.FP32.isNaN
        (SALT.Intrinsics.FP32.abs x) = false := by
      rw [SALT.Intrinsics.FP32.isNaN_abs, hNaNFalse]
    have hMagic : SALT.Intrinsics.FP32.isNaN
        1258291200#32 = false := by decide
    have hRound := armAddSub_eq (SALT.Intrinsics.FP32.abs x)
      1258291200#32 hAbs hMagic
    rw [hRound, SALT.Intrinsics.FP32.ne_self x, hNaNFalse]
    have hAbsMagic : SALT.Intrinsics.FP32.abs 1258291200#32 =
        1258291200#32 := by decide
    simp only [hAbsMagic, SALT.Intrinsics.FP32.gt]
    by_cases hCompare : SALT.Intrinsics.FP32.lt 1258291200#32
        (SALT.Intrinsics.FP32.abs x) = true
    · simp [hCompare]
      exact allOnesMask_and x
    · have hCompareFalse : SALT.Intrinsics.FP32.lt 1258291200#32
          (SALT.Intrinsics.FP32.abs x) = false := by
        cases h : SALT.Intrinsics.FP32.lt 1258291200#32
            (SALT.Intrinsics.FP32.abs x)
        · rfl
        · exact False.elim (hCompare h)
      simp [hCompareFalse]
      exact selectMaskFalse x _

private theorem neonBlock4_eq_map (p : f32vrndneParams)
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
  rfl

private theorem rvvChunk_eq_map (p : f32vrndneParams)
    (input : List (BitVec 32)) :
    rvvChunkFromIntrinsics p input = input.map (fRvv p) := by
  induction input with
  | nil => rfl
  | cons x xs ih =>
      change fRvv p x :: rvvChunkFromIntrinsics p xs =
        fRvv p x :: xs.map (fRvv p)
      rw [ih]

private theorem neonPartialTail_eq_take_map (p : f32vrndneParams)
    (loaded : List (BitVec 32)) (hLength : loaded.length = 4)
    (live : Nat) (hLive : live < 4) :
    neonPartialTailLivePrefixFromIntrinsics p loaded live =
      (loaded.map (fNeon p)).take live := by
  rcases loaded with _ | ⟨x0, loaded⟩
  · simp at hLength
  rcases loaded with _ | ⟨x1, loaded⟩
  · simp at hLength
  rcases loaded with _ | ⟨x2, loaded⟩
  · simp at hLength
  rcases loaded with _ | ⟨x3, loaded⟩
  · simp at hLength
  have hTail : loaded = [] := by cases loaded <;> simp_all
  subst loaded
  have hCases : live = 0 ∨ live = 1 ∨ live = 2 ∨ live = 3 := by omega
  rcases hCases with h | h | h | h <;> subst live <;> rfl

private theorem neonTailWithOverread_eq_map (p : f32vrndneParams)
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
  rw [← List.map_take, hPrefix]

theorem neonBlockEqualsMap : neonBlockEqualsMapClaim := neonBlock4_eq_map

theorem rvvChunkEqualsMap : rvvChunkEqualsMapClaim := rvvChunk_eq_map

theorem elementFunctionsEqual : elementFunctionsEqualClaim := by
  exact elementFunctionsEqualCore

theorem neonLoopEqualsMap : neonLoopEqualsMapClaim := by
  intro p input overread hOverread
  unfold neonValueLoopWithOverreadFromIntrinsics
  apply SALT.Kernel.Schedule.runFixedChunkTail_eq_map 4 (by decide)
      (neonBlock4FromIntrinsics p) _ (fNeon p)
  · exact neonBlock4_eq_map p
  · intro tail hPositive hLength
    exact neonTailWithOverread_eq_map p tail overread hPositive hLength hOverread

theorem rvvLoopEqualsMap : rvvLoopEqualsMapClaim := by
  intro p input schedule
  exact SALT.Kernel.Schedule.processBlocks_eq_map _ _
    (rvvChunk_eq_map p) input schedule

theorem completeValueEquivalence : completeValueEquivalenceClaim := by
  intro p input overread schedule hOverread
  rw [neonLoopEqualsMap p input overread hOverread]
  rw [rvvLoopEqualsMap p input schedule]
  exact List.map_congr_left (fun x _ => elementFunctionsEqualCore p x)

end SALT.Corpus.f32vrndne
