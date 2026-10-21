Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.StructAssume.
From Reduction.Generated.RVV Require Import a800001ce a800001d0 a800001da a800001c4 a800001f6.

Definition rvv_misa `{!islaG Σ} `{!threadG} : iProp Σ :=
  "misa" ↦ᵣ RegVal_Struct [("bits", RVal_Bits (BV 64 0x8000000000200104))].
Arguments rvv_misa /.

Lemma rvv_advance `{!islaG Σ} `{!threadG} (n p vl : bv 64) :
  instr 0x800001ce (Some a800001ce) -∗ instr 0x800001d0 (Some a800001d0) -∗
  instr_body 0x800001ce (
    "x10" ↦ᵣ RVal_Bits n ∗ "x11" ↦ᵣ RVal_Bits p ∗ "x15" ↦ᵣ RVal_Bits vl ∗
    instr_pre 0x800001d2 (
      "x10" ↦ᵣ RVal_Bits (bv_sub n vl) ∗ "x11" ↦ᵣ RVal_Bits (bv_add p vl) ∗
      "x15" ↦ᵣ RVal_Bits vl)).
Proof.
  iStartProof. repeat kernelAStep; liShow.
  Unshelve. all: prepare_sidecond. all: try bv_solve.
  Unshelve. all: try done.
Qed.

Lemma rvv_backedge `{!islaG Σ} `{!threadG} (n : bv 64) :
  instr 0x800001da (Some a800001da) ⊢ instr_body 0x800001da (
    rvv_misa ∗ "x10" ↦ᵣ RVal_Bits n ∗
    instr_pre (if decide (n = BV 64 0) then 0x800001dc else 0x800001c6)
      (rvv_misa ∗ "x10" ↦ᵣ RVal_Bits n)).
Proof.
  case_decide; iStartProof; repeat kernelAStep; liShow.
  Unshelve. all: prepare_sidecond. all: try bv_solve.
  Unshelve. all: try done.
Qed.

Lemma rvv_entry_branch `{!islaG Σ} `{!threadG} (n : bv 64) :
  instr 0x800001c4 (Some a800001c4) ⊢ instr_body 0x800001c4 (
    rvv_misa ∗ "x10" ↦ᵣ RVal_Bits n ∗
    instr_pre (if decide (n = BV 64 0) then 0x800001dc else 0x800001c6)
      (rvv_misa ∗ "x10" ↦ᵣ RVal_Bits n)).
Proof.
  case_decide; iStartProof; repeat kernelAStep; liShow.
  Unshelve. all: prepare_sidecond. all: try bv_solve.
  Unshelve. all: try done.
Qed.

Lemma rvv_return `{!islaG Σ} `{!threadG} (ret : bv 64) :
  bv_and ret (BV 64 0xfffffffffffffffe) = ret ->
  instr 0x800001f6 (Some a800001f6) ⊢ instr_body 0x800001f6 (
    rvv_misa ∗ "x1" ↦ᵣ RVal_Bits ret ∗
    instr_pre (bv_unsigned ret) (rvv_misa ∗ "x1" ↦ᵣ RVal_Bits ret)).
Proof.
  intros Halign. iStartProof. repeat kernelAStep; liShow.
  Unshelve. all: prepare_sidecond. all: try bv_solve.
  Unshelve. all: try done.
all: rewrite (bv_add_0_r ret (BV 64 0) eq_refl).
  all: rewrite Halign.
  all: repeat kernelAStep; liShow.
  Unshelve. all: prepare_sidecond. all: try bv_solve.
  Unshelve. all: try done.
Qed.
Print Assumptions rvv_advance.
Print Assumptions rvv_backedge.
Print Assumptions rvv_entry_branch.
Print Assumptions rvv_return.
