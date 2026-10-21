Require Import isla.aarch64.aarch64.
Require Import Reduction.NEON.NeonSequence Reduction.NEON.NeonProof.
From Reduction.Generated.NEON Require Import a80001000 a80001024 a80001028.

Definition q_init (q : nat -> bv 128) (i : nat) :=
  match i with 0%nat => BV 128 0 | _ => q i end.
Definition q_reduced (q : nat -> bv 128) (i : nat) :=
  match i with 0%nat => bv_concat 128 (BV 96 0) (neon_sum4 (q 0%nat)) | _ => q i end.

Lemma neon_init `{!islaG Σ} `{!threadG} q d :
  instr 0x80001000 (Some a80001000) ⊢ instr_body 0x80001000 (
    neon_env d ∗ "_V" ↦ᵣ neon_regs q ∗
    instr_pre 0x80001004 (neon_env d ∗ "_V" ↦ᵣ neon_regs (q_init q))).
Proof.
  iStartProof. liARun.
  Unshelve. all: prepare_sidecond. all: try bv_solve.
  Unshelve. all: try done.
Qed.

Lemma neon_reduce_to_scalar `{!islaG Σ} `{!threadG} q d (tmp : bv 64) :
  instr 0x80001024 (Some a80001024) -∗ instr 0x80001028 (Some a80001028) -∗
  instr_body 0x80001024 (
    neon_env d ∗ "_V" ↦ᵣ neon_regs q ∗ "R9" ↦ᵣ RVal_Bits tmp ∗
    instr_pre 0x8000102c (neon_env d ∗ "_V" ↦ᵣ neon_regs (q_reduced q) ∗
      "R9" ↦ᵣ RVal_Bits (bv_zero_extend 64 (neon_sum4 (q 0%nat))))).
Proof.
  iStartProof. liARun.
  Unshelve. all: prepare_sidecond. all: try bv_solve.
  Unshelve. all: try done.
Qed.
Print Assumptions neon_init.
Print Assumptions neon_reduce_to_scalar.
