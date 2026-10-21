Require Import isla.aarch64.aarch64.
Require Import Reduction.NEON.NeonKernel Reduction.NEON.NeonSequence Reduction.NEON.NeonLoop Reduction.NEON.NeonSequenceSpec Reduction.NEON.NeonTail Reduction.NEON.NeonEdges Reduction.NEON.Program.
From Reduction.Generated.NEON Require Import a80001000 a80001004 a80001008 a8000100c a80001010 a80001014 a80001018 a8000101c a80001020 a80001024 a80001028 a8000102c a80001030 a80001034 a80001038 a8000103c a80001040 a80001044 a80001048 a8000104c.

Lemma neon_program_correct `{!islaG Σ} `{!threadG}
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
      "R8" ↦ᵣ RVal_Bits (bv_zero_extend 64 (bv_add initial (bv_add (block_sum bs) (byte_sum xs)))) ∗
      "R9" ↦ᵣ RVal_Bits (bv_zero_extend 64 (bv_add (block_sum bs) (byte_sum xs))) ∗
      flags ∗ input_memory (bv_unsigned p) bs xs ∗
      bv_unsigned out ↦ₘ (bv_add initial (bv_add (block_sum bs) (byte_sum xs))))).
Proof.
  intros Htail Hrange Halign Hout Halignout.
  iIntros "#Htable".
  iAssert (instr 0x80001000 (Some a80001000)) as "#H00".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x80001004 (Some a80001004)) as "#H04".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x80001008 (Some a80001008)) as "#H08".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x8000100c (Some a8000100c)) as "#H0c".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x80001010 (Some a80001010)) as "#H10".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x80001014 (Some a80001014)) as "#H14".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x80001018 (Some a80001018)) as "#H18".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x8000101c (Some a8000101c)) as "#H1c".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x80001020 (Some a80001020)) as "#H20".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x80001024 (Some a80001024)) as "#H24".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x80001028 (Some a80001028)) as "#H28".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x8000102c (Some a8000102c)) as "#H2c".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x80001030 (Some a80001030)) as "#H30".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x80001034 (Some a80001034)) as "#H34".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x80001038 (Some a80001038)) as "#H38".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x8000103c (Some a8000103c)) as "#H3c".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x80001040 (Some a80001040)) as "#H40".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x80001044 (Some a80001044)) as "#H44".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x80001048 (Some a80001048)) as "#H48".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iAssert (instr 0x8000104c (Some a8000104c)) as "#H4c".
  { iApply (instr_intro with "Htable"); vm_compute; reflexivity. }
  iApply (neon_kernel_correct bs xs q p out retaddr scratch8 scratch9 mpidr initial d
    Htail Hrange Halign Hout Halignout with "H00 H04 H08 H0c H10 H14 H18 H1c H20 H24 H28 H2c H30 H34 H38 H3c H40 H44 H48 H4c").
  Unshelve. all: constructor; vm_compute; reflexivity.
Qed.
Print Assumptions neon_program_correct.
