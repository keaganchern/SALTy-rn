Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.StructAssume Reduction.RVV.RvvSharedDefs Reduction.RVV.RvvReduce.
Require Import Reduction.Generated.RVV.a800001ea.
Definition rvv_final_env `{!islaG Σ} `{!threadG} : iProp Σ :=
    "elen" ↦ᵣ (RegVal_Base (Val_Bits (BV 1%N 0x1%Z))) ∗
    "vlen" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x3%Z))) ∗
    "misa" ↦ᵣ (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000200104%Z)))]) ∗
    "rv_enable_zfinx" ↦ᵣ (RegVal_Base (Val_Bool false)) ∗
    "rv_enable_vext" ↦ᵣ (RegVal_Base (Val_Bool true)) ∗
    "mstatus" ↦ᵣ (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) ∗
    "vstart" ↦ᵣ (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) ∗
    "vlenb" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0x20%Z))) ∗
    "vtype" ↦ᵣ (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0xd0%Z)))]).
Arguments rvv_final_env /.
Definition rvv_sum8_seed (seed acc : bv 65536) : bv 32 := bv_add (bv_add (bv_add (bv_add (bv_add (bv_add (bv_add (bv_add (bv_extract 0 32 seed) (bv_extract 0 32 acc)) (bv_extract 32 32 acc)) (bv_extract 64 32 acc)) (bv_extract 96 32 acc)) (bv_extract 128 32 acc)) (bv_extract 160 32 acc)) (bv_extract 192 32 acc)) (bv_extract 224 32 acc).

Definition rvv_reduced8 (seed acc : bv 65536) : bv 65536 :=
  pack8 (fun i => match i with 0%N => rvv_sum8_seed seed acc | _ => bv_extract (32*i) 32 acc end).
Lemma rvv_reduce8_shared `{!islaG Σ} `{!threadG} pc (mask seed acc : bv 65536) :
  instr pc (Some a800001ea) ⊢ instr_body pc (
    rvv_final_env ∗ "vl" ↦ᵣ RVal_Bits (BV 64 8) ∗
    "vr0" ↦ᵣ RVal_Bits mask ∗ "vr1" ↦ᵣ RVal_Bits seed ∗ "vr8" ↦ᵣ RVal_Bits acc ∗
    instr_pre (pc+4) (
      rvv_final_env ∗ "vl" ↦ᵣ RVal_Bits (BV 64 8) ∗
      "vr0" ↦ᵣ RVal_Bits mask ∗ "vr1" ↦ᵣ RVal_Bits seed ∗
      "vr8" ↦ᵣ RVal_Bits (rvv_reduced8 seed acc))).
Proof.
  exact (Reduction.RVV.RvvReduce.rvv_reduce8 pc mask seed acc).
Qed.
Print Assumptions rvv_reduce8_shared.
