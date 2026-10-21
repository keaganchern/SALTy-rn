Require Import isla.aarch64.aarch64.
Require Import Reduction.NEON.NeonTail.
From Reduction.Generated.NEON Require Import a8000102c a80001030 a80001034 a80001038 a8000103c.

Lemma neon_tail_with_zero `{!islaG Σ} `{!threadG} (xs : list (bv 8))
    (p : bv 64) (acc : bv 32) (d : bv 1) :
  (0x80000000 <= bv_unsigned p /\
    bv_unsigned p + Z.of_nat (length xs) <= 0x84000000)%Z ->
  instr 0x8000102c (Some a8000102c) -∗
  instr 0x80001030 (Some a80001030) -∗ instr 0x80001034 (Some a80001034) -∗
  instr 0x80001038 (Some a80001038) -∗ instr 0x8000103c (Some a8000103c) -∗
  instr_body 0x8000102c (
    byte_state p (Z.of_nat (length xs)) acc d ∗ byte_memory (bv_unsigned p) xs ∗
    instr_pre 0x80001040 (
      byte_state (bv_add p (Z_to_bv 64 (Z.of_nat (length xs)))) 0
        (bv_add acc (byte_sum xs)) d ∗ byte_memory (bv_unsigned p) xs)).
Proof.
  intros Hrange. destruct xs as [|x xs].
  - cbn [length byte_sum byte_memory]. iStartProof. liARun.
    Unshelve. all: prepare_sidecond. all: try bv_solve.
    Unshelve. all: try done.
    all: try (exfalso; bv_simplify H0; bv_solve).
  - iIntros "#H2c #H30 #H34 #H38 #H3c".
    iPoseProof (neon_byte_loop (x::xs) p acc d ltac:(discriminate) Hrange
      with "H30 H34 H38 H3c") as "Htail".
    iStartProof. liARun.
    Unshelve. all: prepare_sidecond. all: cbn [length] in Hrange.
    all: try bv_simplify H0; try bv_solve.
    Unshelve. all: try done.
    all: try (exfalso; bv_simplify H0; bv_solve).
Qed.
Print Assumptions neon_tail_with_zero.
