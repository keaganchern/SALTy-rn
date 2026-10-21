From isla Require Import opsem.

Definition a80001044 : isla_trace :=
  Smt (DeclareConst 27%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "R8" [] (RegVal_Base (Val_Symbolic 27%Z)) Mk_annot :t:
  Smt (DeclareConst 29%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "R9" [] (RegVal_Base (Val_Symbolic 29%Z)) Mk_annot :t:
  Smt (DefineConst 55%Z (Manyop Concat [Val (Val_Bits (BV 32%N 0x0%Z)) Mk_annot; Manyop (Bvmanyarith Bvadd) [Unop (Extract 31%N 0%N) (Unop (ZeroExtend 96%N) (Unop (Extract 31%N 0%N) (Val (Val_Symbolic 27%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot; Unop (Extract 31%N 0%N) (Unop (ZeroExtend 96%N) (Unop (Extract 31%N 0%N) (Val (Val_Symbolic 29%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot] Mk_annot] Mk_annot)) Mk_annot :t:
  WriteReg "R8" [] (RegVal_Base (Val_Symbolic 55%Z)) Mk_annot :t:
  Smt (DeclareConst 56%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "_PC" [] (RegVal_Base (Val_Symbolic 56%Z)) Mk_annot :t:
  Smt (DefineConst 57%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 56%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x4%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  WriteReg "_PC" [] (RegVal_Base (Val_Symbolic 57%Z)) Mk_annot :t:
  tnil
.
