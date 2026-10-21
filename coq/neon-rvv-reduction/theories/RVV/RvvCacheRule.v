Require Import isla.riscv64.riscv64.
From iris.proofmode Require Import environments.
Lemma cached_vector_definition `{!islaG Σ} `{!threadG}
    n es ann e (value : bv 65536) :
  eval_exp' e = Some (Val_Bits value) ->
  (∀ v : bv 65536, ⌜v = value⌝ -∗ WPasm (subst_trace (Val_Bits v) n es))
    ⊢ WPasm (Smt (DefineConst n e) ann :t: es).
Proof.
  intros Heval. iIntros "H". iApply wp_define_const.
  rewrite wp_exp_unfold. iExists (Val_Bits value). iSplit.
  - iPureIntro. apply eval_exp'_sound. exact Heval.
  - iApply "H". done.
Qed.
Print Assumptions cached_vector_definition.
