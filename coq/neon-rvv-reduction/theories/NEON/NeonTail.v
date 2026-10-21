Require Import isla.aarch64.aarch64.
Require Import Reduction.NEON.NeonSequence Reduction.NEON.NeonLoop.
From Reduction.Generated.NEON Require Import a80001030 a80001034 a80001038 a8000103c.

Fixpoint byte_memory `{!islaG Σ} `{!threadG} (p : Z) (xs : list (bv 8)) : iProp Σ :=
  match xs with [] => emp | x::xs => p ↦ₘ x ∗ byte_memory (p+1) xs end.
Fixpoint byte_sum (xs : list (bv 8)) : bv 32 :=
  match xs with [] => BV 32 0 | x::xs => bv_add (bv_zero_extend 32 x) (byte_sum xs) end.
Definition byte_state `{!islaG Σ} `{!threadG} (p : bv 64) (n : Z) (acc : bv 32) (d : bv 1) : iProp Σ :=
  neon_env d ∗ "R0" ↦ᵣ RVal_Bits (Z_to_bv 64 n) ∗ "R1" ↦ᵣ RVal_Bits p ∗
  "R9" ↦ᵣ RVal_Bits (bv_zero_extend 64 acc) ∗
  (∃ tmp : bv 64, "R8" ↦ᵣ RVal_Bits tmp) ∗ flags.
Arguments byte_state /.

Lemma advance_bytes (p : bv 64) n :
  bv_add (bv_add p (BV 64 1)) (Z_to_bv 64 (Z.of_nat n)) =
  bv_add p (Z_to_bv 64 (Z.of_nat (S n))).
Proof.
  rewrite <- bv_add_assoc. f_equal. apply bv_eq. bv_simplify.
  rewrite Nat2Z.inj_succ. f_equal. lia.
Qed.

Lemma neon_byte_loop `{!islaG Σ} `{!threadG} (xs : list (bv 8))
    (p : bv 64) (acc : bv 32) (d : bv 1) :
  xs <> [] ->
  (0x80000000 <= bv_unsigned p /\
    bv_unsigned p + Z.of_nat (length xs) <= 0x84000000)%Z ->
  instr 0x80001030 (Some a80001030) -∗ instr 0x80001034 (Some a80001034) -∗
  instr 0x80001038 (Some a80001038) -∗ instr 0x8000103c (Some a8000103c) -∗
  instr_body 0x80001030 (
    byte_state p (Z.of_nat (length xs)) acc d ∗ byte_memory (bv_unsigned p) xs ∗
    instr_pre 0x80001040 (
      byte_state (bv_add p (Z_to_bv 64 (Z.of_nat (length xs)))) 0
        (bv_add acc (byte_sum xs)) d ∗ byte_memory (bv_unsigned p) xs)).
Proof.
  revert p acc. induction xs as [|x xs IH]; intros p acc Hne Hrange; [contradiction|].
  destruct xs as [|y ys].
  - cbn [length byte_memory byte_sum]. cbn [length] in Hrange.
    iStartProof. liARun.
    Unshelve. all: prepare_sidecond.
    all: try (exfalso; bv_simplify H4; bv_solve).
    all: try bv_solve.
    Unshelve. all: try done.
    all: try (exfalso; bv_simplify H0; bv_solve).
    all: try (exfalso; bv_simplify H4; bv_solve).
  - iIntros "#H30 #H34 #H38 #H3c".
    pose (p' := bv_add p (BV 64 1)).
    assert (Hp' : bv_unsigned p' = (bv_unsigned p + 1)%Z).
    { unfold p'. cbn [length] in Hrange. bv_solve. }
    assert (Hrange' : (0x80000000 <= bv_unsigned p' /\
      bv_unsigned p' + Z.of_nat (length (y::ys)) <= 0x84000000)%Z).
    { rewrite Hp'. cbn [length] in Hrange |- *. lia. }
    iApply (instr_pre_intro_Some with "H30").
    iIntros "(Hs & Hmem & Hexit) HPC".
    iDestruct "Hs" as "(Henv & HR0 & HR1 & HR9 & HR8 & Hflags)".
    iDestruct "Henv" as "(?&?&?&?&?&?&?&?&?&?&?&?&?&?&?&?)".
    iDestruct "HR8" as (tmp) "?".
    iDestruct "Hflags" as (fn fz fc fv) "(?&?&?&?)".
    iDestruct "Hmem" as "(Hx & Hrest)".
    iPoseProof (IH p' (bv_add acc (bv_zero_extend 32 x)) ltac:(discriminate) Hrange'
      with "H30 H34 H38 H3c") as "Hloop".
    liARun.
    Unshelve. all: prepare_sidecond.
    all: cbn [length] in Hrange.
    all: try (exfalso; bv_simplify H4; bv_solve).
    all: try bv_solve.
  Unshelve. all: try done.
  all: try (exfalso; bv_simplify H0; bv_solve).
  all: try (exfalso; bv_simplify H4; bv_solve).
  iDestruct "Hrest" as "[Hy Hys]".
  iSplitL "Hy". { rewrite Hp'. iExact "Hy". }
  iSplitL "Hys". { rewrite Hp'. iExact "Hys". }
  iApply (instr_pre_wand with "Hexit"); [done|done|].
  iIntros "[Hs Hrest]".
  assert (Hptr : bv_add p' (Z_to_bv 64 (Z.of_nat (S (length ys)))) =
    bv_add p (Z_to_bv 64 (Z.of_nat (S (S (length ys)))))).
  { unfold p'. apply advance_bytes. }
  assert (Haddr : bv_unsigned LET1 = bv_unsigned p) by (unfold LET1, LET0; bv_solve).
  rewrite <- Hptr.
  assert (Hsum : bv_add acc (bv_add (bv_zero_extend 32 x) (bv_add (bv_zero_extend 32 y) (byte_sum ys))) =
    bv_add (bv_add acc (bv_zero_extend 32 x)) (bv_add (bv_zero_extend 32 y) (byte_sum ys))) by apply bv_add_assoc.
  rewrite Hsum. iFrame "Hs".
  rewrite Hp'. rewrite <- Haddr. iFrame.
Qed.
Print Assumptions neon_byte_loop.
