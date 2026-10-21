Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.StructAssume Reduction.RVV.RvvReduce.
From Reduction.Generated.RVV Require Import a800001bc a800001c0 a800001dc a800001e0 a800001e4.

Definition rvv_typed_env `{!islaG Σ} `{!threadG} (ty : bv 64) : iProp Σ :=
    "elen" ↦ᵣ (RegVal_Base (Val_Bits (BV 1%N 0x1%Z))) ∗
    "vlen" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x3%Z))) ∗
    "misa" ↦ᵣ (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000200104%Z)))]) ∗
    "rv_enable_zfinx" ↦ᵣ (RegVal_Base (Val_Bool false)) ∗
    "rv_enable_vext" ↦ᵣ (RegVal_Base (Val_Bool true)) ∗
    "mstatus" ↦ᵣ (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) ∗
    "vstart" ↦ᵣ (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) ∗
    "vlenb" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0x20%Z))) ∗
    "vtype" ↦ᵣ (RegVal_Struct [("bits", RegVal_Base (Val_Bits ty))]).
Arguments rvv_typed_env /.

Lemma rvv_zero_accumulator `{!islaG Σ} `{!threadG} pc (mask old : bv 65536) :
  instr pc (Some a800001c0) ⊢ instr_body pc (
    rvv_final_env ∗ "vl" ↦ᵣ RVal_Bits (BV 64 8) ∗
    "vr0" ↦ᵣ RVal_Bits mask ∗ "vr8" ↦ᵣ RVal_Bits old ∗
    instr_pre (pc+4) (
      rvv_final_env ∗ "vl" ↦ᵣ RVal_Bits (BV 64 8) ∗
      "vr0" ↦ᵣ RVal_Bits mask ∗ "vr8" ↦ᵣ RVal_Bits (BV 65536 0))).
Proof.
  iStartProof. repeat kernelAStep; liShow.
  Unshelve. all: prepare_sidecond. all: try bv_solve.
  Unshelve. all: try done.
Qed.
Print Assumptions rvv_zero_accumulator.

Lemma rvv_zero_seed `{!islaG Σ} `{!threadG} pc (mask old : bv 65536) :
  instr pc (Some a800001e0) ⊢ instr_body pc (
    rvv_final_env ∗ "vl" ↦ᵣ RVal_Bits (BV 64 8) ∗
    "vr0" ↦ᵣ RVal_Bits mask ∗ "vr1" ↦ᵣ RVal_Bits old ∗
    instr_pre (pc+4) (
      rvv_final_env ∗ "vl" ↦ᵣ RVal_Bits (BV 64 8) ∗
      "vr0" ↦ᵣ RVal_Bits mask ∗ "vr1" ↦ᵣ RVal_Bits (BV 65536 0))).
Proof.
  iStartProof. repeat kernelAStep; liShow.
  Unshelve. all: prepare_sidecond. all: try bv_solve.
  Unshelve. all: try done.
Qed.
Print Assumptions rvv_zero_seed.

Lemma rvv_capacity_x14 `{!islaG Σ} `{!threadG} pc (oldvl oldrd : bv 64) :
  instr pc (Some a800001bc) ⊢ instr_body pc (
    rvv_final_env ∗ "vl" ↦ᵣ RVal_Bits oldvl ∗ "x14" ↦ᵣ RVal_Bits oldrd ∗
    instr_pre (pc+4) (
      rvv_final_env ∗ "vl" ↦ᵣ RVal_Bits (BV 64 8) ∗ "x14" ↦ᵣ RVal_Bits (BV 64 8))).
Proof.
  all: iStartProof.
  all: repeat kernelAStep; liShow.
  Unshelve. all: prepare_sidecond. all: try bv_solve.
  Unshelve. all: try done.
Qed.
Print Assumptions rvv_capacity_x14.

Lemma rvv_capacity_x15 `{!islaG Σ} `{!threadG} pc (oldvl oldrd oldtype : bv 64) :
  (oldtype = BV 64 0x90 \/ oldtype = BV 64 0xd0) ->
  instr pc (Some a800001dc) ⊢ instr_body pc (
    rvv_typed_env oldtype ∗ "vl" ↦ᵣ RVal_Bits oldvl ∗ "x15" ↦ᵣ RVal_Bits oldrd ∗
    instr_pre (pc+4) (
      rvv_final_env ∗ "vl" ↦ᵣ RVal_Bits (BV 64 8) ∗ "x15" ↦ᵣ RVal_Bits (BV 64 8))).
Proof.
  intros [-> | ->].
  all: iStartProof.
  all: repeat kernelAStep; liShow.
  Unshelve. all: prepare_sidecond. all: try bv_solve.
  Unshelve. all: try done.
Qed.
Print Assumptions rvv_capacity_x15.

Lemma capacity_x14_trace_same : a800001e4 = a800001bc.
Proof. reflexivity. Qed.
Print Assumptions capacity_x14_trace_same.
