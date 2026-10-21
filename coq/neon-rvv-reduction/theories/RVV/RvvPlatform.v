Require Import isla.riscv64.riscv64.
Definition rvv_platform_env `{!islaG Σ} `{!threadG} : iProp Σ :=
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
Arguments rvv_platform_env /.
