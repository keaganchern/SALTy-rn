From isla Require Import opsem.
(* Share closed bitvector constants; the stored width and value are unchanged. *)
Definition wide8 : bv 65536 := BV 65536 8.
Definition wide32 : bv 65536 := BV 65536 32.
Lemma wide8_unsigned : bv_unsigned wide8 = 8%Z.
Proof. reflexivity. Qed.
Lemma wide32_unsigned : bv_unsigned wide32 = 32%Z.
Proof. reflexivity. Qed.
Print Assumptions wide8_unsigned.
Print Assumptions wide32_unsigned.
