Require Import isla.aarch64.aarch64.
Require Import Reduction.NEON.NeonSequence Reduction.NEON.NeonLoop Reduction.NEON.NeonLoopSpec Reduction.NEON.NeonSequenceSpec Reduction.NEON.NeonProof Reduction.NEON.NeonEdges Reduction.NEON.NeonTail Reduction.NEON.NeonTailEntry Reduction.NEON.NeonFinalize.
From Reduction.Generated.NEON Require Import a80001000 a80001004 a80001008 a8000100c a80001010 a80001014 a80001018 a8000101c a80001020 a80001024 a80001028 a8000102c a80001030 a80001034 a80001038 a8000103c a80001040 a80001044 a80001048 a8000104c.

Definition input_memory `{!islaG Σ} `{!threadG} p bs xs : iProp Σ :=
  block_memory p bs ∗ byte_memory (p + 16 * Z.of_nat (length bs)) xs.

(* Full entry-to-return contract; arbitrary 16-byte blocks plus a 0..15-byte
   suffix, with exact final vector and scratch-register values retained. *)
Lemma neon_kernel_correct `{!islaG Σ} `{!threadG}
    (bs : list block) (xs : list (bv 8)) (q : nat -> bv 128)
    (p out retaddr scratch8 scratch9 mpidr : bv 64) (initial : bv 32) (d : bv 1) :
  (Z.of_nat (length xs) < 16)%Z ->
  (0x80000000 <= bv_unsigned p /\
    bv_unsigned p + 16 * Z.of_nat (length bs) + Z.of_nat (length xs) <= 0x84000000)%Z ->
  (bv_unsigned p mod 16 = 0)%Z ->
  (0x80000000 <= bv_unsigned out <= 0x83fffffc)%Z ->
  bv_and out (BV 64 3) = BV 64 0 ->
  instr 0x80001000 (Some a80001000) -∗
  instr 0x80001004 (Some a80001004) -∗
  instr 0x80001008 (Some a80001008) -∗
  instr 0x8000100c (Some a8000100c) -∗
  instr 0x80001010 (Some a80001010) -∗
  instr 0x80001014 (Some a80001014) -∗
  instr 0x80001018 (Some a80001018) -∗
  instr 0x8000101c (Some a8000101c) -∗
  instr 0x80001020 (Some a80001020) -∗
  instr 0x80001024 (Some a80001024) -∗
  instr 0x80001028 (Some a80001028) -∗
  instr 0x8000102c (Some a8000102c) -∗
  instr 0x80001030 (Some a80001030) -∗
  instr 0x80001034 (Some a80001034) -∗
  instr 0x80001038 (Some a80001038) -∗
  instr 0x8000103c (Some a8000103c) -∗
  instr 0x80001040 (Some a80001040) -∗
  instr 0x80001044 (Some a80001044) -∗
  instr 0x80001048 (Some a80001048) -∗
  instr 0x8000104c (Some a8000104c) -∗
  instr_body 0x80001000 (
    block_state q p (16 * Z.of_nat (length bs) + Z.of_nat (length xs)) bs d ∗
    byte_memory (bv_unsigned p + 16 * Z.of_nat (length bs)) xs ∗
    "R2" ↦ᵣ RVal_Bits out ∗ "R8" ↦ᵣ RVal_Bits scratch8 ∗ "R9" ↦ᵣ RVal_Bits scratch9 ∗
    "R30" ↦ᵣ RVal_Bits retaddr ∗ "MPIDR_EL1" ↦ᵣ RVal_Bits mpidr ∗
    bv_unsigned out ↦ₘ initial ∗
    instr_pre (bv_unsigned retaddr) (
      neon_env d ∗ "R0" ↦ᵣ RVal_Bits (Z_to_bv 64 0) ∗
      "R1" ↦ᵣ RVal_Bits (bv_add p (Z_to_bv 64 (16 * Z.of_nat (length bs) + Z.of_nat (length xs)))) ∗
      "R2" ↦ᵣ RVal_Bits out ∗ "R30" ↦ᵣ RVal_Bits retaddr ∗ "MPIDR_EL1" ↦ᵣ RVal_Bits mpidr ∗
      "_V" ↦ᵣ neon_regs (q_reduced (fold_neon bs (q_init q))) ∗
      "R8" ↦ᵣ RVal_Bits (bv_zero_extend 64 (bv_add initial (bv_add (block_sum bs) (byte_sum xs)))) ∗
      "R9" ↦ᵣ RVal_Bits (bv_zero_extend 64 (bv_add (block_sum bs) (byte_sum xs))) ∗
      flags ∗ input_memory (bv_unsigned p) bs xs ∗
      bv_unsigned out ↦ₘ (bv_add initial (bv_add (block_sum bs) (byte_sum xs))))).
Proof.
  intros Htail Hrange Halign Hout Halignout.
  assert (Ht : (0 <= Z.of_nat (length xs) < 16)%Z) by lia.
  assert (Hb : (0x80000000 <= bv_unsigned p /\
    bv_unsigned p + 16 * Z.of_nat (length bs) <= 0x84000000)%Z) by lia.
  pose (p' := bv_add p (Z_to_bv 64 (16 * Z.of_nat (length bs)))).
  assert (Hp' : bv_unsigned p' = (bv_unsigned p + 16 * Z.of_nat (length bs))%Z).
  { unfold p'. bv_solve. }
  assert (Hr : (0x80000000 <= bv_unsigned p' /\
    bv_unsigned p' + Z.of_nat (length xs) <= 0x84000000)%Z).
  { rewrite Hp'. lia. }
  pose (q' := fold_neon bs (q_init q)).
  assert (Hsum : neon_sum4 (q' 0%nat) = block_sum bs).
  { unfold q'. rewrite neon_machine_loop_result.
    change (bv_add (neon_sum4 (BV 128 0)) (block_sum bs) = block_sum bs).
    unfold neon_sum4. bv_solve. }
  iIntros "#H00 #H04 #H08 #H0c #H10 #H14 #H18 #H1c #H20 #H24 #H28 #H2c #H30 #H34 #H38 #H3c #H40 #H44 #H48 #H4c".
  iPoseProof (neon_init q d with "H00") as "Hinit".
  iPoseProof (neon_block_loop bs (q_init q) p (Z.of_nat (length xs)) d Ht Hb Halign
    with "H04 H08 H0c H10 H14 H18 H1c H20") as "Hloop".
  iPoseProof (neon_reduce_to_scalar q' d scratch9 with "H24 H28") as "Hreduce".
  iPoseProof (neon_tail_with_zero xs p' (neon_sum4 (q' 0%nat)) d Hr
    with "H2c H30 H34 H38 H3c") as "Htail".
  iPoseProof (neon_write_result out retaddr mpidr initial
    (bv_add (neon_sum4 (q' 0%nat)) (byte_sum xs)) d Hout Halignout
    with "H40 H44 H48 H4c") as "Hwrite".
  iApply (instr_pre_wand with "Hinit"); [done|done|].
  iIntros "(Hs & Hxs & HR2 & HR8 & HR9 & HR30 & HM & Houtmem & Hexit)".
  iDestruct "Hs" as "(Henv & HR0 & HR1 & HV & Hbs & Hflags)".
  iFrame "Henv HV".
  iApply (instr_pre_wand with "Hloop"); [done|done|].
  iIntros "[Henv HV]". iFrame "Henv HR0 HR1 HV Hbs Hflags".
  iApply (instr_pre_wand with "Hreduce"); [done|done|].
  iIntros "[Hs Hbs]".
  iDestruct "Hs" as "(Henv & HR0 & HR1 & HV & Hemp & Hflags)".
  iFrame "Henv HV HR9".
  iApply (instr_pre_wand with "Htail"); [done|done|].
  iIntros "(Henv & HV & HR9)".
  iSplitL "Henv HR0 HR1 HR9 HR8 Hflags".
  { iFrame "Henv HR0 HR1 HR9 Hflags". iExists scratch8. iFrame. }
  iSplitL "Hxs". { rewrite Hp'. iExact "Hxs". }
  iApply (instr_pre_wand with "Hwrite"); [done|done|].
  iIntros "[Hs Hxs]".
  iDestruct "Hs" as "(Henv & HR0 & HR1 & HR9 & HR8 & Hflags)".
  iFrame "Henv HR2 HR8 HR9 HR30 HM Houtmem".
  iApply (instr_pre_wand with "Hexit"); [done|done|].
  iIntros "(Henv & HR2 & HR8 & HR9 & HR30 & HM & Houtmem)".
  assert (Hptr : bv_add p' (Z_to_bv 64 (Z.of_nat (length xs))) =
    bv_add p (Z_to_bv 64 (16 * Z.of_nat (length bs) + Z.of_nat (length xs)))).
  { unfold p'. rewrite <- bv_add_assoc. f_equal. apply bv_eq. bv_simplify. done. }
  rewrite <- Hptr. rewrite <- Hsum. iFrame "Henv HR0 HR1 HR2 HR30 HM HV HR8 HR9 Hflags Houtmem".
  unfold input_memory. iFrame "Hbs". rewrite <- Hp'. iExact "Hxs".
Qed.
Print Assumptions neon_kernel_correct.
