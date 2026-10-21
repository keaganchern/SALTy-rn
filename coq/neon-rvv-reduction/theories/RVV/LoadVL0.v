Require Import isla.riscv64.riscv64.
Require Import Reduction.RVV.RvvFastUnfold Reduction.RVV.RvvActiveCache Reduction.RVV.RvvCachedSteps Reduction.RVV.StructAssume.
Require Import Reduction.RVV.StructAssume Reduction.RVV.RvvArithmetic Reduction.RVV.RvvSharedDefs Reduction.RVV.RvvLoadSharedDefs Reduction.RVV.RvvCompactLoad Reduction.RVV.RvvCachedSteps Reduction.RVV.RvvUpdateExpressions Reduction.RVV.RvvUpdateMath Reduction.RVV.RvvFreshGuard Reduction.RVV.RvvTaggedResume Reduction.RVV.RvvGuardFix Reduction.RVV.RvvActiveCache Reduction.RVV.RvvDirectAssert Reduction.RVV.RvvAssertNormalize.
Require Import Reduction.Generated.RVV.a800001ca.
Local Opaque load_update_value_0 load_update_value_1 load_update_value_2 load_update_value_3 load_update_value_4 load_update_value_5 load_update_value_6 load_update_value_7 load_update_value_8 load_update_value_9 load_update_value_10 load_update_value_11 load_update_value_12 load_update_value_13 load_update_value_14 load_update_value_15 load_update_value_16 load_update_value_17 load_update_value_18 load_update_value_19 load_update_value_20 load_update_value_21 load_update_value_22 load_update_value_23 load_update_value_24 load_update_value_25 load_update_value_26 load_update_value_27 load_update_value_28 load_update_value_29 load_update_value_30 load_update_value_31.
Ltac lightGuard := first [
  progress normalizePathGuards
 | solve [exfalso; match goal with H : false = true |- _ => discriminate H end]
 | solve [exfalso; match goal with H : True -> False |- _ => apply H; exact I end]
 | match goal with H : context[bv_signed _] |- _ =>
   let P := type of H in
   lazymatch P with guard_seen _ => fail | _ =>
    tryif (match goal with _ : guard_seen P |- _ => idtac end) then fail else
    first [solve [exfalso; clear -H; timeout 1 (vm_compute in H; first [discriminate H | apply H; reflexivity])]
    | let marker := fresh "LIGHT_GUARD" in pose proof (guard_seen_intro P) as marker]
   end end
 ].
Ltac lightStep :=
 lazymatch goal with
 | |- environments.envs_entails _ (WPasm tnil) => fail
 | _ => try liAIntroduceLetInGoal; first [lightGuard | fastTraceUnfold | directActiveCachedVector | directCachedVector | kernelAStep]
 end.
Lemma rvv_load_inline_case_0 `{!islaG Σ} `{!threadG} pc
    (p : bv 64) (mask old : bv 65536) (f : N -> bv 8) :
  (0x80000000 <= bv_unsigned p <= 0x83fffff8)%Z ->
  instr pc (Some a800001ca) ⊢ instr_body pc (
    rvv_memory_env ∗ "vl" ↦ᵣ RVal_Bits (BV 64 0) ∗ "x11" ↦ᵣ RVal_Bits p ∗
    "vr0" ↦ᵣ RVal_Bits mask ∗ "vr2" ↦ᵣ RVal_Bits old ∗
    bv_unsigned p ↦ₘ∗ input8 f ∗
    instr_pre (pc+4) (
      rvv_memory_env ∗ "vl" ↦ᵣ RVal_Bits (BV 64 0) ∗ "x11" ↦ᵣ RVal_Bits p ∗
      "vr0" ↦ᵣ RVal_Bits mask ∗ "vr2" ↦ᵣ RVal_Bits (loaded8 (BV 64 0) old f) ∗
      bv_unsigned p ↦ₘ∗ input8 f)).
Proof.
  intros Hrange. rewrite <- a800001ca_shared_exact. iStartProof. repeat lightStep.

Show.
Require Import Reduction.RVV.RvvTaggedCache Reduction.RVV.RvvLoadClosing Reduction.RVV.RvvLoadCaseMath Reduction.RVV.RvvCompactActiveLets.
Ltac finishBoundVector k old f :=
 match goal with H : vector_value_eq ?v (load_update_value_31 _ _) |- _ =>
 let hf := fresh "FINAL_VECTOR" in
 assert (hf : v = loaded8 (BV 64 (Z.of_nat k)) old f) by (solveLoadCase k old f);
 subst v
 end.
Ltac unaliasBoolGuard :=
 match goal with H : ?b = ?v |- _ =>
   lazymatch type of b with bool => is_var b;
     let rhs := eval cbv delta [b] in b in progress change (rhs = v) in H end
 end.
all: repeat unaliasBoolGuard.
all: normalizePathGuards.
Ltac closeFixedGuard :=
 solve [exfalso; match goal with H : context [bv_signed _] |- _ =>
   clear -H; timeout 1 (vm_compute in H; first [discriminate H | apply H; reflexivity]) end].
all: try closeFixedGuard.

all: finishBoundVector 0%nat old f.
all: repeat directCachedAStep; liShow.
Unshelve. all: prepare_sidecond.
all: try bv_solve.
Unshelve. all: try done.
Show.
Qed.

Print Assumptions rvv_load_inline_case_0.
