Require Import isla.aarch64.aarch64.
Require Import Reduction.Generated.NEON.a8000100c Reduction.Generated.NEON.a80001010 Reduction.Generated.NEON.a80001014 Reduction.Generated.NEON.a80001018.
Require Import Reduction.NEON.NeonPairProof Reduction.NEON.NeonWordProof Reduction.NEON.NeonLoadProof Reduction.NEON.NeonZero Reduction.NEON.MemoryBridge.

Definition neon_env `{!islaG Σ} `{!threadG} (d : bv 1) : iProp Σ :=
  "HCR_EL2" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0x80000000%Z))) ∗
    "CFG_ID_AA64PFR0_EL1_EL3" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) ∗
    "CFG_ID_AA64PFR0_EL1_EL2" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) ∗
    "CFG_ID_AA64PFR0_EL1_EL1" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) ∗
    "CFG_ID_AA64PFR0_EL1_EL0" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) ∗
    "TCR_EL2" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0x0%Z))) ∗
    "CPTR_EL3" ↦ᵣ (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) ∗
    "CPTR_EL2" ↦ᵣ (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) ∗
    "EDSCR" ↦ᵣ (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) ∗
    "OSDLR_EL1" ↦ᵣ (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) ∗
    "OSLSR_EL1" ↦ᵣ (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) ∗
    "PSTATE" # "EL" ↦ᵣ (RegVal_Base (Val_Bits (BV 2%N 0x2%Z))) ∗
    "PSTATE" # "nRW" ↦ᵣ (RegVal_Base (Val_Bits (BV 1%N 0x0%Z))) ∗
    "SCR_EL3" ↦ᵣ (RegVal_Base (Val_Bits (BV 32%N 0x501%Z))) ∗
    "SCTLR_EL2" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0x4000002%Z))) ∗
    "PSTATE" # "D" ↦ᵣ RVal_Bits d.
Definition neon_regs (q : nat -> bv 128) : valu := RegVal_Vector [RVal_Bits (q 0%nat); RVal_Bits (q 1%nat); RVal_Bits (q 2%nat); RVal_Bits (q 3%nat); RVal_Bits (q 4%nat); RVal_Bits (q 5%nat); RVal_Bits (q 6%nat); RVal_Bits (q 7%nat); RVal_Bits (q 8%nat); RVal_Bits (q 9%nat); RVal_Bits (q 10%nat); RVal_Bits (q 11%nat); RVal_Bits (q 12%nat); RVal_Bits (q 13%nat); RVal_Bits (q 14%nat); RVal_Bits (q 15%nat); RVal_Bits (q 16%nat); RVal_Bits (q 17%nat); RVal_Bits (q 18%nat); RVal_Bits (q 19%nat); RVal_Bits (q 20%nat); RVal_Bits (q 21%nat); RVal_Bits (q 22%nat); RVal_Bits (q 23%nat); RVal_Bits (q 24%nat); RVal_Bits (q 25%nat); RVal_Bits (q 26%nat); RVal_Bits (q 27%nat); RVal_Bits (q 28%nat); RVal_Bits (q 29%nat); RVal_Bits (q 30%nat); RVal_Bits (q 31%nat)].
Arguments neon_env /.
Arguments neon_regs /.

Definition after_load_pair (q : nat -> bv 128) (low high : bv 64) (i : nat) : bv 128 :=
  let bytes := bv_concat 128 high low in
  let halves := neon_uadalp8_result (BV 128 0) bytes in
  match i with
  | 0%nat => neon_uadalp16_result (q 0%nat) halves
  | 1%nat => halves
  | 2%nat => bytes
  | _ => q i
  end.

Definition q_loaded (q : nat -> bv 128) (low high : bv 64) (i : nat) :=
  if Nat.eqb i 2 then bv_concat 128 high low else q i.
Definition q_zeroed (q : nat -> bv 128) (i : nat) :=
  if Nat.eqb i 1 then BV 128 0 else q i.
Definition q_paired (q : nat -> bv 128) (i : nat) :=
  if Nat.eqb i 1 then neon_uadalp8_result (q 1%nat) (q 2%nat) else q i.

Local Opaque neon_uadalp8_result neon_uadalp16_result.

(* Compose the actual load/zero/pair/accumulate traces with checked contracts. *)
Lemma neon_load_widen_accumulate `{!islaG Σ} `{!threadG}
    (q : nat -> bv 128) (address low high : bv 64) (d : bv 1) :
  (0x80000000 <= bv_unsigned address <= 0x83fffff0)%Z ->
  (bv_unsigned address mod 16 = 0)%Z ->
  instr 0x8000100c (Some a8000100c) -∗
  instr 0x80001010 (Some a80001010) -∗
  instr 0x80001014 (Some a80001014) -∗
  instr 0x80001018 (Some a80001018) -∗
  instr_body 0x8000100c (
    neon_env d ∗ "R1" ↦ᵣ RVal_Bits address ∗
    "_V" ↦ᵣ neon_regs q ∗
    bv_unsigned address ↦ₘ low ∗ (bv_unsigned address + 8) ↦ₘ high ∗
    instr_pre 0x8000101c (
      neon_env d ∗ "R1" ↦ᵣ RVal_Bits (bv_add address (BV 64 16)) ∗
      "_V" ↦ᵣ neon_regs (after_load_pair q low high) ∗
      bv_unsigned address ↦ₘ low ∗ (bv_unsigned address + 8) ↦ₘ high)).
Proof.
  intros Hrange Halign.
  iIntros "#Hload #Hzero #Hpair #Hword".
  iPoseProof (neon_load16_exact 0x8000100c q address low high d Hrange Halign with "Hload") as "Hload_spec".
  iPoseProof (neon_zero_half_accumulator 0x80001010 (q_loaded q low high) with "Hzero") as "Hzero_spec".
  iPoseProof (neon_uadalp8_exact 0x80001014 (q_zeroed (q_loaded q low high)) with "Hpair") as "Hpair_spec".
  iPoseProof (neon_uadalp16_exact 0x80001018 (q_paired (q_zeroed (q_loaded q low high))) with "Hword") as "Hword_spec".
  iApply (instr_pre_wand with "Hload_spec"); [done|done|].
  iIntros "(Henv & HR1 & HV & Hlow & Hhigh & Hexit)".
  iDestruct "Henv" as "(?&?&?&?&?&?&?&?&?&?&?&?&?&?&?&?)".
  iFrame.
  iApply (instr_pre_wand with "Hzero_spec"); [done|done|].
  iIntros "(?&?&?&?&?&?&?&?&?&?&?&?&?&?&?&?&?&?&?&?)".
  iFrame.
  iApply (instr_pre_wand with "Hpair_spec"); [done|done|].
  iIntros "(?&?&?&?&?&?&?&?&?&?&?)".
  iFrame.
  iApply (instr_pre_wand with "Hword_spec"); [done|done|].
  iIntros "(?&?&?&?&?&?&?&?&?&?&?)".
  iFrame.
  iApply (instr_pre_wand with "Hexit"); [done|done|].
  iIntros "(?&?&?&?&?&?&?&?&?&?&?)".
  iFrame.
Qed.
Print Assumptions neon_load_widen_accumulate.
