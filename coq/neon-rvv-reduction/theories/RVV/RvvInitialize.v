Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.RvvPrepare Reduction.RVV.RvvReduce.
From Reduction.Generated.RVV Require Import a800001bc a800001c0.

Lemma rvv_initialize `{!islaG Σ} `{!threadG}
    (oldvl oldrd : bv 64) (mask old : bv 65536) :
  instr 0x800001bc (Some a800001bc) -∗ instr 0x800001c0 (Some a800001c0) -∗
  instr_body 0x800001bc (
    rvv_final_env ∗ "vl" ↦ᵣ RVal_Bits oldvl ∗ "x14" ↦ᵣ RVal_Bits oldrd ∗
    "vr0" ↦ᵣ RVal_Bits mask ∗ "vr8" ↦ᵣ RVal_Bits old ∗
    instr_pre 0x800001c4 (
      rvv_final_env ∗ "vl" ↦ᵣ RVal_Bits (BV 64 8) ∗ "x14" ↦ᵣ RVal_Bits (BV 64 8) ∗
      "vr0" ↦ᵣ RVal_Bits mask ∗ "vr8" ↦ᵣ RVal_Bits (BV 65536 0))).
Proof.
  iIntros "#Hbc #Hc0".
  iPoseProof (rvv_capacity_x14 0x800001bc oldvl oldrd with "Hbc") as "Hcap".
  iPoseProof (rvv_zero_accumulator 0x800001c0 mask old with "Hc0") as "Hzero".
  iApply (instr_pre_wand with "Hcap"); [done|done|].
  iIntros "(Henv & Hvl & Hrd & Hmask & Hacc & Hexit)".
  iFrame "Henv Hvl Hrd".
  iApply (instr_pre_wand with "Hzero"); [done|done|].
  iIntros "(Henv & Hvl & Hrd)".
  iFrame "Henv Hvl Hmask Hacc".
  iApply (instr_pre_wand with "Hexit"); [done|done|].
  iIntros "(Henv & Hvl & Hmask & Hacc)". iFrame.
Qed.
Print Assumptions rvv_initialize.
