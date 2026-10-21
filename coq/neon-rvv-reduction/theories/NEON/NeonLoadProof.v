Require Import isla.aarch64.aarch64.
Require Import Reduction.Generated.Bridge.neon_load_ram.a210604.
Require Import Reduction.NEON.MemoryBridge.


Lemma neon_load16_exact `{!islaG Σ} `{!threadG} pc (q : nat -> bv 128)
    (address low high : bv 64) (d : bv 1) :
  (0x80000000 <= bv_unsigned address <= 0x83fffff0)%Z ->
  (bv_unsigned address mod 16 = 0)%Z ->
  instr pc (Some a210604) ⊢ instr_body pc (
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
    "PSTATE" # "D" ↦ᵣ RVal_Bits d ∗
    "R1" ↦ᵣ RVal_Bits address ∗
    "_V" ↦ᵣ RegVal_Vector [RVal_Bits (q 0%nat); RVal_Bits (q 1%nat); RVal_Bits (q 2%nat); RVal_Bits (q 3%nat); RVal_Bits (q 4%nat); RVal_Bits (q 5%nat); RVal_Bits (q 6%nat); RVal_Bits (q 7%nat); RVal_Bits (q 8%nat); RVal_Bits (q 9%nat); RVal_Bits (q 10%nat); RVal_Bits (q 11%nat); RVal_Bits (q 12%nat); RVal_Bits (q 13%nat); RVal_Bits (q 14%nat); RVal_Bits (q 15%nat); RVal_Bits (q 16%nat); RVal_Bits (q 17%nat); RVal_Bits (q 18%nat); RVal_Bits (q 19%nat); RVal_Bits (q 20%nat); RVal_Bits (q 21%nat); RVal_Bits (q 22%nat); RVal_Bits (q 23%nat); RVal_Bits (q 24%nat); RVal_Bits (q 25%nat); RVal_Bits (q 26%nat); RVal_Bits (q 27%nat); RVal_Bits (q 28%nat); RVal_Bits (q 29%nat); RVal_Bits (q 30%nat); RVal_Bits (q 31%nat)] ∗
    bv_unsigned address ↦ₘ low ∗
    (bv_unsigned address + 8) ↦ₘ high ∗
    instr_pre (pc+4) (
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
      "PSTATE" # "D" ↦ᵣ RVal_Bits d ∗
      "R1" ↦ᵣ RVal_Bits (bv_add address (BV 64 16)) ∗
      "_V" ↦ᵣ RegVal_Vector [RVal_Bits (q 0%nat); RVal_Bits (q 1%nat); RVal_Bits (bv_concat 128 high low); RVal_Bits (q 3%nat); RVal_Bits (q 4%nat); RVal_Bits (q 5%nat); RVal_Bits (q 6%nat); RVal_Bits (q 7%nat); RVal_Bits (q 8%nat); RVal_Bits (q 9%nat); RVal_Bits (q 10%nat); RVal_Bits (q 11%nat); RVal_Bits (q 12%nat); RVal_Bits (q 13%nat); RVal_Bits (q 14%nat); RVal_Bits (q 15%nat); RVal_Bits (q 16%nat); RVal_Bits (q 17%nat); RVal_Bits (q 18%nat); RVal_Bits (q 19%nat); RVal_Bits (q 20%nat); RVal_Bits (q 21%nat); RVal_Bits (q 22%nat); RVal_Bits (q 23%nat); RVal_Bits (q 24%nat); RVal_Bits (q 25%nat); RVal_Bits (q 26%nat); RVal_Bits (q 27%nat); RVal_Bits (q 28%nat); RVal_Bits (q 29%nat); RVal_Bits (q 30%nat); RVal_Bits (q 31%nat)] ∗
      bv_unsigned address ↦ₘ low ∗
      (bv_unsigned address + 8) ↦ₘ high)).
Proof.
  intros Hrange Halign.
  iStartProof. repeat liAStep; liShow.
  Unshelve. all: prepare_sidecond.
  all: try bv_solve.
  all: try (apply aligned16_mask; exact Halign).
  all: try (rewrite loaded_pair_concat; reflexivity).
  all: try reflexivity.
  Unshelve. all: try (repeat liAStep; liShow).
  Unshelve. all: prepare_sidecond.
  all: try bv_solve.
  Unshelve.
  assert (Haddr : bv_unsigned LET4 = (bv_unsigned address + 8)%Z).
  { unfold LET4, LET3, LET2. bv_solve. }
  rewrite <- Haddr. iFrame.
Qed.
Print Assumptions neon_load16_exact.
