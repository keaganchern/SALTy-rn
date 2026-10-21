From isla Require Import opsem.

Definition a800001ea : isla_trace :=
  AssumeReg "vlen" [] (RegVal_Base (Val_Bits (BV 4%N 0x3%Z))) Mk_annot :t:
  AssumeReg "misa" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000200104%Z)))]) Mk_annot :t:
  AssumeReg "rv_enable_zfinx" [] (RegVal_Base (Val_Bool false)) Mk_annot :t:
  AssumeReg "rv_enable_vext" [] (RegVal_Base (Val_Bool true)) Mk_annot :t:
  AssumeReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  AssumeReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
  AssumeReg "vl" [] (RegVal_Base (Val_Bits (BV 64%N 0x8%Z))) Mk_annot :t:
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
  ReadReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
  ReadReg "vl" [] (RegVal_Base (Val_Bits (BV 64%N 0x8%Z))) Mk_annot :t:
  Smt (DeclareConst 3%Z (Ty_BitVec 65536%N)) Mk_annot :t:
  ReadReg "vr0" [] (RegVal_Base (Val_Symbolic 3%Z)) Mk_annot :t:
  Smt (DeclareConst 7%Z (Ty_BitVec 65536%N)) Mk_annot :t:
  ReadReg "vr8" [] (RegVal_Base (Val_Symbolic 7%Z)) Mk_annot :t:
  ReadReg "vlen" [] (RegVal_Base (Val_Bits (BV 4%N 0x3%Z))) Mk_annot :t:
  Smt (DeclareConst 30%Z (Ty_BitVec 65536%N)) Mk_annot :t:
  ReadReg "vr1" [] (RegVal_Base (Val_Symbolic 30%Z)) Mk_annot :t:
  Smt (DefineConst 82%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Unop (Extract 255%N 224%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot) Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (Extract 223%N 192%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (Extract 191%N 160%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (Extract 159%N 128%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (Extract 127%N 96%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (Extract 95%N 64%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (Extract 63%N 32%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Manyop (Bvmanyarith Bvadd) [Manyop (Bvmanyarith Bvadd) [Manyop (Bvmanyarith Bvadd) [Manyop (Bvmanyarith Bvadd) [Manyop (Bvmanyarith Bvadd) [Manyop (Bvmanyarith Bvadd) [Manyop (Bvmanyarith Bvadd) [Unop (Extract 31%N 0%N) (Val (Val_Symbolic 30%Z) Mk_annot) Mk_annot; Unop (Extract 31%N 0%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot] Mk_annot; Unop (Extract 63%N 32%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot] Mk_annot; Unop (Extract 95%N 64%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot] Mk_annot; Unop (Extract 127%N 96%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot] Mk_annot; Unop (Extract 159%N 128%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot] Mk_annot; Unop (Extract 191%N 160%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot] Mk_annot; Unop (Extract 223%N 192%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot] Mk_annot; Unop (Extract 255%N 224%N) (Val (Val_Symbolic 7%Z) Mk_annot) Mk_annot] Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  WriteReg "vr8" [] (RegVal_Base (Val_Symbolic 82%Z)) Mk_annot :t:
  ReadReg "rv_enable_vext" [] (RegVal_Base (Val_Bool true)) Mk_annot :t:
  ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  WriteReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
  WriteReg "PC" [] (RegVal_Base (Val_Symbolic 1%Z)) Mk_annot :t:
  tnil
.
