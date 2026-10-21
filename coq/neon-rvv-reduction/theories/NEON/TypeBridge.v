(* Candidate observation interfaces based on the actual imported register
   layouts. These definitions do NOT assert that a whole kernel refines them. *)
From stdpp.bitvector Require Import bitvector.

Definition neon_u32_lanes (v : bv 128) : list (bv 32) :=
  [bv_extract 0 32 v; bv_extract 32 32 v;
   bv_extract 64 32 v; bv_extract 96 32 v].
Definition neon_u16_lanes (v : bv 128) : list (bv 16) :=
  [bv_extract 0 16 v; bv_extract 16 16 v;
   bv_extract 32 16 v; bv_extract 48 16 v;
   bv_extract 64 16 v; bv_extract 80 16 v;
   bv_extract 96 16 v; bv_extract 112 16 v].
Definition rvv_u32_lanes256 (v : bv 65536) : list (bv 32) :=
  [bv_extract 0 32 v; bv_extract 32 32 v;
   bv_extract 64 32 v; bv_extract 96 32 v;
   bv_extract 128 32 v; bv_extract 160 32 v;
   bv_extract 192 32 v; bv_extract 224 32 v].
Definition sum32 (xs : list (bv 32)) : bv 32 := fold_left bv_add xs (BV 32 0).

(* q0 is the NEON word accumulator, q1 its pending halfword accumulator. *)
Definition neon_accumulator_view (q0 q1 : bv 128) : bv 32 :=
  bv_add (sum32 (neon_u32_lanes q0))
         (sum32 (map (bv_zero_extend 32) (neon_u16_lanes q1))).
(* This view is configuration-specific: VLEN=256, e32,m8, registers 8..15. *)
Definition rvv_accumulator_view256 (r : nat -> bv 65536) : bv 32 :=
  sum32 (flat_map (fun i => rvv_u32_lanes256 (r i)) (seq 8 8)).
Definition accumulator_relation q0 q1 r : Prop :=
  neon_accumulator_view q0 q1 = rvv_accumulator_view256 r.

(* The typed arithmetic obligation underlying one unsigned byte pair.
   An ISA proof still has to connect its trace to these lane expressions. *)
Lemma widen_pair_without_overflow (a : bv 16) (x y : bv 8) :
  (bv_unsigned a + bv_unsigned x + bv_unsigned y < 65536)%Z ->
  bv_zero_extend 32 (bv_add a (bv_add (bv_zero_extend 16 x) (bv_zero_extend 16 y))) =
  bv_add (bv_zero_extend 32 a)
         (bv_add (bv_zero_extend 32 x) (bv_zero_extend 32 y)).
Proof.
  intros H. bv_simplify.
  rewrite (bv_wrap_small 16 (bv_unsigned a + (bv_unsigned x + bv_unsigned y))).
  - rewrite bv_wrap_bv_wrap by lia. reflexivity.
  - change (0 <= bv_unsigned a + (bv_unsigned x + bv_unsigned y) < 65536)%Z.
    pose proof (bv_unsigned_in_range 16 a).
    pose proof (bv_unsigned_in_range 8 x).
    pose proof (bv_unsigned_in_range 8 y). lia.
Qed.

Example typed_overflow_counterexample :
  bv_zero_extend 32 (bv_add (BV 16 65535) (BV 16 1)) <> bv_add (BV 32 65535) (BV 32 1).
Proof. vm_compute. discriminate. Qed.

Print Assumptions widen_pair_without_overflow.
Print Assumptions typed_overflow_counterexample.
