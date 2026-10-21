Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.StructAssume.
Require Import Reduction.Generated.RVV.a800001c6.

(* This official snapshot chooses a balanced last two chunks. In particular,
   AVL=9 gives VL=5, not 8. The theorem follows the extracted semantics. *)
Definition selected_vl8 (n : Z) : Z :=
  if decide (n <= 8) then n else
  if decide (n < 16) then (n+1) `quot` 2 else 8.

Lemma signed_zext64_simple (x : bv 64) :
  bv_signed (bv_zero_extend 128 x) = bv_unsigned x.
Proof.
  rewrite bv_zero_extend_signed. apply bv_swrap_small.
  pose proof (bv_unsigned_in_range 64 x) as Hx.
  change (0 <= bv_unsigned x < 18446744073709551616) in Hx.
  change (-170141183460469231731687303715884105728 <= bv_unsigned x <
          170141183460469231731687303715884105728).
  lia.
Qed.

Lemma vsetvl8_loop_entry_and_backedge `{!islaG Σ} `{!threadG} pc
    (remaining oldvl oldrd oldtype : bv 64) (oldstart : bv 16) :
  (oldtype = BV 64 0x90 \/ oldtype = BV 64 0xd0) ->
  instr pc (Some a800001c6) ⊢ instr_body pc (
    "elen" ↦ᵣ RVal_Bits (BV 1 1) ∗
    "vlen" ↦ᵣ RVal_Bits (BV 4 3) ∗
    "misa" ↦ᵣ RegVal_Struct [("bits", RVal_Bits (BV 64 0x8000000000200104))] ∗
    "rv_enable_zfinx" ↦ᵣ RVal_Bool false ∗
    "mstatus" ↦ᵣ RegVal_Struct [("bits", RVal_Bits (BV 64 0x8000000000000600))] ∗
    "vtype" ↦ᵣ RegVal_Struct [("bits", RVal_Bits oldtype)] ∗
    "vstart" ↦ᵣ RVal_Bits oldstart ∗
    "vl" ↦ᵣ RVal_Bits oldvl ∗
    "x10" ↦ᵣ RVal_Bits remaining ∗ "x15" ↦ᵣ RVal_Bits oldrd ∗
    instr_pre (pc+4) (
      "vl" ↦ᵣ RVal_Bits (Z_to_bv 64 (selected_vl8 (bv_unsigned remaining))) ∗
      "x15" ↦ᵣ RVal_Bits (Z_to_bv 64 (selected_vl8 (bv_unsigned remaining))) ∗
      "vtype" ↦ᵣ RegVal_Struct [("bits", RVal_Bits (BV 64 0x90))] ∗
      "vstart" ↦ᵣ RVal_Bits (BV 16 0) ∗
      "elen" ↦ᵣ RVal_Bits (BV 1 1) ∗
      "vlen" ↦ᵣ RVal_Bits (BV 4 3) ∗
      "misa" ↦ᵣ RegVal_Struct [("bits", RVal_Bits (BV 64 0x8000000000200104))] ∗
      "rv_enable_zfinx" ↦ᵣ RVal_Bool false ∗
      "mstatus" ↦ᵣ RegVal_Struct [("bits", RVal_Bits (BV 64 0x8000000000000600))] ∗
      "x10" ↦ᵣ RVal_Bits remaining)).
Proof.
  intros Htype.
  destruct Htype as [-> | ->].
  all: iStartProof.
  all: repeat kernelAStep; liShow.
  Unshelve. all: prepare_sidecond.
  all: repeat match goal with
       | Hx : context [bv_signed (bv_zero_extend 128 _)] |- _ =>
           rewrite signed_zext64_simple in Hx
       end.
  all: try bv_simplify H0; try bv_simplify H1.
  all: unfold selected_vl8; repeat case_decide; try bv_solve.
  all: bv_simplify.
  Unshelve. all: try done.
Qed.

Print Assumptions vsetvl8_loop_entry_and_backedge.
