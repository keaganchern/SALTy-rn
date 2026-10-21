From isla Require Import opsem.

Definition a800001f2 : isla_trace :=
  Smt (DeclareConst 0%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "PC" [] (RegVal_Base (Val_Symbolic 0%Z)) Mk_annot :t:
  Smt (DefineConst 1%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 0%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x2%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  Smt (DeclareConst 2%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "x15" [] (RegVal_Base (Val_Symbolic 2%Z)) Mk_annot :t:
  Smt (DeclareConst 4%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "x13" [] (RegVal_Base (Val_Symbolic 4%Z)) Mk_annot :t:
  Smt (DefineConst 7%Z (Unop (SignExtend 32%N) (Manyop (Bvmanyarith Bvadd) [Unop (Extract 31%N 0%N) (Val (Val_Symbolic 2%Z) Mk_annot) Mk_annot; Unop (Extract 31%N 0%N) (Val (Val_Symbolic 4%Z) Mk_annot) Mk_annot] Mk_annot) Mk_annot)) Mk_annot :t:
  WriteReg "x15" [] (RegVal_Base (Val_Symbolic 7%Z)) Mk_annot :t:
  WriteReg "PC" [] (RegVal_Base (Val_Symbolic 1%Z)) Mk_annot :t:
  tnil
.
