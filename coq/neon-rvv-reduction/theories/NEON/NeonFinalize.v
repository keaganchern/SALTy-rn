Require Import isla.aarch64.aarch64.
Require Import Reduction.NEON.NeonSequence.
From Reduction.Generated.NEON Require Import a80001040 a80001044 a80001048 a8000104c.

Lemma neon_write_result `{!islaG Σ} `{!threadG}
    (out retaddr mpidr : bv 64) (initial sum : bv 32) (d : bv 1) :
  (0x80000000 <= bv_unsigned out <= 0x83fffffc)%Z ->
  bv_and out (BV 64 3) = BV 64 0 ->
  instr 0x80001040 (Some a80001040) -∗ instr 0x80001044 (Some a80001044) -∗
  instr 0x80001048 (Some a80001048) -∗ instr 0x8000104c (Some a8000104c) -∗
  instr_body 0x80001040 (
    neon_env d ∗ "R2" ↦ᵣ RVal_Bits out ∗ (∃ tmp : bv 64, "R8" ↦ᵣ RVal_Bits tmp) ∗
    "R9" ↦ᵣ RVal_Bits (bv_zero_extend 64 sum) ∗ "R30" ↦ᵣ RVal_Bits retaddr ∗
    "MPIDR_EL1" ↦ᵣ RVal_Bits mpidr ∗ bv_unsigned out ↦ₘ initial ∗
    instr_pre (bv_unsigned retaddr) (
      neon_env d ∗ "R2" ↦ᵣ RVal_Bits out ∗
      "R8" ↦ᵣ RVal_Bits (bv_zero_extend 64 (bv_add initial sum)) ∗
      "R9" ↦ᵣ RVal_Bits (bv_zero_extend 64 sum) ∗ "R30" ↦ᵣ RVal_Bits retaddr ∗
      "MPIDR_EL1" ↦ᵣ RVal_Bits mpidr ∗ bv_unsigned out ↦ₘ (bv_add initial sum))).
Proof.
  intros Hrange Halign. iStartProof. liARun.
  Unshelve. all: prepare_sidecond. all: try bv_solve.
  Unshelve. all: try done.
  assert (Ha : bv_unsigned LET11 = bv_unsigned out) by (unfold LET11, LET10, LET7; bv_solve).
  assert (Hv : LET8 = bv_add initial sum) by (unfold LET8; bv_solve).
  rewrite <- Ha. rewrite <- Hv. iFrame.
Qed.
Print Assumptions neon_write_result.
