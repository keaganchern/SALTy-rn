From isla Require Import opsem.

Definition a800001ee : isla_trace :=
  AssumeReg "misa" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000200104%Z)))]) Mk_annot :t:
  AssumeReg "rv_enable_zfinx" [] (RegVal_Base (Val_Bool false)) Mk_annot :t:
  AssumeReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  AssumeReg "vlenb" [] (RegVal_Base (Val_Bits (BV 64%N 0x20%Z))) Mk_annot :t:
  AssumeReg "vtype" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0xd0%Z)))]) Mk_annot :t:
  Smt (DeclareConst 0%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "PC" [] (RegVal_Base (Val_Symbolic 0%Z)) Mk_annot :t:
  Smt (DefineConst 1%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 0%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x4%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  ReadReg "misa" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000200104%Z)))]) Mk_annot :t:
  ReadReg "rv_enable_zfinx" [] (RegVal_Base (Val_Bool false)) Mk_annot :t:
  ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  ReadReg "vtype" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0xd0%Z)))]) Mk_annot :t:
  ReadReg "vlenb" [] (RegVal_Base (Val_Bits (BV 64%N 0x20%Z))) Mk_annot :t:
  Smt (DeclareConst 4%Z (Ty_BitVec 65536%N)) Mk_annot :t:
  ReadReg "vr8" [] (RegVal_Base (Val_Symbolic 4%Z)) Mk_annot :t:
  Smt (DefineConst 14%Z (Unop (SignExtend 32%N) (Unop (Extract 31%N 0%N) (Val (Val_Symbolic 4%Z) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  WriteReg "x15" [] (RegVal_Base (Val_Symbolic 14%Z)) Mk_annot :t:
  WriteReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
  WriteReg "PC" [] (RegVal_Base (Val_Symbolic 1%Z)) Mk_annot :t:
  tnil
.
