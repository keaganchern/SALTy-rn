From isla Require Import opsem.
Require Import Reduction.Generated.RVV.a800001bc.
Require Import Reduction.Generated.RVV.a800001c0.
Require Import Reduction.Generated.RVV.a800001c4.
Require Import Reduction.Generated.RVV.a800001c6.
Require Import Reduction.Generated.RVV.a800001ca.
Require Import Reduction.Generated.RVV.a800001ce.
Require Import Reduction.Generated.RVV.a800001d0.
Require Import Reduction.Generated.RVV.a800001d2.
Require Import Reduction.Generated.RVV.a800001d6.
Require Import Reduction.Generated.RVV.a800001da.
Require Import Reduction.Generated.RVV.a800001dc.
Require Import Reduction.Generated.RVV.a800001e0.
Require Import Reduction.Generated.RVV.a800001e4.
Require Import Reduction.Generated.RVV.a800001e8.
Require Import Reduction.Generated.RVV.a800001ea.
Require Import Reduction.Generated.RVV.a800001ee.
Require Import Reduction.Generated.RVV.a800001f2.
Require Import Reduction.Generated.RVV.a800001f4.
Require Import Reduction.Generated.RVV.a800001f6.

Definition rvv_kernel : gmap Z isla_trace := list_to_map [
  (2147484092%Z, a800001bc);
  (2147484096%Z, a800001c0);
  (2147484100%Z, a800001c4);
  (2147484102%Z, a800001c6);
  (2147484106%Z, a800001ca);
  (2147484110%Z, a800001ce);
  (2147484112%Z, a800001d0);
  (2147484114%Z, a800001d2);
  (2147484118%Z, a800001d6);
  (2147484122%Z, a800001da);
  (2147484124%Z, a800001dc);
  (2147484128%Z, a800001e0);
  (2147484132%Z, a800001e4);
  (2147484136%Z, a800001e8);
  (2147484138%Z, a800001ea);
  (2147484142%Z, a800001ee);
  (2147484146%Z, a800001f2);
  (2147484148%Z, a800001f4);
  (2147484150%Z, a800001f6)].

Lemma rvv_kernel_size : size rvv_kernel = 19%nat.
Proof. vm_compute. reflexivity. Qed.
