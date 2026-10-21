Require Import isla.riscv64.riscv64 Reduction.RVV.RvvActiveCache Reduction.RVV.RvvTaggedResume Reduction.RVV.RvvGuardFix Reduction.RVV.RvvCachedSteps Reduction.RVV.RvvFastUnfold Reduction.RVV.StructAssume.
From iris.proofmode Require Import environments.
Lemma direct_assert_rule `{!islaG Σ} `{!threadG} es ann e b :
 eval_exp' e = Some (Val_Bool b) ->
 (⌜b = true⌝ -∗ WPasm es) ⊢ WPasm (Smt (Assert e) ann :t: es).
Proof.
 intros He. iIntros "H". iApply wp_assert.
 rewrite wp_exp_unfold. iExists (Val_Bool b). iSplit.
 - iPureIntro. apply eval_exp'_sound. exact He.
 - iExists b. iSplit; [done|]. iExact "H".
Qed.
Print Assumptions direct_assert_rule.
Ltac directAssert :=
 lazymatch goal with
 | |- envs_entails _ (WPasm (Smt (Assert ?e) ?ann :t: ?es)) =>
 let res := eval lazy [eval_exp' mapM mbind option_bind eval_unop eval_manyop eval_binop option_fmap option_map fmap mret option_ret guard_or mthrow option_mfail foldl bvn_to_bv decide decide_rel BinNat.N.eq_dec N.eq_dec N_rec N_rect bvn_n sumbool_rec sumbool_rect BinPos.Pos.eq_dec Pos.eq_dec positive_rect positive_rec eq_rect eq_ind_r eq_ind eq_sym bvn_val N.add N.sub Pos.add Pos.succ Pos.sub_mask Pos.double_mask Pos.succ_double_mask Pos.pred_double Pos.double_pred_mask] in (eval_exp' e) in
 lazymatch res with
 | Some (Val_Bool ?b) =>
   notypeclasses refine (tac_fast_apply (direct_assert_rule es ann e b eq_refl) _);
   let h := fresh "PATH_GUARD" in iIntros (h); liSimpl
 end
 end.
Ltac directCachedAStep ::= first [fastTraceUnfold | directAssert | directActiveCachedVector | directCachedVector | kernelAStep].
