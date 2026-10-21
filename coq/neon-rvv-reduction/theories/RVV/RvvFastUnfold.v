Require Import isla.riscv64.riscv64 Reduction.RVV.StructAssume Reduction.RVV.RvvRemember.
From iris.proofmode Require Import environments.
(* Use definitional conversion for local trace aliases, avoiding a separate
   Iris equivalence proof whose reflexivity check traverses the large suffix. *)
Ltac fastTraceUnfold :=
  lazymatch goal with
  | |- envs_entails ?D (WPasm ?es) =>
    is_var es;
    let body := eval cbv beta delta [es TRACE_LET] in es in
    change (envs_entails D (WPasm body));
    try clear es
  end.
Ltac fastKernelAStep := first [fastTraceUnfold | rememberVector | kernelAStep].
