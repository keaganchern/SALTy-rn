Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.RvvSharedDefs Reduction.RVV.RvvLiterals Reduction.RVV.RvvLoadDefs.
Definition rvv_memory_env `{!islaG Σ} `{!threadG} : iProp Σ :=
  rvv_loop_env ∗
    "cur_privilege" ↦ᵣ (RegVal_Base (Val_Enum "Machine")) ∗
    "rv_pmp_count" ↦ᵣ (RegVal_I 0%Z 64%Z) ∗
    "rv_enable_misaligned_access" ↦ᵣ (RegVal_Base (Val_Bool false)) ∗
    "rv_ram_base" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0x80000000%Z))) ∗
    "rv_ram_size" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0x4000000%Z))) ∗
    "rv_rom_base" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0x1000%Z))) ∗
    "rv_rom_size" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0x100%Z))) ∗
    "rv_clint_base" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0x2000000%Z))) ∗
    "rv_clint_size" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0xc0000%Z))) ∗
    "rv_htif_tohost" ↦ᵣ (RegVal_Base (Val_Bits (BV 64%N 0x40001000%Z))).
Arguments rvv_memory_env /.
Definition pack32bytes (f : N -> bv 8) : bv 65536 := bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_or (bv_shiftl (bv_zero_extend 65536 (f 31%N)) wide8) (bv_zero_extend 65536 (f 30%N))) wide8) (bv_zero_extend 65536 (f 29%N))) wide8) (bv_zero_extend 65536 (f 28%N))) wide8) (bv_zero_extend 65536 (f 27%N))) wide8) (bv_zero_extend 65536 (f 26%N))) wide8) (bv_zero_extend 65536 (f 25%N))) wide8) (bv_zero_extend 65536 (f 24%N))) wide8) (bv_zero_extend 65536 (f 23%N))) wide8) (bv_zero_extend 65536 (f 22%N))) wide8) (bv_zero_extend 65536 (f 21%N))) wide8) (bv_zero_extend 65536 (f 20%N))) wide8) (bv_zero_extend 65536 (f 19%N))) wide8) (bv_zero_extend 65536 (f 18%N))) wide8) (bv_zero_extend 65536 (f 17%N))) wide8) (bv_zero_extend 65536 (f 16%N))) wide8) (bv_zero_extend 65536 (f 15%N))) wide8) (bv_zero_extend 65536 (f 14%N))) wide8) (bv_zero_extend 65536 (f 13%N))) wide8) (bv_zero_extend 65536 (f 12%N))) wide8) (bv_zero_extend 65536 (f 11%N))) wide8) (bv_zero_extend 65536 (f 10%N))) wide8) (bv_zero_extend 65536 (f 9%N))) wide8) (bv_zero_extend 65536 (f 8%N))) wide8) (bv_zero_extend 65536 (f 7%N))) wide8) (bv_zero_extend 65536 (f 6%N))) wide8) (bv_zero_extend 65536 (f 5%N))) wide8) (bv_zero_extend 65536 (f 4%N))) wide8) (bv_zero_extend 65536 (f 3%N))) wide8) (bv_zero_extend 65536 (f 2%N))) wide8) (bv_zero_extend 65536 (f 1%N))) wide8) (bv_zero_extend 65536 (f 0%N)).

Definition loaded8 (vl : bv 64) (old : bv 65536) (f : N -> bv 8) : bv 65536 :=
  pack32bytes (fun i => if decide (Z.of_N i < bv_unsigned vl)%Z
    then f i else bv_extract (8*i) 8 old).
Definition input8 (f : N -> bv 8) := [f 0%N;f 1%N;f 2%N;f 3%N;f 4%N;f 5%N;f 6%N;f 7%N].

Lemma shared_loaded8_exact vl old f : loaded8 vl old f = Reduction.RVV.RvvLoadDefs.loaded8 vl old f.
Proof. reflexivity. Qed.
Print Assumptions shared_loaded8_exact.
