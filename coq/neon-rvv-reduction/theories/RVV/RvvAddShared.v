Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.StructAssume Reduction.RVV.RvvArithmetic Reduction.RVV.RvvSharedDefs Reduction.RVV.RvvCompactAdd.
Require Import Reduction.Generated.RVV.a800001d6.
Definition added8 (vl : bv 64) (acc src : bv 65536) : bv 65536 :=
  pack8 (fun i => if decide (Z.of_N i < bv_unsigned vl)%Z
    then bv_add (bv_extract (32*i) 32 acc) (bv_extract (32*i) 32 src)
    else bv_extract (32*i) 32 acc).
Lemma rvv_add_all_active_lanes_shared `{!islaG Σ} `{!threadG} pc
    (vl : bv 64) (mask acc src : bv 65536) :
  (bv_unsigned vl <= 8)%Z ->
  instr pc (Some a800001d6) ⊢ instr_body pc (
    rvv_loop_env ∗ "vl" ↦ᵣ RVal_Bits vl ∗
    "vr0" ↦ᵣ RVal_Bits mask ∗ "vr16" ↦ᵣ RVal_Bits src ∗ "vr8" ↦ᵣ RVal_Bits acc ∗
    instr_pre (pc+4) (
      rvv_loop_env ∗ "vl" ↦ᵣ RVal_Bits vl ∗
      "vr0" ↦ᵣ RVal_Bits mask ∗ "vr16" ↦ᵣ RVal_Bits src ∗
      "vr8" ↦ᵣ RVal_Bits (added8 vl acc src))).
Proof.
  intros Hvl. rewrite <- a800001d6_shared_exact.
  all: iStartProof.
  all: repeat kernelAStep; liShow.
  Unshelve. all: prepare_sidecond.
  all: try bv_solve.
  all: repeat match goal with Hx : context [bv_signed _] |- _ => progress bv_simplify Hx end.
  all: unfold added8, pack8; cbn [N.mul N.of_nat Z.of_N].
  all: repeat case_decide; try bv_solve; try reflexivity.
  Unshelve. all: try done.
  all: pose proof (vl_minus_one vl Hvl) as Hminus.
  all: repeat match goal with Hx : context [bv_signed ?value] |- _ =>
    progress rewrite Hminus in Hx end.
  all: repeat match goal with Hx : context [bv_signed _] |- _ => progress bv_simplify Hx end.
  all: repeat match goal with Hx : context [bv_swrap 128 ?z] |- _ =>
    progress rewrite (bv_swrap_small 128 z ltac:(change (-170141183460469231731687303715884105728 <= z < 170141183460469231731687303715884105728)%Z; lia)) in Hx end.
  all: pose proof (bv_unsigned_in_range 64 vl) as Hvlrange.
  all: first [assert (Hvalue : bv_unsigned vl = 0) by lia |
    assert (Hvalue : bv_unsigned vl = 1) by lia |
    assert (Hvalue : bv_unsigned vl = 2) by lia |
    assert (Hvalue : bv_unsigned vl = 3) by lia |
    assert (Hvalue : bv_unsigned vl = 4) by lia |
    assert (Hvalue : bv_unsigned vl = 5) by lia |
    assert (Hvalue : bv_unsigned vl = 6) by lia |
    assert (Hvalue : bv_unsigned vl = 7) by lia |
    assert (Hvalue : bv_unsigned vl = 8) by lia].
  all: unfold added8, pack8.
  all: rewrite Hvalue.
  all: repeat first [rewrite decide_True; [|lia] | rewrite decide_False; [|lia]].
  all: cbn [Z.of_N N.mul]; iFrame.
Time Qed.
Print Assumptions rvv_add_all_active_lanes_shared.
