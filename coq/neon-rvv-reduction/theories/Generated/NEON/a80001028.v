From isla Require Import opsem.

Definition a80001028 : isla_trace :=
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
  Smt (DeclareConst 52%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 53%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 54%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 55%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 56%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 57%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 58%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 59%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 60%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 61%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 62%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 63%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 64%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 65%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 66%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 67%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 68%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 69%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 70%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 71%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 72%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 73%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 74%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 75%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 76%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 77%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 78%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 79%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 80%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 81%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 82%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 83%Z (Ty_BitVec 128%N)) Mk_annot :t:
  ReadReg "_V" [] (RegVal_Vector [RegVal_Base (Val_Symbolic 52%Z); RegVal_Base (Val_Symbolic 53%Z); RegVal_Base (Val_Symbolic 54%Z); RegVal_Base (Val_Symbolic 55%Z); RegVal_Base (Val_Symbolic 56%Z); RegVal_Base (Val_Symbolic 57%Z); RegVal_Base (Val_Symbolic 58%Z); RegVal_Base (Val_Symbolic 59%Z); RegVal_Base (Val_Symbolic 60%Z); RegVal_Base (Val_Symbolic 61%Z); RegVal_Base (Val_Symbolic 62%Z); RegVal_Base (Val_Symbolic 63%Z); RegVal_Base (Val_Symbolic 64%Z); RegVal_Base (Val_Symbolic 65%Z); RegVal_Base (Val_Symbolic 66%Z); RegVal_Base (Val_Symbolic 67%Z); RegVal_Base (Val_Symbolic 68%Z); RegVal_Base (Val_Symbolic 69%Z); RegVal_Base (Val_Symbolic 70%Z); RegVal_Base (Val_Symbolic 71%Z); RegVal_Base (Val_Symbolic 72%Z); RegVal_Base (Val_Symbolic 73%Z); RegVal_Base (Val_Symbolic 74%Z); RegVal_Base (Val_Symbolic 75%Z); RegVal_Base (Val_Symbolic 76%Z); RegVal_Base (Val_Symbolic 77%Z); RegVal_Base (Val_Symbolic 78%Z); RegVal_Base (Val_Symbolic 79%Z); RegVal_Base (Val_Symbolic 80%Z); RegVal_Base (Val_Symbolic 81%Z); RegVal_Base (Val_Symbolic 82%Z); RegVal_Base (Val_Symbolic 83%Z)]) Mk_annot :t:
  Smt (DefineConst 86%Z (Manyop Concat [Val (Val_Bits (BV 32%N 0x0%Z)) Mk_annot; Unop (Extract 31%N 0%N) (Val (Val_Symbolic 52%Z) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  WriteReg "R9" [] (RegVal_Base (Val_Symbolic 86%Z)) Mk_annot :t:
  Smt (DeclareConst 87%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "_PC" [] (RegVal_Base (Val_Symbolic 87%Z)) Mk_annot :t:
  Smt (DefineConst 88%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 87%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x4%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  WriteReg "_PC" [] (RegVal_Base (Val_Symbolic 88%Z)) Mk_annot :t:
  tnil
.
