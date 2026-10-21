Require Import isla.riscv64.riscv64 Reduction.RVV.RvvCachedSteps Reduction.RVV.RvvFreshGuard.
From iris.proofmode Require Import environments.
Inductive vector_value_eq (x y : bv 65536) : Prop := vector_value_eq_intro : x = y -> vector_value_eq x y.
Lemma tagged_vector_definition `{!islaG Σ} `{!threadG}
    n es ann e (value : bv 65536) :
  eval_exp' e = Some (Val_Bits value) ->
  (∀ v : bv 65536, ⌜vector_value_eq v value⌝ -∗ WPasm (subst_trace (Val_Bits v) n es))
    ⊢ WPasm (Smt (DefineConst n e) ann :t: es).
Proof.
  intros Heval. iIntros "H". iApply wp_define_const.
  rewrite wp_exp_unfold. iExists (Val_Bits value). iSplit.
  - iPureIntro. apply eval_exp'_sound. exact Heval.
  - iApply "H". iPureIntro. constructor. reflexivity.
Qed.
Ltac applyCachedVector n es ann e value H ::=
  notypeclasses refine (tac_fast_apply (tagged_vector_definition n es ann e value H) _);
  let v := fresh "VEC" in iIntros (v) "%";
  idtac "tagged vector expression" v.
Print Assumptions tagged_vector_definition.
