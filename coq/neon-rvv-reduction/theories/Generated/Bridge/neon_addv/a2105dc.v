From isla Require Import opsem.

Definition a2105dc : isla_trace :=
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
  Smt (DefineConst 61%Z (Val (Val_Symbolic 29%Z) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 66%Z (Unop (Extract 127%N 64%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 84%Z (Unop (Extract 63%N 0%N) (Val (Val_Symbolic 61%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 103%Z (Manyop Concat [Val (Val_Bits (BV 96%N 0x0%Z)) Mk_annot; Manyop (Bvmanyarith Bvadd) [Manyop (Bvmanyarith Bvadd) [Unop (Extract 31%N 0%N) (Val (Val_Symbolic 84%Z) Mk_annot) Mk_annot; Unop (Extract 63%N 32%N) (Val (Val_Symbolic 84%Z) Mk_annot) Mk_annot] Mk_annot; Manyop (Bvmanyarith Bvadd) [Unop (Extract 31%N 0%N) (Val (Val_Symbolic 66%Z) Mk_annot) Mk_annot; Unop (Extract 63%N 32%N) (Val (Val_Symbolic 66%Z) Mk_annot) Mk_annot] Mk_annot] Mk_annot] Mk_annot)) Mk_annot :t:
  WriteReg "_V" [] (RegVal_Vector [RegVal_Base (Val_Symbolic 103%Z); RegVal_Base (Val_Symbolic 30%Z); RegVal_Base (Val_Symbolic 31%Z); RegVal_Base (Val_Symbolic 32%Z); RegVal_Base (Val_Symbolic 33%Z); RegVal_Base (Val_Symbolic 34%Z); RegVal_Base (Val_Symbolic 35%Z); RegVal_Base (Val_Symbolic 36%Z); RegVal_Base (Val_Symbolic 37%Z); RegVal_Base (Val_Symbolic 38%Z); RegVal_Base (Val_Symbolic 39%Z); RegVal_Base (Val_Symbolic 40%Z); RegVal_Base (Val_Symbolic 41%Z); RegVal_Base (Val_Symbolic 42%Z); RegVal_Base (Val_Symbolic 43%Z); RegVal_Base (Val_Symbolic 44%Z); RegVal_Base (Val_Symbolic 45%Z); RegVal_Base (Val_Symbolic 46%Z); RegVal_Base (Val_Symbolic 47%Z); RegVal_Base (Val_Symbolic 48%Z); RegVal_Base (Val_Symbolic 49%Z); RegVal_Base (Val_Symbolic 50%Z); RegVal_Base (Val_Symbolic 51%Z); RegVal_Base (Val_Symbolic 52%Z); RegVal_Base (Val_Symbolic 53%Z); RegVal_Base (Val_Symbolic 54%Z); RegVal_Base (Val_Symbolic 55%Z); RegVal_Base (Val_Symbolic 56%Z); RegVal_Base (Val_Symbolic 57%Z); RegVal_Base (Val_Symbolic 58%Z); RegVal_Base (Val_Symbolic 59%Z); RegVal_Base (Val_Symbolic 60%Z)]) Mk_annot :t:
  Smt (DeclareConst 104%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "_PC" [] (RegVal_Base (Val_Symbolic 104%Z)) Mk_annot :t:
  Smt (DefineConst 105%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 104%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x4%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  WriteReg "_PC" [] (RegVal_Base (Val_Symbolic 105%Z)) Mk_annot :t:
  tnil
.
