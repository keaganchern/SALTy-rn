Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.StructAssume Reduction.RVV.RvvPlatform Reduction.RVV.RvvReduce.
From Reduction.Generated.RVV Require Import a800001e8 a800001ee a800001f2 a800001f4 a800001f6.

Lemma extract_sext32 (x : bv 32) : bv_extract 0 32 (bv_sign_extend 64 x) = x.
Proof. bv_solve. Qed.

Lemma rvv_output_load `{!islaG Σ} `{!threadG} (p tmp : bv 64) (initial : bv 32) :
  (0x80000000 <= bv_unsigned p <= 0x83fffffc)%Z ->
  bv_and p (BV 64 3) = BV 64 0 ->
  instr 0x800001e8 (Some a800001e8) ⊢ instr_body 0x800001e8 (
    rvv_platform_env ∗
    "mstatus" ↦ᵣ RegVal_Struct [("bits", RVal_Bits (BV 64 0x8000000000000600))] ∗
    "x12" ↦ᵣ RVal_Bits p ∗ "x13" ↦ᵣ RVal_Bits tmp ∗ bv_unsigned p ↦ₘ initial ∗
    instr_pre 0x800001ea (
      rvv_platform_env ∗
      "mstatus" ↦ᵣ RegVal_Struct [("bits", RVal_Bits (BV 64 0x8000000000000600))] ∗
      "x12" ↦ᵣ RVal_Bits p ∗ "x13" ↦ᵣ RVal_Bits (bv_sign_extend 64 initial) ∗
      bv_unsigned p ↦ₘ initial)).
Proof.
  intros Hrange Halign. iStartProof. repeat kernelAStep; liShow.
  Unshelve. all: prepare_sidecond. all: try bv_solve.
  Unshelve. all: try done.
assert (Ha : bv_unsigned LET0 = bv_unsigned p) by (unfold LET0; bv_solve).
  rewrite <- Ha. iFrame.
Qed.

Lemma rvv_writeback_return `{!islaG Σ} `{!threadG}
    (out ret tmp : bv 64) (initial : bv 32) (acc : bv 65536) :
  (0x80000000 <= bv_unsigned out <= 0x83fffffc)%Z ->
  bv_and out (BV 64 3) = BV 64 0 ->
  bv_and ret (BV 64 0xfffffffffffffffe) = ret ->
  instr 0x800001ee (Some a800001ee) -∗ instr 0x800001f2 (Some a800001f2) -∗
  instr 0x800001f4 (Some a800001f4) -∗ instr 0x800001f6 (Some a800001f6) -∗
  instr_body 0x800001ee (
    rvv_final_env ∗ rvv_platform_env ∗
    "x12" ↦ᵣ RVal_Bits out ∗ "x13" ↦ᵣ RVal_Bits (bv_sign_extend 64 initial) ∗
    "x15" ↦ᵣ RVal_Bits tmp ∗ "x1" ↦ᵣ RVal_Bits ret ∗ "vr8" ↦ᵣ RVal_Bits acc ∗
    bv_unsigned out ↦ₘ initial ∗
    instr_pre (bv_unsigned ret) (
      rvv_final_env ∗ rvv_platform_env ∗
      "x12" ↦ᵣ RVal_Bits out ∗ "x13" ↦ᵣ RVal_Bits (bv_sign_extend 64 initial) ∗
      "x15" ↦ᵣ RVal_Bits (bv_sign_extend 64 (bv_add (bv_extract 0 32 acc) initial)) ∗
      "x1" ↦ᵣ RVal_Bits ret ∗ "vr8" ↦ᵣ RVal_Bits acc ∗
      bv_unsigned out ↦ₘ (bv_add (bv_extract 0 32 acc) initial))).
Proof.
  intros Hrange Halign Hret. iStartProof. repeat kernelAStep; liShow.
  Unshelve. all: prepare_sidecond. all: try bv_solve.
  Unshelve. all: try done.
  all: try (rewrite (bv_add_0_r ret (BV 64 0) eq_refl); rewrite Hret;
    repeat kernelAStep; liShow).
  Unshelve. all: prepare_sidecond. all: try (rewrite !extract_sext32; reflexivity).
  Unshelve. all: try done.
  all: assert (Ha : bv_unsigned LET4 = bv_unsigned out) by (unfold LET4; bv_solve).
  all: assert (Hv : LET5 = bv_add (bv_extract 0 32 acc) initial) by
    (unfold LET5, LET2, LET0; rewrite !extract_sext32; reflexivity).
  all: rewrite <- Ha. all: rewrite <- Hv. all: iFrame.
Qed.
Print Assumptions rvv_output_load.
Print Assumptions rvv_writeback_return.
