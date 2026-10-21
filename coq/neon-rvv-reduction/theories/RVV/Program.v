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

Definition rvv_program : gmap addr isla_trace := list_to_map [
  (BV 64 2147484092%Z, Reduction.Generated.RVV.a800001bc.a800001bc);
  (BV 64 2147484096%Z, Reduction.Generated.RVV.a800001c0.a800001c0);
  (BV 64 2147484100%Z, Reduction.Generated.RVV.a800001c4.a800001c4);
  (BV 64 2147484102%Z, Reduction.Generated.RVV.a800001c6.a800001c6);
  (BV 64 2147484106%Z, Reduction.Generated.RVV.a800001ca.a800001ca);
  (BV 64 2147484110%Z, Reduction.Generated.RVV.a800001ce.a800001ce);
  (BV 64 2147484112%Z, Reduction.Generated.RVV.a800001d0.a800001d0);
  (BV 64 2147484114%Z, Reduction.Generated.RVV.a800001d2.a800001d2);
  (BV 64 2147484118%Z, Reduction.Generated.RVV.a800001d6.a800001d6);
  (BV 64 2147484122%Z, Reduction.Generated.RVV.a800001da.a800001da);
  (BV 64 2147484124%Z, Reduction.Generated.RVV.a800001dc.a800001dc);
  (BV 64 2147484128%Z, Reduction.Generated.RVV.a800001e0.a800001e0);
  (BV 64 2147484132%Z, Reduction.Generated.RVV.a800001e4.a800001e4);
  (BV 64 2147484136%Z, Reduction.Generated.RVV.a800001e8.a800001e8);
  (BV 64 2147484138%Z, Reduction.Generated.RVV.a800001ea.a800001ea);
  (BV 64 2147484142%Z, Reduction.Generated.RVV.a800001ee.a800001ee);
  (BV 64 2147484146%Z, Reduction.Generated.RVV.a800001f2.a800001f2);
  (BV 64 2147484148%Z, Reduction.Generated.RVV.a800001f4.a800001f4);
  (BV 64 2147484150%Z, Reduction.Generated.RVV.a800001f6.a800001f6)].
Lemma rvv_program_size : size rvv_program = 19%nat.
Proof. vm_compute. reflexivity. Qed.
Print Assumptions rvv_program_size.
