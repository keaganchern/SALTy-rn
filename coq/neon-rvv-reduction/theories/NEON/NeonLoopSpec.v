Require Import isla.aarch64.aarch64.
Require Import Reduction.NEON.NeonLoop Reduction.NEON.NeonSequence Reduction.NEON.NeonSequenceSpec Reduction.NEON.NeonProof.
From Reduction.Generated.NEON Require Import a80001004 a80001008 a8000100c a80001010 a80001014 a80001018 a8000101c a80001020.
Lemma neon_machine_loop_result bs q :
  neon_sum4 (fold_neon bs q 0%nat) = bv_add (neon_sum4 (q 0%nat)) (block_sum bs).
Proof. apply structured_neon_blocks_sum. Qed.

Lemma neon_block_loop_observation `{!islaG Σ} `{!threadG} (bs : list block)
    (q : nat -> bv 128) (p : bv 64) (tailn : Z) (d : bv 1) :
  (0 <= tailn < 16)%Z ->
  (0x80000000 <= bv_unsigned p /\
    bv_unsigned p + 16 * Z.of_nat (length bs) <= 0x84000000)%Z ->
  (bv_unsigned p mod 16 = 0)%Z ->
  instr 0x80001004 (Some a80001004) -∗ instr 0x80001008 (Some a80001008) -∗
  instr 0x8000100c (Some a8000100c) -∗ instr 0x80001010 (Some a80001010) -∗
  instr 0x80001014 (Some a80001014) -∗ instr 0x80001018 (Some a80001018) -∗
  instr 0x8000101c (Some a8000101c) -∗ instr 0x80001020 (Some a80001020) -∗
  instr_body 0x80001004 (
    block_state q p (16 * Z.of_nat (length bs) + tailn) bs d ∗
    instr_pre 0x80001024 (
      ∃ qout : nat -> bv 128, block_state qout (bv_add p (Z_to_bv 64 (16 * Z.of_nat (length bs))))
        tailn [] d ∗ block_memory (bv_unsigned p) bs ∗
      ⌜neon_sum4 (qout 0%nat) = bv_add (neon_sum4 (q 0%nat)) (block_sum bs)⌝)).
Proof.
  intros Htail Hrange Halign.
  iIntros "#H04 #H08 #H0c #H10 #H14 #H18 #H1c #H20".
  iPoseProof (neon_block_loop bs q p tailn d Htail Hrange Halign
    with "H04 H08 H0c H10 H14 H18 H1c H20") as "Hloop".
  iApply (instr_pre_wand with "Hloop"); [done|done|].
  iIntros "[Hs Hout]". iFrame "Hs".
  iApply (instr_pre_wand with "Hout"); [done|done|].
  iIntros "[Hs Hmem]". iExists (fold_neon bs q). iFrame.
  iPureIntro. apply neon_machine_loop_result.
Qed.
Print Assumptions neon_machine_loop_result.
Print Assumptions neon_block_loop_observation.
