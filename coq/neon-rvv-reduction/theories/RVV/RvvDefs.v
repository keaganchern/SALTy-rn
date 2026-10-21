Require Import isla.riscv64.riscv64.
Definition rvv_loop_env `{!islaG Σ} `{!threadG} : iProp Σ :=
    "elen" ↦ᵣ (RegVal_Base (Val_Bits (BV 1%N 0x1%Z))) ∗
    "vlen" ↦ᵣ (RegVal_Base (Val_Bits (BV 4%N 0x3%Z))) ∗
    "misa" ↦ᵣ (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000200104%Z)))]) ∗
    "rv_enable_zfinx" ↦ᵣ (RegVal_Base (Val_Bool false)) ∗
    "rv_enable_vext" ↦ᵣ (RegVal_Base (Val_Bool true)) ∗
    "mstatus" ↦ᵣ (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) ∗
    "vstart" ↦ᵣ (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) ∗
    "vlenb" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0x20%Z))) ∗
    "vtype" ↦ᵣ (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x90%Z)))]).
Arguments rvv_loop_env /.
Definition pack8 (f : N -> bv 32) : bv 65536 := bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_zero_extend 65536 (f 7%N)) (BV 65536 32)) (bv_zero_extend 65536 (f 6%N))) (BV 65536 32)) (bv_zero_extend 65536 (f 5%N))) (BV 65536 32)) (bv_zero_extend 65536 (f 4%N))) (BV 65536 32)) (bv_zero_extend 65536 (f 3%N))) (BV 65536 32)) (bv_zero_extend 65536 (f 2%N))) (BV 65536 32)) (bv_zero_extend 65536 (f 1%N))) (BV 65536 32)) (bv_zero_extend 65536 (f 0%N)).
Definition widened8 (vl : bv 64) (old src : bv 65536) : bv 65536 :=
  pack8 (fun i => if decide (Z.of_N i < bv_unsigned vl)%Z
    then bv_zero_extend 32 (bv_extract (8*i) 8 src)
    else bv_extract (32*i) 32 old).
