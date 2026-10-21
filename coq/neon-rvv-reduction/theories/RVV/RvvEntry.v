Require Import isla.riscv64.riscv64 Reduction.RVV.RvvPrepare Reduction.RVV.RvvControl Reduction.RVV.RvvReduce.
From Reduction.Generated.RVV Require Import a800001c4.
Lemma rvv_entry_env `{!islaG Σ} `{!threadG} (n : bv 64) :
  instr 0x800001c4 (Some a800001c4) ⊢ instr_body 0x800001c4 (
    rvv_final_env ∗ "x10" ↦ᵣ RVal_Bits n ∗
    instr_pre (if decide (n = BV 64 0) then 0x800001dc else 0x800001c6)
      (rvv_final_env ∗ "x10" ↦ᵣ RVal_Bits n)).
Proof.
  iIntros "#Hi". iPoseProof (rvv_entry_branch n with "Hi") as "Hbranch".
  iApply (instr_pre_wand with "Hbranch"); [done|done|].
  iIntros "(Henv & Hn & Hexit)".
  iDestruct "Henv" as "(He & Hl & Hmisa & Hz & Hext & Hstatus & Hstart & Hlenb & Htype)".
  iFrame "Hmisa Hn".
  iApply (instr_pre_wand with "Hexit"); [done|done|].
  iIntros "[Hmisa Hn]". unfold rvv_final_env. iFrame.
Qed.

Print Assumptions rvv_entry_env.
