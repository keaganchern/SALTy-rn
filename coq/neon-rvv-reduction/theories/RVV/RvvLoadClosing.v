Require Import isla.riscv64.riscv64 Reduction.RVV.RvvLoadSharedDefs Reduction.RVV.RvvUpdateExpressions
 Reduction.RVV.RvvUpdateMath Reduction.RVV.RvvLoadCaseMath Reduction.RVV.RvvTaggedCache Reduction.RVV.RvvArithmetic Reduction.RVV.RvvFreshGuard Reduction.RVV.RvvGuardFix.
Ltac unfoldGoalAliases :=
 repeat match goal with x := _ |- _ => progress unfold x end.
Ltac exposeVectorGoal :=
 rewriteVectorValues; unfoldGoalAliases;
 repeat rewrite byte_zext_self.
Ltac solveLoadCase k old f :=
 exposeVectorGoal;
 lazymatch k with
 | 0%nat => exact (load_case_value_0 old f)
 | 1%nat => exact (load_case_value_1 old f)
 | 2%nat => exact (load_case_value_2 old f)
 | 3%nat => exact (load_case_value_3 old f)
 | 4%nat => exact (load_case_value_4 old f)
 | 5%nat => exact (load_case_value_5 old f)
 | 6%nat => exact (load_case_value_6 old f)
 | 7%nat => exact (load_case_value_7 old f)
 | 8%nat => exact (load_case_value_8 old f)
 end.
