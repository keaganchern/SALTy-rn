From isla Require Import opsem.
Require Import Reduction.Generated.NEON.a80001000.
Require Import Reduction.Generated.NEON.a80001004.
Require Import Reduction.Generated.NEON.a80001008.
Require Import Reduction.Generated.NEON.a8000100c.
Require Import Reduction.Generated.NEON.a80001010.
Require Import Reduction.Generated.NEON.a80001014.
Require Import Reduction.Generated.NEON.a80001018.
Require Import Reduction.Generated.NEON.a8000101c.
Require Import Reduction.Generated.NEON.a80001020.
Require Import Reduction.Generated.NEON.a80001024.
Require Import Reduction.Generated.NEON.a80001028.
Require Import Reduction.Generated.NEON.a8000102c.
Require Import Reduction.Generated.NEON.a80001030.
Require Import Reduction.Generated.NEON.a80001034.
Require Import Reduction.Generated.NEON.a80001038.
Require Import Reduction.Generated.NEON.a8000103c.
Require Import Reduction.Generated.NEON.a80001040.
Require Import Reduction.Generated.NEON.a80001044.
Require Import Reduction.Generated.NEON.a80001048.
Require Import Reduction.Generated.NEON.a8000104c.

Definition neon_program : gmap addr isla_trace := list_to_map [
  (BV 64 2147487744%Z, Reduction.Generated.NEON.a80001000.a80001000);
  (BV 64 2147487748%Z, Reduction.Generated.NEON.a80001004.a80001004);
  (BV 64 2147487752%Z, Reduction.Generated.NEON.a80001008.a80001008);
  (BV 64 2147487756%Z, Reduction.Generated.NEON.a8000100c.a8000100c);
  (BV 64 2147487760%Z, Reduction.Generated.NEON.a80001010.a80001010);
  (BV 64 2147487764%Z, Reduction.Generated.NEON.a80001014.a80001014);
  (BV 64 2147487768%Z, Reduction.Generated.NEON.a80001018.a80001018);
  (BV 64 2147487772%Z, Reduction.Generated.NEON.a8000101c.a8000101c);
  (BV 64 2147487776%Z, Reduction.Generated.NEON.a80001020.a80001020);
  (BV 64 2147487780%Z, Reduction.Generated.NEON.a80001024.a80001024);
  (BV 64 2147487784%Z, Reduction.Generated.NEON.a80001028.a80001028);
  (BV 64 2147487788%Z, Reduction.Generated.NEON.a8000102c.a8000102c);
  (BV 64 2147487792%Z, Reduction.Generated.NEON.a80001030.a80001030);
  (BV 64 2147487796%Z, Reduction.Generated.NEON.a80001034.a80001034);
  (BV 64 2147487800%Z, Reduction.Generated.NEON.a80001038.a80001038);
  (BV 64 2147487804%Z, Reduction.Generated.NEON.a8000103c.a8000103c);
  (BV 64 2147487808%Z, Reduction.Generated.NEON.a80001040.a80001040);
  (BV 64 2147487812%Z, Reduction.Generated.NEON.a80001044.a80001044);
  (BV 64 2147487816%Z, Reduction.Generated.NEON.a80001048.a80001048);
  (BV 64 2147487820%Z, Reduction.Generated.NEON.a8000104c.a8000104c)].
Lemma neon_program_size : size neon_program = 20%nat.
Proof. vm_compute. reflexivity. Qed.
Print Assumptions neon_program_size.
