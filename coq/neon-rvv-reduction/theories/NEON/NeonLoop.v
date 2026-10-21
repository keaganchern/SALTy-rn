Require Import isla.aarch64.aarch64.
Require Import Reduction.Generated.NEON.Kernel Reduction.NEON.NeonSequence Reduction.NEON.NeonPairProof Reduction.NEON.NeonWordProof Reduction.NEON.MemoryBridge Reduction.NEON.Pointer.
From Reduction.Generated.NEON Require Import a80001004 a80001008 a8000100c a80001010 a80001014 a80001018 a8000101c a80001020.

Definition block := (bv 64 * bv 64)%type.
Fixpoint fold_neon (bs : list block) (q : nat -> bv 128) : nat -> bv 128 :=
  match bs with
  | [] => q
  | (lo,hi)::bs => fold_neon bs (after_load_pair q lo hi)
  end.
Fixpoint block_memory `{!islaG Σ} `{!threadG} (p : Z) (bs : list block) : iProp Σ :=
  match bs with
  | [] => emp
  | (lo,hi)::bs => p ↦ₘ lo ∗ (p+8) ↦ₘ hi ∗ block_memory (p+16) bs
  end.
Definition flags `{!islaG Σ} `{!threadG} : iProp Σ :=
  ∃ (n z c v : bv 1), "PSTATE" # "N" ↦ᵣ RVal_Bits n ∗
  "PSTATE" # "Z" ↦ᵣ RVal_Bits z ∗ "PSTATE" # "C" ↦ᵣ RVal_Bits c ∗
  "PSTATE" # "V" ↦ᵣ RVal_Bits v.
Definition block_state `{!islaG Σ} `{!threadG}
    (q : nat -> bv 128) (p : bv 64) (n : Z) (bs : list block) (d : bv 1) : iProp Σ :=
  neon_env d ∗ "R0" ↦ᵣ RVal_Bits (Z_to_bv 64 n) ∗
  "R1" ↦ᵣ RVal_Bits p ∗ "_V" ↦ᵣ neon_regs q ∗
  block_memory (bv_unsigned p) bs ∗ flags.
Arguments block_state /.
Arguments flags /.
Local Opaque neon_uadalp8_result neon_uadalp16_result.

(* Unbounded number of 16-byte blocks, with an arbitrary 0..15 byte suffix.
   The suffix is handled after this loop; the postcondition is exact state. *)
Lemma neon_block_loop `{!islaG Σ} `{!threadG} (bs : list block)
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
      block_state (fold_neon bs q) (bv_add p (Z_to_bv 64 (16 * Z.of_nat (length bs))))
        tailn [] d ∗ block_memory (bv_unsigned p) bs)).
Proof.
  revert q p. induction bs as [|[lo hi] bs IH]; intros q p Htail Hrange Halign.
  - cbn [length fold_neon block_memory].
    iStartProof. liARun.
    Unshelve. all: prepare_sidecond.
    all: try bv_simplify H0; try bv_solve.
    all: try (apply aligned16_mask; exact Halign).
    Unshelve. all: prepare_sidecond.
    all: try bv_simplify H0; try bv_solve.
  - iIntros "#H04 #H08 #H0c #H10 #H14 #H18 #H1c #H20".
    assert (Hp : (0x80000000 <= bv_unsigned p <= 0x83fffff0)%Z).
    { cbn [length] in Hrange. lia. }
    pose (p' := bv_add p (BV 64 16)).
    assert (Hp' : bv_unsigned p' = (bv_unsigned p + 16)%Z).
    { unfold p'. bv_solve. }
    assert (Hrange' : (0x80000000 <= bv_unsigned p' /\
      bv_unsigned p' + 16 * Z.of_nat (length bs) <= 0x84000000)%Z).
    { rewrite Hp'. cbn [length] in Hrange. lia. }
    assert (Halign' : (bv_unsigned p' mod 16 = 0)%Z).
    { rewrite Hp'. rewrite Z.add_mod; [rewrite Halign; reflexivity|lia]. }
    iPoseProof (neon_load_widen_accumulate q p lo hi d Hp Halign
      with "H0c H10 H14 H18") as "Hbody".
    iApply (instr_pre_intro_Some with "H04").
    iIntros "[Hstate Hexit] HPC".
    iDestruct "Hstate" as "(Henv & HR0 & HR1 & HV & Hmem & Hflags)".
    iDestruct "Henv" as "(?&?&?&?&?&?&?&?&?&?&?&?&?&?&?&?)".
    iDestruct "Hflags" as (fn fz fc fv) "(?&?&?&?)".
    iDestruct "Hmem" as "(Hlo & Hhi & Hrest)".
    iPoseProof (IH (after_load_pair q lo hi) p' Htail Hrange' Halign'
      with "H04 H08 H0c H10 H14 H18 H1c H20") as "Hloop".
    liARun.
    Unshelve. all: prepare_sidecond.
    all: try bv_simplify H0; try bv_solve.
    all: try (apply aligned16_mask; exact Halign).
    Unshelve. all: prepare_sidecond.
    all: try bv_simplify H0; try bv_solve.
Unshelve. all: prepare_sidecond.
all: try done.
all: try (exfalso; bv_simplify H0; bv_solve).
Unshelve. all: try done.
all: try (exfalso; bv_simplify H0; bv_solve).
  iSplitL "Hrest". { rewrite Hp'. iExact "Hrest". }
  iFrame.
  iApply (instr_pre_wand with "Hexit"); [done|done|].
  iIntros "[Hstate Hrest]".
  assert (Hptr : bv_add p' (Z_to_bv 64 (16 * Z.of_nat (length bs))) =
    bv_add p (Z_to_bv 64 (16 * Z.of_nat (length ((lo,hi)::bs))))).
  { unfold p'. apply advance_blocks. }
  cbn [fold_neon block_memory].
  rewrite <- Hptr. iFrame "Hstate".
  iFrame. rewrite Hp'. iExact "Hrest".
Qed.
Print Assumptions neon_block_loop.
