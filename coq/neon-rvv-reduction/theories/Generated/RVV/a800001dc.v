From isla Require Import opsem.

Definition a800001dc : isla_trace :=
  AssumeReg "elen" [] (RegVal_Base (Val_Bits (BV 1%N 0x1%Z))) Mk_annot :t:
  AssumeReg "vlen" [] (RegVal_Base (Val_Bits (BV 4%N 0x3%Z))) Mk_annot :t:
  AssumeReg "misa" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000200104%Z)))]) Mk_annot :t:
  AssumeReg "rv_enable_zfinx" [] (RegVal_Base (Val_Bool false)) Mk_annot :t:
  AssumeReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  Smt (DeclareConst 0%Z (Ty_BitVec 64%N)) Mk_annot :t:
  Assume (AExp_Manyop Or [AExp_Binop (Eq) (AExp_Val (AVal_Var "vtype" [Field "bits"]) Mk_annot) (AExp_Val (AVal_Bits (BV 64%N 0x90%Z)) Mk_annot) Mk_annot; AExp_Binop (Eq) (AExp_Val (AVal_Var "vtype" [Field "bits"]) Mk_annot) (AExp_Val (AVal_Bits (BV 64%N 0xd0%Z)) Mk_annot) Mk_annot] Mk_annot) Mk_annot :t:
  Smt (Assert (Manyop Or [Binop (Eq) (Val (Val_Symbolic 0%Z) Mk_annot) (Val (Val_Bits (BV 64%N 0x90%Z)) Mk_annot) Mk_annot; Binop (Eq) (Val (Val_Symbolic 0%Z) Mk_annot) (Val (Val_Bits (BV 64%N 0xd0%Z)) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  Smt (DeclareConst 1%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "PC" [] (RegVal_Base (Val_Symbolic 1%Z)) Mk_annot :t:
  Smt (DefineConst 2%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 1%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x4%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  ReadReg "misa" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000200104%Z)))]) Mk_annot :t:
  ReadReg "rv_enable_zfinx" [] (RegVal_Base (Val_Bool false)) Mk_annot :t:
  ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  ReadReg "vlen" [] (RegVal_Base (Val_Bits (BV 4%N 0x3%Z))) Mk_annot :t:
  ReadReg "elen" [] (RegVal_Base (Val_Bits (BV 1%N 0x1%Z))) Mk_annot :t:
  ReadReg "vtype" [] (RegVal_Struct [("bits", RegVal_Base (Val_Symbolic 0%Z))]) Mk_annot :t:
  Smt (DefineConst 3%Z (Unop (Extract 2%N 0%N) (Val (Val_Symbolic 0%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Binop (Eq) (Val (Val_Symbolic 3%Z) Mk_annot) (Val (Val_Bits (BV 3%N 0x5%Z)) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Binop (Eq) (Val (Val_Symbolic 3%Z) Mk_annot) (Val (Val_Bits (BV 3%N 0x6%Z)) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Binop (Eq) (Val (Val_Symbolic 3%Z) Mk_annot) (Val (Val_Bits (BV 3%N 0x7%Z)) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Unop (Not) (Binop (Eq) (Val (Val_Symbolic 3%Z) Mk_annot) (Val (Val_Bits (BV 3%N 0x0%Z)) Mk_annot) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 12%Z (Unop (Extract 5%N 3%N) (Val (Val_Symbolic 0%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Binop (Eq) (Val (Val_Symbolic 12%Z) Mk_annot) (Val (Val_Bits (BV 3%N 0x0%Z)) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Binop (Eq) (Val (Val_Symbolic 12%Z) Mk_annot) (Val (Val_Bits (BV 3%N 0x1%Z)) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Unop (Not) (Binop (Eq) (Val (Val_Symbolic 12%Z) Mk_annot) (Val (Val_Bits (BV 3%N 0x2%Z)) Mk_annot) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  WriteReg "vtype" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0xd0%Z)))]) Mk_annot :t:
  ReadReg "vtype" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0xd0%Z)))]) Mk_annot :t:
  WriteReg "vl" [] (RegVal_Base (Val_Bits (BV 64%N 0x8%Z))) Mk_annot :t:
  ReadReg "vl" [] (RegVal_Base (Val_Bits (BV 64%N 0x8%Z))) Mk_annot :t:
  WriteReg "x15" [] (RegVal_Base (Val_Bits (BV 64%N 0x8%Z))) Mk_annot :t:
  ReadReg "vtype" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0xd0%Z)))]) Mk_annot :t:
  WriteReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
  ReadReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
  WriteReg "PC" [] (RegVal_Base (Val_Symbolic 2%Z)) Mk_annot :t:
  tnil
.
