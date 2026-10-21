Require Import isla.riscv64.riscv64 Reduction.RVV.RvvDirectAssert Reduction.RVV.RvvFreshGuard Reduction.RVV.RvvGuardFix Reduction.RVV.RvvCachedSteps.
From iris.proofmode Require Import environments.
Ltac normalizePathGuards :=
 repeat first [
  match goal with H : bool_decide _ = true |- _ => apply bool_decide_eq_true in H end
 | match goal with H : bool_decide _ = false |- _ => apply bool_decide_eq_false in H end
 | match goal with H : negb _ = true |- _ => apply Bool.negb_true_iff in H end
 | match goal with H : negb _ = false |- _ => apply Bool.negb_false_iff in H end].
Ltac freshCachedAStep ::= first [progress normalizePathGuards | freshGuard | directCachedAStep].
Ltac terminalCachedAStep :=
 lazymatch goal with
 | |- envs_entails _ (WPasm tnil) => fail
 | _ => freshCachedAStep
 end.
