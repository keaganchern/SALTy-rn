Require Import isla.aarch64.aarch64.
Require Import Reduction.Generated.NEON.a80001010.

Lemma neon_zero_half_accumulator `{!islaG Σ} `{!threadG} pc (q : nat -> bv 128) :
  instr pc (Some a80001010) ⊢ instr_body pc (
    "HCR_EL2" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0x80000000%Z))) ∗
    "CFG_ID_AA64PFR0_EL1_EL3" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) ∗
    "CFG_ID_AA64PFR0_EL1_EL2" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) ∗
    "CFG_ID_AA64PFR0_EL1_EL1" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) ∗
    "CFG_ID_AA64PFR0_EL1_EL0" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) ∗
    "CPTR_EL3" ↦ᵣ (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) ∗
    "CPTR_EL2" ↦ᵣ (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) ∗
    "PSTATE" # "EL" ↦ᵣ (RegVal_Base (Val_Bits (BV 2%N 0x2%Z))) ∗
    "PSTATE" # "nRW" ↦ᵣ (RegVal_Base (Val_Bits (BV 1%N 0x0%Z))) ∗
    "SCR_EL3" ↦ᵣ (RegVal_Base (Val_Bits (BV 32%N 0x501%Z))) ∗
    "_V" ↦ᵣ RegVal_Vector [RVal_Bits (q 0%nat); RVal_Bits (q 1%nat); RVal_Bits (q 2%nat); RVal_Bits (q 3%nat); RVal_Bits (q 4%nat); RVal_Bits (q 5%nat); RVal_Bits (q 6%nat); RVal_Bits (q 7%nat); RVal_Bits (q 8%nat); RVal_Bits (q 9%nat); RVal_Bits (q 10%nat); RVal_Bits (q 11%nat); RVal_Bits (q 12%nat); RVal_Bits (q 13%nat); RVal_Bits (q 14%nat); RVal_Bits (q 15%nat); RVal_Bits (q 16%nat); RVal_Bits (q 17%nat); RVal_Bits (q 18%nat); RVal_Bits (q 19%nat); RVal_Bits (q 20%nat); RVal_Bits (q 21%nat); RVal_Bits (q 22%nat); RVal_Bits (q 23%nat); RVal_Bits (q 24%nat); RVal_Bits (q 25%nat); RVal_Bits (q 26%nat); RVal_Bits (q 27%nat); RVal_Bits (q 28%nat); RVal_Bits (q 29%nat); RVal_Bits (q 30%nat); RVal_Bits (q 31%nat)] ∗
    instr_pre (pc+4) (
    "HCR_EL2" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0x80000000%Z))) ∗
    "CFG_ID_AA64PFR0_EL1_EL3" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) ∗
    "CFG_ID_AA64PFR0_EL1_EL2" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) ∗
    "CFG_ID_AA64PFR0_EL1_EL1" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) ∗
    "CFG_ID_AA64PFR0_EL1_EL0" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) ∗
    "CPTR_EL3" ↦ᵣ (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) ∗
    "CPTR_EL2" ↦ᵣ (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) ∗
    "PSTATE" # "EL" ↦ᵣ (RegVal_Base (Val_Bits (BV 2%N 0x2%Z))) ∗
    "PSTATE" # "nRW" ↦ᵣ (RegVal_Base (Val_Bits (BV 1%N 0x0%Z))) ∗
    "SCR_EL3" ↦ᵣ (RegVal_Base (Val_Bits (BV 32%N 0x501%Z))) ∗
    "_V" ↦ᵣ RegVal_Vector [RVal_Bits (q 0%nat); RVal_Bits (BV 128 0); RVal_Bits (q 2%nat); RVal_Bits (q 3%nat); RVal_Bits (q 4%nat); RVal_Bits (q 5%nat); RVal_Bits (q 6%nat); RVal_Bits (q 7%nat); RVal_Bits (q 8%nat); RVal_Bits (q 9%nat); RVal_Bits (q 10%nat); RVal_Bits (q 11%nat); RVal_Bits (q 12%nat); RVal_Bits (q 13%nat); RVal_Bits (q 14%nat); RVal_Bits (q 15%nat); RVal_Bits (q 16%nat); RVal_Bits (q 17%nat); RVal_Bits (q 18%nat); RVal_Bits (q 19%nat); RVal_Bits (q 20%nat); RVal_Bits (q 21%nat); RVal_Bits (q 22%nat); RVal_Bits (q 23%nat); RVal_Bits (q 24%nat); RVal_Bits (q 25%nat); RVal_Bits (q 26%nat); RVal_Bits (q 27%nat); RVal_Bits (q 28%nat); RVal_Bits (q 29%nat); RVal_Bits (q 30%nat); RVal_Bits (q 31%nat)])).
Proof.
  iStartProof. repeat liAStep; liShow.
  Unshelve. all: prepare_sidecond.
  all: try reflexivity.
  Unshelve. all: try done.
Time Qed.
Print Assumptions neon_zero_half_accumulator.
