Require Import isla.aarch64.aarch64.
Require Import Reduction.Generated.Bridge.neon_uadalp16.a2105c4.

(* Exact 16-bit pair to 32-bit accumulator update from the ISA trace. *)
Definition neon_pair32_update (offset : N) (mask shift : bv 128)
    (acc src : bv 128) : bv 128 :=
  let value := bv_zero_extend 128
        (bv_add (bv_extract offset 32 acc)
          (bv_add
            (bv_extract 0 32 (bv_zero_extend 128 (bv_extract offset 16 src)))
            (bv_extract 0 32 (bv_zero_extend 128 (bv_extract (offset+16) 16 src))))) in
  bv_or (bv_and acc mask)
        (if N.eqb offset 0 then value else bv_shiftl value shift).
Definition neon_uadalp16_result (acc src : bv 128) : bv 128 :=
  let a0 := neon_pair32_update 0 (BV 128 0xffffffffffffffffffffffff00000000) (BV 128 0) acc src in
  let a1 := neon_pair32_update 32 (BV 128 0xffffffffffffffff00000000ffffffff) (BV 128 32) a0 src in
  let a2 := neon_pair32_update 64 (BV 128 0xffffffff00000000ffffffffffffffff) (BV 128 64) a1 src in
  let a3 := neon_pair32_update 96 (BV 128 0xffffffffffffffffffffffff) (BV 128 96) a2 src in
  a3.

Lemma neon_uadalp16_exact `{!islaG Σ} `{!threadG} pc (q : nat -> bv 128) :
  instr pc (Some a2105c4) ⊢ instr_body pc (
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
    "_V" ↦ᵣ RegVal_Vector [RVal_Bits (neon_uadalp16_result (q 0%nat) (q 1%nat)); RVal_Bits (q 1%nat); RVal_Bits (q 2%nat); RVal_Bits (q 3%nat); RVal_Bits (q 4%nat); RVal_Bits (q 5%nat); RVal_Bits (q 6%nat); RVal_Bits (q 7%nat); RVal_Bits (q 8%nat); RVal_Bits (q 9%nat); RVal_Bits (q 10%nat); RVal_Bits (q 11%nat); RVal_Bits (q 12%nat); RVal_Bits (q 13%nat); RVal_Bits (q 14%nat); RVal_Bits (q 15%nat); RVal_Bits (q 16%nat); RVal_Bits (q 17%nat); RVal_Bits (q 18%nat); RVal_Bits (q 19%nat); RVal_Bits (q 20%nat); RVal_Bits (q 21%nat); RVal_Bits (q 22%nat); RVal_Bits (q 23%nat); RVal_Bits (q 24%nat); RVal_Bits (q 25%nat); RVal_Bits (q 26%nat); RVal_Bits (q 27%nat); RVal_Bits (q 28%nat); RVal_Bits (q 29%nat); RVal_Bits (q 30%nat); RVal_Bits (q 31%nat)])).
Proof.
  iStartProof. repeat liAStep; liShow.
  Unshelve. all: prepare_sidecond.
  all: try reflexivity.
  Unshelve. all: try done.
Qed.
Print Assumptions neon_uadalp16_exact.
