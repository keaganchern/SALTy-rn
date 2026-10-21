Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.RvvPrepare Reduction.RVV.RvvSharedDefs Reduction.RVV.RvvSimpleVset Reduction.RVV.RvvControl.
From Reduction.Generated.RVV Require Import a800001c6 a800001da a800001c4.
Lemma rvv_vset_loop_env `{!islaG Σ} `{!threadG}
    (n oldvl oldrd oldtype : bv 64) :
  (oldtype = BV 64 0x90 \/ oldtype = BV 64 0xd0) ->
  instr 0x800001c6 (Some a800001c6) ⊢ instr_body 0x800001c6 (
    rvv_typed_env oldtype ∗ "vl" ↦ᵣ RVal_Bits oldvl ∗
    "x10" ↦ᵣ RVal_Bits n ∗ "x15" ↦ᵣ RVal_Bits oldrd ∗
    instr_pre 0x800001ca (
      rvv_loop_env ∗ "vl" ↦ᵣ RVal_Bits (Z_to_bv 64 (selected_vl8 (bv_unsigned n))) ∗
      "x10" ↦ᵣ RVal_Bits n ∗
      "x15" ↦ᵣ RVal_Bits (Z_to_bv 64 (selected_vl8 (bv_unsigned n))))).
Proof.
  intros Htype. iIntros "#Hi".
  iPoseProof (vsetvl8_loop_entry_and_backedge 0x800001c6 n oldvl oldrd oldtype (BV 16 0) Htype with "Hi") as "Hset".
  iApply (instr_pre_wand with "Hset"); [done|done|].
  iIntros "(Henv & Hvl & Hn & Hrd & Hexit)".
  iDestruct "Henv" as "(He & Hl & Hmisa & Hz & Hext & Hstatus & Hstart & Hlenb & Htype)".
  iFrame "He Hl Hmisa Hz Hstatus Htype Hstart Hvl Hn Hrd".
  iApply (instr_pre_wand with "Hexit"); [done|done|].
  iIntros "(Hvl & Hrd & Htype & Hstart & He & Hl & Hmisa & Hz & Hstatus & Hn)".
  unfold rvv_loop_env. iFrame.
Qed.

Lemma rvv_backedge_env `{!islaG Σ} `{!threadG} (n : bv 64) :
  instr 0x800001da (Some a800001da) ⊢ instr_body 0x800001da (
    rvv_loop_env ∗ "x10" ↦ᵣ RVal_Bits n ∗
    instr_pre (if decide (n = BV 64 0) then 0x800001dc else 0x800001c6)
      (rvv_loop_env ∗ "x10" ↦ᵣ RVal_Bits n)).
Proof.
  iIntros "#Hi". iPoseProof (rvv_backedge n with "Hi") as "Hbranch".
  iApply (instr_pre_wand with "Hbranch"); [done|done|].
  iIntros "(Henv & Hn & Hexit)".
  iDestruct "Henv" as "(He & Hl & Hmisa & Hz & Hext & Hstatus & Hstart & Hlenb & Htype)".
  iFrame "Hmisa Hn".
  iApply (instr_pre_wand with "Hexit"); [done|done|].
  iIntros "[Hmisa Hn]". unfold rvv_loop_env. iFrame.
Qed.
Print Assumptions rvv_vset_loop_env.
Print Assumptions rvv_backedge_env.
