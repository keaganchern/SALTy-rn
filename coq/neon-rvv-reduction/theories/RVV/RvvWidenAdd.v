Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.RvvSharedDefs Reduction.RVV.RvvWidenShared Reduction.RVV.RvvAddShared Reduction.RVV.RvvStepMath.
From Reduction.Generated.RVV Require Import a800001d2 a800001d6.

Lemma rvv_widen_add `{!islaG Σ} `{!threadG}
    (vl : bv 64) (mask old src acc : bv 65536) :
  (bv_unsigned vl <= 8)%Z ->
  instr 0x800001d2 (Some a800001d2) -∗ instr 0x800001d6 (Some a800001d6) -∗
  instr_body 0x800001d2 (
    rvv_loop_env ∗ "vl" ↦ᵣ RVal_Bits vl ∗ "vr0" ↦ᵣ RVal_Bits mask ∗
    "vr2" ↦ᵣ RVal_Bits src ∗ "vr16" ↦ᵣ RVal_Bits old ∗ "vr8" ↦ᵣ RVal_Bits acc ∗
    instr_pre 0x800001da (
      rvv_loop_env ∗ "vl" ↦ᵣ RVal_Bits vl ∗ "vr0" ↦ᵣ RVal_Bits mask ∗
      "vr2" ↦ᵣ RVal_Bits src ∗ "vr16" ↦ᵣ RVal_Bits (widened8 vl old src) ∗
      "vr8" ↦ᵣ RVal_Bits (added_words vl acc (widened8 vl old src)))).
Proof.
  intros Hvl. iIntros "#Hw #Ha".
  iPoseProof (rvv_widen_all_active_lanes_shared 0x800001d2 vl mask old src Hvl with "Hw") as "Hwide".
  iPoseProof (rvv_add_all_active_lanes_shared 0x800001d6 vl mask acc (widened8 vl old src) Hvl with "Ha") as "Hadd".
  iApply (instr_pre_wand with "Hwide"); [done|done|].
  iIntros "(Henv & Hvl & Hmask & Hsrc & Hold & Hacc & Hexit)".
  iFrame "Henv Hvl Hmask Hsrc Hold".
  iApply (instr_pre_wand with "Hadd"); [done|done|].
  iIntros "(Henv & Hvl & Hmask & Hsrc & Hold)". iFrame "Henv Hvl Hmask Hold Hacc".
  iApply (instr_pre_wand with "Hexit"); [done|done|].
  iIntros "(Henv & Hvl & Hmask & Hold & Hacc)". iFrame.
Qed.
Print Assumptions rvv_widen_add.
