From stdpp.bitvector Require Import bitvector.
Require Import Reduction.RVV.RvvLoadSharedDefs Reduction.RVV.RvvLiterals Reduction.RVV.RvvBytePackingShared.
Local Opaque bv_or bv_shiftl bv_zero_extend.
Lemma pack32bytes_lane_all (f : N -> bv 8) (i : N) : (i < 32)%N ->
  bv_extract (8*i) 8 (pack32bytes f) = f i.
Proof.
  intros Hi.
  assert (i=0 \/ i=1 \/ i=2 \/ i=3 \/ i=4 \/ i=5 \/ i=6 \/ i=7 \/ i=8 \/ i=9 \/ i=10 \/ i=11 \/ i=12 \/ i=13 \/ i=14 \/ i=15 \/ i=16 \/ i=17 \/ i=18 \/ i=19 \/ i=20 \/ i=21 \/ i=22 \/ i=23 \/ i=24 \/ i=25 \/ i=26 \/ i=27 \/ i=28 \/ i=29 \/ i=30 \/ i=31)%N as Hcases by lia.
  destruct Hcases as [Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|[Hcase|Hcase]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]; subst i.
  all: unfold pack32bytes; fold push8.
  all: repeat first [rewrite (get_push8_next 30) by lia |
    rewrite (get_push8_next 29) by lia |
    rewrite (get_push8_next 28) by lia |
    rewrite (get_push8_next 27) by lia |
    rewrite (get_push8_next 26) by lia |
    rewrite (get_push8_next 25) by lia |
    rewrite (get_push8_next 24) by lia |
    rewrite (get_push8_next 23) by lia |
    rewrite (get_push8_next 22) by lia |
    rewrite (get_push8_next 21) by lia |
    rewrite (get_push8_next 20) by lia |
    rewrite (get_push8_next 19) by lia |
    rewrite (get_push8_next 18) by lia |
    rewrite (get_push8_next 17) by lia |
    rewrite (get_push8_next 16) by lia |
    rewrite (get_push8_next 15) by lia |
    rewrite (get_push8_next 14) by lia |
    rewrite (get_push8_next 13) by lia |
    rewrite (get_push8_next 12) by lia |
    rewrite (get_push8_next 11) by lia |
    rewrite (get_push8_next 10) by lia |
    rewrite (get_push8_next 9) by lia |
    rewrite (get_push8_next 8) by lia |
    rewrite (get_push8_next 7) by lia |
    rewrite (get_push8_next 6) by lia |
    rewrite (get_push8_next 5) by lia |
    rewrite (get_push8_next 4) by lia |
    rewrite (get_push8_next 3) by lia |
    rewrite (get_push8_next 2) by lia |
    rewrite (get_push8_next 1) by lia |
    rewrite (get_push8_next 0) by lia].
  all: try apply get_push8_zero.
  Local Transparent bv_zero_extend.
  apply bv_eq. bv_simplify. apply bv_wrap_small. apply bv_unsigned_in_range.
Qed.
Print Assumptions pack32bytes_lane_all.
