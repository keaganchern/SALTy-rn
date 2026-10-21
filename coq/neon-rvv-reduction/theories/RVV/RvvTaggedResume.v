Require Import isla.riscv64.riscv64 Reduction.RVV.RvvCachedSteps Reduction.RVV.RvvTaggedCache Reduction.RVV.RvvFreshGuard Reduction.RVV.RvvCacheRule.
From iris.proofmode Require Import environments.
Ltac applyCachedVector n es ann e value H ::=
  notypeclasses refine (tac_fast_apply (tagged_vector_definition n es ann e value H) _);
  let v := fresh "VEC" in iIntros (v) "%";
  idtac "resumed vector expression" n v;
  liSimpl.
Ltac preserveVectorEqualities :=
  repeat match goal with
  | E : ?v = ?value |- _ =>
    lazymatch type of v with
    | bv 65536 =>
      let H := fresh "VECTOR_EQUATION" in
      assert (H : vector_value_eq v value) by (constructor; exact E); clear E
    end
  end.
