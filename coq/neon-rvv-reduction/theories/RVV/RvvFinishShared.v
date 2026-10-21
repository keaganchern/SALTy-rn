Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.RvvPrepare Reduction.RVV.RvvReduceShared Reduction.RVV.RvvPackingShared Reduction.RVV.RvvPlatform Reduction.RVV.RvvWritebackFast.
From Reduction.Generated.RVV Require Import a800001bc a800001dc a800001e0 a800001e4 a800001e8
  a800001ea a800001ee a800001f2 a800001f4 a800001f6.

Lemma rvv_output_load_env `{!islaG Σ} `{!threadG} (p tmp : bv 64) (initial : bv 32) :
  (0x80000000 <= bv_unsigned p <= 0x83fffffc)%Z ->
  bv_and p (BV 64 3) = BV 64 0 ->
  instr 0x800001e8 (Some a800001e8) ⊢ instr_body 0x800001e8 (
    rvv_final_env ∗ rvv_platform_env ∗ "x12" ↦ᵣ RVal_Bits p ∗
    "x13" ↦ᵣ RVal_Bits tmp ∗ bv_unsigned p ↦ₘ initial ∗
    instr_pre 0x800001ea (
      rvv_final_env ∗ rvv_platform_env ∗ "x12" ↦ᵣ RVal_Bits p ∗
      "x13" ↦ᵣ RVal_Bits (bv_sign_extend 64 initial) ∗ bv_unsigned p ↦ₘ initial)).
Proof.
  intros Hrange Halign. iIntros "#Hi".
  iPoseProof (rvv_output_load p tmp initial Hrange Halign with "Hi") as "Hload".
  iApply (instr_pre_wand with "Hload"); [done|done|].
  iIntros "(Henv & Hplatform & Hp & Htmp & Hmem & Hexit)".
  iDestruct "Henv" as "(Helen & Hlen & Hmisa & Hzfinx & Hext & Hstatus & Hstart & Hlenb & Htype)".
  iFrame "Hplatform Hstatus Hp Htmp Hmem".
  iApply (instr_pre_wand with "Hexit"); [done|done|].
  iIntros "(Hplatform & Hstatus & Hp & Htmp & Hmem)".
  unfold rvv_final_env. iFrame.
Qed.

Lemma low32_reduced seed acc :
  bv_extract 0 32 (Reduction.RVV.RvvReduceShared.rvv_reduced8 seed acc) = rvv_sum8_seed seed acc.
Proof.
  unfold Reduction.RVV.RvvReduceShared.rvv_reduced8. rewrite (pack8_lane _ 0 ltac:(lia)). reflexivity.
Qed.

(* All instructions from the loop exit through the real return instruction. *)
Lemma rvv_finish_shared `{!islaG Σ} `{!threadG}
    (oldtype oldvl rd14 rd15 tmp13 out ret : bv 64)
    (mask seed acc : bv 65536) (initial : bv 32) :
  (oldtype = BV 64 0x90 \/ oldtype = BV 64 0xd0) ->
  (0x80000000 <= bv_unsigned out <= 0x83fffffc)%Z ->
  bv_and out (BV 64 3) = BV 64 0 ->
  bv_and ret (BV 64 0xfffffffffffffffe) = ret ->
  instr 0x800001dc (Some a800001dc) -∗ instr 0x800001e0 (Some a800001e0) -∗
  instr 0x800001e4 (Some a800001e4) -∗ instr 0x800001e8 (Some a800001e8) -∗
  instr 0x800001ea (Some a800001ea) -∗ instr 0x800001ee (Some a800001ee) -∗
  instr 0x800001f2 (Some a800001f2) -∗ instr 0x800001f4 (Some a800001f4) -∗
  instr 0x800001f6 (Some a800001f6) -∗
  instr_body 0x800001dc (
    rvv_typed_env oldtype ∗ rvv_platform_env ∗ "vl" ↦ᵣ RVal_Bits oldvl ∗
    "x14" ↦ᵣ RVal_Bits rd14 ∗ "x15" ↦ᵣ RVal_Bits rd15 ∗
    "x13" ↦ᵣ RVal_Bits tmp13 ∗ "x12" ↦ᵣ RVal_Bits out ∗ "x1" ↦ᵣ RVal_Bits ret ∗
    "vr0" ↦ᵣ RVal_Bits mask ∗ "vr1" ↦ᵣ RVal_Bits seed ∗ "vr8" ↦ᵣ RVal_Bits acc ∗
    bv_unsigned out ↦ₘ initial ∗
    instr_pre (bv_unsigned ret) (
      rvv_final_env ∗ rvv_platform_env ∗ "vl" ↦ᵣ RVal_Bits (BV 64 8) ∗
      "x14" ↦ᵣ RVal_Bits (BV 64 8) ∗
      "x15" ↦ᵣ RVal_Bits (bv_sign_extend 64 (bv_add (rvv_sum8_seed (BV 65536 0) acc) initial)) ∗
      "x13" ↦ᵣ RVal_Bits (bv_sign_extend 64 initial) ∗
      "x12" ↦ᵣ RVal_Bits out ∗ "x1" ↦ᵣ RVal_Bits ret ∗
      "vr0" ↦ᵣ RVal_Bits mask ∗ "vr1" ↦ᵣ RVal_Bits (BV 65536 0) ∗
      "vr8" ↦ᵣ RVal_Bits (Reduction.RVV.RvvReduceShared.rvv_reduced8 (BV 65536 0) acc) ∗
      bv_unsigned out ↦ₘ (bv_add (rvv_sum8_seed (BV 65536 0) acc) initial))).
Proof.
  intros Htype Hrange Halign Hret.
  iIntros "#Hdc #He0 #He4 #He8 #Hea #Hee #Hf2 #Hf4 #Hf6".
  iAssert (instr 0x800001e4 (Some a800001bc)) as "#Hcapinstr".
  { rewrite <- capacity_x14_trace_same. iExact "He4". }
  iPoseProof (rvv_capacity_x15 0x800001dc oldvl rd15 oldtype Htype with "Hdc") as "Hcap15".
  iPoseProof (rvv_zero_seed 0x800001e0 mask seed with "He0") as "Hzero".
  iPoseProof (rvv_capacity_x14 0x800001e4 (BV 64 8) rd14 with "Hcapinstr") as "Hcap14".
  iPoseProof (rvv_output_load_env out tmp13 initial Hrange Halign with "He8") as "Hload".
  iPoseProof (rvv_reduce8_shared 0x800001ea mask (BV 65536 0) acc with "Hea") as "Hreduce".
  iPoseProof (rvv_writeback_return out ret (BV 64 8) initial
    (Reduction.RVV.RvvReduceShared.rvv_reduced8 (BV 65536 0) acc) Hrange Halign Hret with "Hee Hf2 Hf4 Hf6") as "Hwrite".
  iApply (instr_pre_wand with "Hcap15"); [done|done|].
  iIntros "(Henv & Hplatform & Hvl & H14 & H15 & H13 & Hout & Hret & Hmask & Hseed & Hacc & Hmem & Hexit)".
  iFrame "Henv Hvl H15".
  iApply (instr_pre_wand with "Hzero"); [done|done|].
  iIntros "(Henv & Hvl & H15)". iFrame "Henv Hvl Hmask Hseed".
  iApply (instr_pre_wand with "Hcap14"); [done|done|].
  iIntros "(Henv & Hvl & Hmask & Hseed)". iFrame "Henv Hvl H14".
  iApply (instr_pre_wand with "Hload"); [done|done|].
  iIntros "(Henv & Hvl & H14)". iFrame "Henv Hplatform Hout H13 Hmem".
  iApply (instr_pre_wand with "Hreduce"); [done|done|].
  iIntros "(Henv & Hplatform & Hout & H13 & Hmem)". iFrame "Henv Hvl Hmask Hseed Hacc".
  iApply (instr_pre_wand with "Hwrite"); [done|done|].
  iIntros "(Henv & Hvl & Hmask & Hseed & Hacc)".
  iFrame "Henv Hplatform Hout H13 H15 Hret Hacc Hmem".
  iApply (instr_pre_wand with "Hexit"); [done|done|].
  iIntros "(Henv & Hplatform & Hout & H13 & H15 & Hret & Hacc & Hmem)".
  rewrite low32_reduced. iFrame.
Qed.
Print Assumptions rvv_output_load_env.
Print Assumptions low32_reduced.
Print Assumptions rvv_finish_shared.
