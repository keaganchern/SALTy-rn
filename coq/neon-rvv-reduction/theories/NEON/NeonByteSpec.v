Require Import isla.aarch64.aarch64.
Require Import Reduction.NEON.NeonProgram Reduction.NEON.NeonKernel Reduction.NEON.NeonSequence Reduction.NEON.NeonLoop Reduction.NEON.NeonSequenceSpec Reduction.NEON.NeonTail Reduction.NEON.NeonEdges Reduction.NEON.Program Reduction.NEON.KernelSpec.

Lemma neon_program_byte_spec `{!islaG Σ} `{!threadG}
    (bs : list block) (xs : list (bv 8)) (q : nat -> bv 128)
    (p out retaddr scratch8 scratch9 mpidr : bv 64) (initial : bv 32) (d : bv 1) :
  (Z.of_nat (length xs) < 16)%Z ->
  (0x80000000 <= bv_unsigned p /\
    bv_unsigned p + 16 * Z.of_nat (length bs) + Z.of_nat (length xs) <= 0x84000000)%Z ->
  (bv_unsigned p mod 16 = 0)%Z ->
  (0x80000000 <= bv_unsigned out <= 0x83fffffc)%Z ->
  bv_and out (BV 64 3) = BV 64 0 ->
  instr_table neon_program ⊢
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
      "R8" ↦ᵣ RVal_Bits (bv_zero_extend 64 (byte_reduction_spec initial (flatten_blocks bs ++ xs))) ∗
      "R9" ↦ᵣ RVal_Bits (bv_zero_extend 64 (bv_add (block_sum bs) (byte_sum xs))) ∗
      flags ∗ input_memory (bv_unsigned p) bs xs ∗
      bv_unsigned out ↦ₘ (byte_reduction_spec initial (flatten_blocks bs ++ xs)))).
Proof.
  intros Htail Hrange Halign Hout Halignout.
  rewrite <- neon_kernel_output_is_byte_spec.
  apply neon_program_correct; assumption.
Qed.
Print Assumptions neon_program_byte_spec.
