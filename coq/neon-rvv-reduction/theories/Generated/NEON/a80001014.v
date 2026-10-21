From isla Require Import opsem.

Definition a80001014 : isla_trace :=
  AssumeReg "HCR_EL2" [] (RegVal_Base (Val_Bits (BV 64%N 0x80000000%Z))) Mk_annot :t:
  AssumeReg "CFG_ID_AA64PFR0_EL1_EL3" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  AssumeReg "CFG_ID_AA64PFR0_EL1_EL2" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  AssumeReg "CFG_ID_AA64PFR0_EL1_EL1" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  AssumeReg "CFG_ID_AA64PFR0_EL1_EL0" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  AssumeReg "CPTR_EL3" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  AssumeReg "CPTR_EL2" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  AssumeReg "PSTATE" [Field "EL"] (RegVal_Base (Val_Bits (BV 2%N 0x2%Z))) Mk_annot :t:
  AssumeReg "PSTATE" [Field "nRW"] (RegVal_Base (Val_Bits (BV 1%N 0x0%Z))) Mk_annot :t:
  AssumeReg "SCR_EL3" [] (RegVal_Base (Val_Bits (BV 32%N 0x501%Z))) Mk_annot :t:
  ReadReg "PSTATE" [Field "EL"] (RegVal_Struct [("EL", RegVal_Base (Val_Bits (BV 2%N 0x2%Z)))]) Mk_annot :t:
  ReadReg "CFG_ID_AA64PFR0_EL1_EL2" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  ReadReg "CFG_ID_AA64PFR0_EL1_EL3" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  ReadReg "PSTATE" [Field "nRW"] (RegVal_Struct [("nRW", RegVal_Base (Val_Bits (BV 1%N 0x0%Z)))]) Mk_annot :t:
  ReadReg "CFG_ID_AA64PFR0_EL1_EL0" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  ReadReg "CFG_ID_AA64PFR0_EL1_EL1" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  ReadReg "SCR_EL3" [] (RegVal_Base (Val_Bits (BV 32%N 0x501%Z))) Mk_annot :t:
  ReadReg "HCR_EL2" [] (RegVal_Base (Val_Bits (BV 64%N 0x80000000%Z))) Mk_annot :t:
  ReadReg "CPTR_EL2" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  ReadReg "CPTR_EL3" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  Smt (DeclareConst 29%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 30%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 31%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 32%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 33%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 34%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 35%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 36%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 37%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 38%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 39%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 40%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 41%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 42%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 43%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 44%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 45%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 46%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 47%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 48%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 49%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 50%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 51%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 52%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 53%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 54%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 55%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 56%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 57%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 58%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 59%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 60%Z (Ty_BitVec 128%N)) Mk_annot :t:
  ReadReg "_V" [] (RegVal_Vector [RegVal_Base (Val_Symbolic 29%Z); RegVal_Base (Val_Symbolic 30%Z); RegVal_Base (Val_Symbolic 31%Z); RegVal_Base (Val_Symbolic 32%Z); RegVal_Base (Val_Symbolic 33%Z); RegVal_Base (Val_Symbolic 34%Z); RegVal_Base (Val_Symbolic 35%Z); RegVal_Base (Val_Symbolic 36%Z); RegVal_Base (Val_Symbolic 37%Z); RegVal_Base (Val_Symbolic 38%Z); RegVal_Base (Val_Symbolic 39%Z); RegVal_Base (Val_Symbolic 40%Z); RegVal_Base (Val_Symbolic 41%Z); RegVal_Base (Val_Symbolic 42%Z); RegVal_Base (Val_Symbolic 43%Z); RegVal_Base (Val_Symbolic 44%Z); RegVal_Base (Val_Symbolic 45%Z); RegVal_Base (Val_Symbolic 46%Z); RegVal_Base (Val_Symbolic 47%Z); RegVal_Base (Val_Symbolic 48%Z); RegVal_Base (Val_Symbolic 49%Z); RegVal_Base (Val_Symbolic 50%Z); RegVal_Base (Val_Symbolic 51%Z); RegVal_Base (Val_Symbolic 52%Z); RegVal_Base (Val_Symbolic 53%Z); RegVal_Base (Val_Symbolic 54%Z); RegVal_Base (Val_Symbolic 55%Z); RegVal_Base (Val_Symbolic 56%Z); RegVal_Base (Val_Symbolic 57%Z); RegVal_Base (Val_Symbolic 58%Z); RegVal_Base (Val_Symbolic 59%Z); RegVal_Base (Val_Symbolic 60%Z)]) Mk_annot :t:
  Smt (DefineConst 61%Z (Val (Val_Symbolic 31%Z) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 66%Z (Val (Val_Symbolic 30%Z) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 75%Z (Manyop (Bvmanyarith Bvor) [Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 66%Z) Mk_annot; Val (Val_Bits (BV 128%N 0xffffffffffffffffffffffffffff0000%Z)) Mk_annot] Mk_annot; Unop (ZeroExtend 112%N) (Manyop (Bvmanyarith Bvadd) [Unop (Extract 15%N 0%N) (Val (Val_Symbolic 66%Z) Mk_annot) Mk_annot; Manyop (Bvmanyarith Bvadd) [Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 7%N 0%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot; Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 15%N 8%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot] Mk_annot] Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  Smt (DefineConst 84%Z (Manyop (Bvmanyarith Bvor) [Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 75%Z) Mk_annot; Val (Val_Bits (BV 128%N 0xffffffffffffffffffffffff0000ffff%Z)) Mk_annot] Mk_annot; Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 112%N) (Manyop (Bvmanyarith Bvadd) [Unop (Extract 31%N 16%N) (Val (Val_Symbolic 75%Z) Mk_annot) Mk_annot; Manyop (Bvmanyarith Bvadd) [Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 23%N 16%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot; Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 31%N 24%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot] Mk_annot] Mk_annot) Mk_annot) (Val (Val_Bits (BV 128%N 0x10%Z)) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  Smt (DefineConst 93%Z (Manyop (Bvmanyarith Bvor) [Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 84%Z) Mk_annot; Val (Val_Bits (BV 128%N 0xffffffffffffffffffff0000ffffffff%Z)) Mk_annot] Mk_annot; Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 112%N) (Manyop (Bvmanyarith Bvadd) [Unop (Extract 47%N 32%N) (Val (Val_Symbolic 84%Z) Mk_annot) Mk_annot; Manyop (Bvmanyarith Bvadd) [Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 39%N 32%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot; Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 47%N 40%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot] Mk_annot] Mk_annot) Mk_annot) (Val (Val_Bits (BV 128%N 0x20%Z)) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  Smt (DefineConst 102%Z (Manyop (Bvmanyarith Bvor) [Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 93%Z) Mk_annot; Val (Val_Bits (BV 128%N 0xffffffffffffffff0000ffffffffffff%Z)) Mk_annot] Mk_annot; Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 112%N) (Manyop (Bvmanyarith Bvadd) [Unop (Extract 63%N 48%N) (Val (Val_Symbolic 93%Z) Mk_annot) Mk_annot; Manyop (Bvmanyarith Bvadd) [Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 55%N 48%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot; Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 63%N 56%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot] Mk_annot] Mk_annot) Mk_annot) (Val (Val_Bits (BV 128%N 0x30%Z)) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  Smt (DefineConst 111%Z (Manyop (Bvmanyarith Bvor) [Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 102%Z) Mk_annot; Val (Val_Bits (BV 128%N 0xffffffffffff0000ffffffffffffffff%Z)) Mk_annot] Mk_annot; Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 112%N) (Manyop (Bvmanyarith Bvadd) [Unop (Extract 79%N 64%N) (Val (Val_Symbolic 102%Z) Mk_annot) Mk_annot; Manyop (Bvmanyarith Bvadd) [Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 71%N 64%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot; Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 79%N 72%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot] Mk_annot] Mk_annot) Mk_annot) (Val (Val_Bits (BV 128%N 0x40%Z)) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  Smt (DefineConst 120%Z (Manyop (Bvmanyarith Bvor) [Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 111%Z) Mk_annot; Val (Val_Bits (BV 128%N 0xffffffff0000ffffffffffffffffffff%Z)) Mk_annot] Mk_annot; Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 112%N) (Manyop (Bvmanyarith Bvadd) [Unop (Extract 95%N 80%N) (Val (Val_Symbolic 111%Z) Mk_annot) Mk_annot; Manyop (Bvmanyarith Bvadd) [Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 87%N 80%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot; Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 95%N 88%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot] Mk_annot] Mk_annot) Mk_annot) (Val (Val_Bits (BV 128%N 0x50%Z)) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  Smt (DefineConst 129%Z (Manyop (Bvmanyarith Bvor) [Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 120%Z) Mk_annot; Val (Val_Bits (BV 128%N 0xffff0000ffffffffffffffffffffffff%Z)) Mk_annot] Mk_annot; Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 112%N) (Manyop (Bvmanyarith Bvadd) [Unop (Extract 111%N 96%N) (Val (Val_Symbolic 120%Z) Mk_annot) Mk_annot; Manyop (Bvmanyarith Bvadd) [Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 103%N 96%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot; Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 111%N 104%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot] Mk_annot] Mk_annot) Mk_annot) (Val (Val_Bits (BV 128%N 0x60%Z)) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  Smt (DefineConst 139%Z (Manyop (Bvmanyarith Bvor) [Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 129%Z) Mk_annot; Val (Val_Bits (BV 128%N 0xffffffffffffffffffffffffffff%Z)) Mk_annot] Mk_annot; Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 112%N) (Manyop (Bvmanyarith Bvadd) [Unop (Extract 127%N 112%N) (Val (Val_Symbolic 129%Z) Mk_annot) Mk_annot; Manyop (Bvmanyarith Bvadd) [Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 119%N 112%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot; Unop (Extract 15%N 0%N) (Unop (ZeroExtend 120%N) (Unop (Extract 127%N 120%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot) Mk_annot) Mk_annot] Mk_annot] Mk_annot) Mk_annot) (Val (Val_Bits (BV 128%N 0x70%Z)) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  WriteReg "_V" [] (RegVal_Vector [RegVal_Base (Val_Symbolic 29%Z); RegVal_Base (Val_Symbolic 139%Z); RegVal_Base (Val_Symbolic 31%Z); RegVal_Base (Val_Symbolic 32%Z); RegVal_Base (Val_Symbolic 33%Z); RegVal_Base (Val_Symbolic 34%Z); RegVal_Base (Val_Symbolic 35%Z); RegVal_Base (Val_Symbolic 36%Z); RegVal_Base (Val_Symbolic 37%Z); RegVal_Base (Val_Symbolic 38%Z); RegVal_Base (Val_Symbolic 39%Z); RegVal_Base (Val_Symbolic 40%Z); RegVal_Base (Val_Symbolic 41%Z); RegVal_Base (Val_Symbolic 42%Z); RegVal_Base (Val_Symbolic 43%Z); RegVal_Base (Val_Symbolic 44%Z); RegVal_Base (Val_Symbolic 45%Z); RegVal_Base (Val_Symbolic 46%Z); RegVal_Base (Val_Symbolic 47%Z); RegVal_Base (Val_Symbolic 48%Z); RegVal_Base (Val_Symbolic 49%Z); RegVal_Base (Val_Symbolic 50%Z); RegVal_Base (Val_Symbolic 51%Z); RegVal_Base (Val_Symbolic 52%Z); RegVal_Base (Val_Symbolic 53%Z); RegVal_Base (Val_Symbolic 54%Z); RegVal_Base (Val_Symbolic 55%Z); RegVal_Base (Val_Symbolic 56%Z); RegVal_Base (Val_Symbolic 57%Z); RegVal_Base (Val_Symbolic 58%Z); RegVal_Base (Val_Symbolic 59%Z); RegVal_Base (Val_Symbolic 60%Z)]) Mk_annot :t:
  Smt (DeclareConst 140%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "_PC" [] (RegVal_Base (Val_Symbolic 140%Z)) Mk_annot :t:
  Smt (DefineConst 141%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 140%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x4%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  WriteReg "_PC" [] (RegVal_Base (Val_Symbolic 141%Z)) Mk_annot :t:
  tnil
.
