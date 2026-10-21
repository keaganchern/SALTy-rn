From isla Require Import opsem.

Definition a80001040 : isla_trace :=
  AssumeReg "HCR_EL2" [] (RegVal_Base (Val_Bits (BV 64%N 0x80000000%Z))) Mk_annot :t:
  AssumeReg "CFG_ID_AA64PFR0_EL1_EL3" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  AssumeReg "CFG_ID_AA64PFR0_EL1_EL2" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  AssumeReg "CFG_ID_AA64PFR0_EL1_EL1" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  AssumeReg "CFG_ID_AA64PFR0_EL1_EL0" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  AssumeReg "TCR_EL2" [] (RegVal_Base (Val_Bits (BV 64%N 0x0%Z))) Mk_annot :t:
  AssumeReg "EDSCR" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  AssumeReg "OSDLR_EL1" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  AssumeReg "OSLSR_EL1" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  Smt (DeclareConst 3%Z (Ty_BitVec 1%N)) Mk_annot :t:
  AssumeReg "PSTATE" [Field "EL"] (RegVal_Base (Val_Bits (BV 2%N 0x2%Z))) Mk_annot :t:
  AssumeReg "PSTATE" [Field "nRW"] (RegVal_Base (Val_Bits (BV 1%N 0x0%Z))) Mk_annot :t:
  AssumeReg "SCR_EL3" [] (RegVal_Base (Val_Bits (BV 32%N 0x501%Z))) Mk_annot :t:
  AssumeReg "SCTLR_EL2" [] (RegVal_Base (Val_Bits (BV 64%N 0x4000002%Z))) Mk_annot :t:
  Smt (DeclareConst 26%Z (Ty_BitVec 64%N)) Mk_annot :t:
  Assume (AExp_Binop ((Bvcomp Bvuge)) (AExp_Val (AVal_Var "R2" []) Mk_annot) (AExp_Val (AVal_Bits (BV 64%N 0x80000000%Z)) Mk_annot) Mk_annot) Mk_annot :t:
  Smt (Assert (Binop ((Bvcomp Bvuge)) (Val (Val_Symbolic 26%Z) Mk_annot) (Val (Val_Bits (BV 64%N 0x80000000%Z)) Mk_annot) Mk_annot)) Mk_annot :t:
  Assume (AExp_Binop ((Bvcomp Bvule)) (AExp_Val (AVal_Var "R2" []) Mk_annot) (AExp_Val (AVal_Bits (BV 64%N 0x83fffffc%Z)) Mk_annot) Mk_annot) Mk_annot :t:
  Smt (Assert (Binop ((Bvcomp Bvule)) (Val (Val_Symbolic 26%Z) Mk_annot) (Val (Val_Bits (BV 64%N 0x83fffffc%Z)) Mk_annot) Mk_annot)) Mk_annot :t:
  Assume (AExp_Binop (Eq) (AExp_Manyop (Bvmanyarith Bvand) [AExp_Val (AVal_Var "R2" []) Mk_annot; AExp_Val (AVal_Bits (BV 64%N 0x3%Z)) Mk_annot] Mk_annot) (AExp_Val (AVal_Bits (BV 64%N 0x0%Z)) Mk_annot) Mk_annot) Mk_annot :t:
  Smt (Assert (Binop (Eq) (Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 26%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x3%Z)) Mk_annot] Mk_annot) (Val (Val_Bits (BV 64%N 0x0%Z)) Mk_annot) Mk_annot)) Mk_annot :t:
  ReadReg "R2" [] (RegVal_Base (Val_Symbolic 26%Z)) Mk_annot :t:
  Smt (DefineConst 65%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 26%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x0%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  ReadReg "PSTATE" [Field "EL"] (RegVal_Struct [("EL", RegVal_Base (Val_Bits (BV 2%N 0x2%Z)))]) Mk_annot :t:
  Smt (DefineConst 69%Z (Binop (Eq) (Val (Val_Symbolic 65%Z) Mk_annot) (Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 65%Z) Mk_annot; Val (Val_Bits (BV 64%N 0xfffffffffffffffc%Z)) Mk_annot] Mk_annot) Mk_annot)) Mk_annot :t:
  ReadReg "SCTLR_EL2" [] (RegVal_Base (Val_Bits (BV 64%N 0x4000002%Z))) Mk_annot :t:
  Smt (Assert (Unop (Not) (Unop (Not) (Val (Val_Symbolic 69%Z) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Unop (Not) (Val (Val_Symbolic 69%Z) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Binop (Eq) (Val (Val_Symbolic 65%Z) Mk_annot) (Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 65%Z) Mk_annot; Val (Val_Bits (BV 64%N 0xfffffffffffffffc%Z)) Mk_annot] Mk_annot) Mk_annot)) Mk_annot :t:
  ReadReg "CFG_ID_AA64PFR0_EL1_EL2" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  ReadReg "CFG_ID_AA64PFR0_EL1_EL3" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  ReadReg "PSTATE" [Field "nRW"] (RegVal_Struct [("nRW", RegVal_Base (Val_Bits (BV 1%N 0x0%Z)))]) Mk_annot :t:
  ReadReg "CFG_ID_AA64PFR0_EL1_EL0" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  ReadReg "CFG_ID_AA64PFR0_EL1_EL1" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  ReadReg "SCR_EL3" [] (RegVal_Base (Val_Bits (BV 32%N 0x501%Z))) Mk_annot :t:
  ReadReg "HCR_EL2" [] (RegVal_Base (Val_Bits (BV 64%N 0x80000000%Z))) Mk_annot :t:
  ReadReg "TCR_EL2" [] (RegVal_Base (Val_Bits (BV 64%N 0x0%Z))) Mk_annot :t:
  Smt (Assert (Unop (Not) (Unop (Not) (Binop (Eq) (Unop (Extract 63%N 52%N) (Val (Val_Symbolic 65%Z) Mk_annot) Mk_annot) (Val (Val_Bits (BV 12%N 0x0%Z)) Mk_annot) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Unop (Not) (Val (Val_Symbolic 69%Z) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  ReadReg "PSTATE" [Field "D"] (RegVal_Struct [("D", RegVal_Base (Val_Symbolic 3%Z))]) Mk_annot :t:
  ReadReg "OSLSR_EL1" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  ReadReg "OSDLR_EL1" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  ReadReg "EDSCR" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  Smt (DefineConst 1244%Z (Val (Val_Symbolic 65%Z) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 1392%Z (Manyop Concat [Val (Val_Bits (BV 4%N 0x0%Z)) Mk_annot; Unop (Extract 51%N 0%N) (Val (Val_Symbolic 65%Z) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  Smt (DefineConst 1393%Z (Unop (ZeroExtend 8%N) (Val (Val_Symbolic 1392%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DeclareConst 1394%Z (Ty_BitVec 32%N)) Mk_annot :t:
  ReadMem (RegVal_Base (Val_Symbolic 1394%Z)) (RegVal_Poison) (RegVal_Base (Val_Symbolic 1393%Z)) 4%N None Mk_annot :t:
  Smt (DefineConst 1398%Z (Manyop Concat [Val (Val_Bits (BV 32%N 0x0%Z)) Mk_annot; Val (Val_Symbolic 1394%Z) Mk_annot] Mk_annot)) Mk_annot :t:
  WriteReg "R8" [] (RegVal_Base (Val_Symbolic 1398%Z)) Mk_annot :t:
  Smt (DeclareConst 1399%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "_PC" [] (RegVal_Base (Val_Symbolic 1399%Z)) Mk_annot :t:
  Smt (DefineConst 1400%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 1399%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x4%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  WriteReg "_PC" [] (RegVal_Base (Val_Symbolic 1400%Z)) Mk_annot :t:
  tnil
.
