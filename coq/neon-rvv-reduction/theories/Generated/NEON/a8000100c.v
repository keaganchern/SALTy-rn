From isla Require Import opsem.

Definition a8000100c : isla_trace :=
  AssumeReg "HCR_EL2" [] (RegVal_Base (Val_Bits (BV 64%N 0x80000000%Z))) Mk_annot :t:
  AssumeReg "CFG_ID_AA64PFR0_EL1_EL3" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  AssumeReg "CFG_ID_AA64PFR0_EL1_EL2" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  AssumeReg "CFG_ID_AA64PFR0_EL1_EL1" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  AssumeReg "CFG_ID_AA64PFR0_EL1_EL0" [] (RegVal_Base (Val_Bits (BV 4%N 0x1%Z))) Mk_annot :t:
  AssumeReg "TCR_EL2" [] (RegVal_Base (Val_Bits (BV 64%N 0x0%Z))) Mk_annot :t:
  AssumeReg "CPTR_EL3" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  AssumeReg "CPTR_EL2" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  AssumeReg "EDSCR" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  AssumeReg "OSDLR_EL1" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  AssumeReg "OSLSR_EL1" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  Smt (DeclareConst 3%Z (Ty_BitVec 1%N)) Mk_annot :t:
  AssumeReg "PSTATE" [Field "EL"] (RegVal_Base (Val_Bits (BV 2%N 0x2%Z))) Mk_annot :t:
  AssumeReg "PSTATE" [Field "nRW"] (RegVal_Base (Val_Bits (BV 1%N 0x0%Z))) Mk_annot :t:
  AssumeReg "SCR_EL3" [] (RegVal_Base (Val_Bits (BV 32%N 0x501%Z))) Mk_annot :t:
  AssumeReg "SCTLR_EL2" [] (RegVal_Base (Val_Bits (BV 64%N 0x4000002%Z))) Mk_annot :t:
  Smt (DeclareConst 26%Z (Ty_BitVec 64%N)) Mk_annot :t:
  Assume (AExp_Binop ((Bvcomp Bvuge)) (AExp_Val (AVal_Var "R1" []) Mk_annot) (AExp_Val (AVal_Bits (BV 64%N 0x80000000%Z)) Mk_annot) Mk_annot) Mk_annot :t:
  Smt (Assert (Binop ((Bvcomp Bvuge)) (Val (Val_Symbolic 26%Z) Mk_annot) (Val (Val_Bits (BV 64%N 0x80000000%Z)) Mk_annot) Mk_annot)) Mk_annot :t:
  Assume (AExp_Binop ((Bvcomp Bvule)) (AExp_Val (AVal_Var "R1" []) Mk_annot) (AExp_Val (AVal_Bits (BV 64%N 0x83fffff0%Z)) Mk_annot) Mk_annot) Mk_annot :t:
  Smt (Assert (Binop ((Bvcomp Bvule)) (Val (Val_Symbolic 26%Z) Mk_annot) (Val (Val_Bits (BV 64%N 0x83fffff0%Z)) Mk_annot) Mk_annot)) Mk_annot :t:
  Assume (AExp_Binop (Eq) (AExp_Manyop (Bvmanyarith Bvand) [AExp_Val (AVal_Var "R1" []) Mk_annot; AExp_Val (AVal_Bits (BV 64%N 0xf%Z)) Mk_annot] Mk_annot) (AExp_Val (AVal_Bits (BV 64%N 0x0%Z)) Mk_annot) Mk_annot) Mk_annot :t:
  Smt (Assert (Binop (Eq) (Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 26%Z) Mk_annot; Val (Val_Bits (BV 64%N 0xf%Z)) Mk_annot] Mk_annot) (Val (Val_Bits (BV 64%N 0x0%Z)) Mk_annot) Mk_annot)) Mk_annot :t:
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
  ReadReg "R1" [] (RegVal_Base (Val_Symbolic 26%Z)) Mk_annot :t:
  Smt (DefineConst 32%Z (Val (Val_Symbolic 26%Z) Mk_annot)) Mk_annot :t:
  Smt (DeclareConst 33%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DefineConst 36%Z (Binop (Eq) (Val (Val_Symbolic 32%Z) Mk_annot) (Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 32%Z) Mk_annot; Val (Val_Bits (BV 64%N 0xfffffffffffffff0%Z)) Mk_annot] Mk_annot) Mk_annot)) Mk_annot :t:
  ReadReg "SCTLR_EL2" [] (RegVal_Base (Val_Bits (BV 64%N 0x4000002%Z))) Mk_annot :t:
  Smt (Assert (Unop (Not) (Unop (Not) (Val (Val_Symbolic 36%Z) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Unop (Not) (Binop (Eq) (Val (Val_Symbolic 32%Z) Mk_annot) (Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 32%Z) Mk_annot; Val (Val_Bits (BV 64%N 0xfffffffffffffff8%Z)) Mk_annot] Mk_annot) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Binop (Eq) (Val (Val_Symbolic 32%Z) Mk_annot) (Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 32%Z) Mk_annot; Val (Val_Bits (BV 64%N 0xfffffffffffffff8%Z)) Mk_annot] Mk_annot) Mk_annot)) Mk_annot :t:
  ReadReg "TCR_EL2" [] (RegVal_Base (Val_Bits (BV 64%N 0x0%Z))) Mk_annot :t:
  Smt (Assert (Unop (Not) (Unop (Not) (Binop (Eq) (Unop (Extract 63%N 52%N) (Val (Val_Symbolic 32%Z) Mk_annot) Mk_annot) (Val (Val_Bits (BV 12%N 0x0%Z)) Mk_annot) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Unop (Not) (Val (Val_Symbolic 36%Z) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  ReadReg "PSTATE" [Field "D"] (RegVal_Struct [("D", RegVal_Base (Val_Symbolic 3%Z))]) Mk_annot :t:
  ReadReg "OSLSR_EL1" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  ReadReg "OSDLR_EL1" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  ReadReg "EDSCR" [] (RegVal_Base (Val_Bits (BV 32%N 0x0%Z))) Mk_annot :t:
  Smt (DefineConst 1213%Z (Val (Val_Symbolic 32%Z) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 1361%Z (Manyop Concat [Val (Val_Bits (BV 4%N 0x0%Z)) Mk_annot; Unop (Extract 51%N 0%N) (Val (Val_Symbolic 32%Z) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  Smt (DefineConst 1362%Z (Unop (ZeroExtend 8%N) (Val (Val_Symbolic 1361%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DeclareConst 1363%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadMem (RegVal_Base (Val_Symbolic 1363%Z)) (RegVal_Poison) (RegVal_Base (Val_Symbolic 1362%Z)) 8%N None Mk_annot :t:
  Smt (DefineConst 1365%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 32%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x8%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  Smt (Assert (Binop (Eq) (Val (Val_Symbolic 1365%Z) Mk_annot) (Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 1365%Z) Mk_annot; Val (Val_Bits (BV 64%N 0xfffffffffffffff8%Z)) Mk_annot] Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Unop (Not) (Binop (Eq) (Unop (Extract 63%N 52%N) (Val (Val_Symbolic 1365%Z) Mk_annot) Mk_annot) (Val (Val_Bits (BV 12%N 0x0%Z)) Mk_annot) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Unop (Not) (Val (Val_Symbolic 36%Z) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 2506%Z (Val (Val_Symbolic 1365%Z) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 2654%Z (Manyop Concat [Val (Val_Bits (BV 4%N 0x0%Z)) Mk_annot; Unop (Extract 51%N 0%N) (Val (Val_Symbolic 1365%Z) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  Smt (DefineConst 2655%Z (Unop (ZeroExtend 8%N) (Val (Val_Symbolic 2654%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DeclareConst 2656%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadMem (RegVal_Base (Val_Symbolic 2656%Z)) (RegVal_Poison) (RegVal_Base (Val_Symbolic 2655%Z)) 8%N None Mk_annot :t:
  Smt (DefineConst 2660%Z (Manyop (Bvmanyarith Bvor) [Manyop (Bvmanyarith Bvand) [Manyop (Bvmanyarith Bvor) [Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 33%Z) Mk_annot; Val (Val_Bits (BV 128%N 0xffffffffffffffff0000000000000000%Z)) Mk_annot] Mk_annot; Unop (ZeroExtend 64%N) (Val (Val_Symbolic 1363%Z) Mk_annot) Mk_annot] Mk_annot; Val (Val_Bits (BV 128%N 0xffffffffffffffff%Z)) Mk_annot] Mk_annot; Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 64%N) (Val (Val_Symbolic 2656%Z) Mk_annot) Mk_annot) (Val (Val_Bits (BV 128%N 0x40%Z)) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
  Smt (DeclareConst 2661%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2662%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2663%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2664%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2665%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2666%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2667%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2668%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2669%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2670%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2671%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2672%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2673%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2674%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2675%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2676%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2677%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2678%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2679%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2680%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2681%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2682%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2683%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2684%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2685%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2686%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2687%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2688%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2689%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2690%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2691%Z (Ty_BitVec 128%N)) Mk_annot :t:
  Smt (DeclareConst 2692%Z (Ty_BitVec 128%N)) Mk_annot :t:
  ReadReg "_V" [] (RegVal_Vector [RegVal_Base (Val_Symbolic 2661%Z); RegVal_Base (Val_Symbolic 2662%Z); RegVal_Base (Val_Symbolic 2663%Z); RegVal_Base (Val_Symbolic 2664%Z); RegVal_Base (Val_Symbolic 2665%Z); RegVal_Base (Val_Symbolic 2666%Z); RegVal_Base (Val_Symbolic 2667%Z); RegVal_Base (Val_Symbolic 2668%Z); RegVal_Base (Val_Symbolic 2669%Z); RegVal_Base (Val_Symbolic 2670%Z); RegVal_Base (Val_Symbolic 2671%Z); RegVal_Base (Val_Symbolic 2672%Z); RegVal_Base (Val_Symbolic 2673%Z); RegVal_Base (Val_Symbolic 2674%Z); RegVal_Base (Val_Symbolic 2675%Z); RegVal_Base (Val_Symbolic 2676%Z); RegVal_Base (Val_Symbolic 2677%Z); RegVal_Base (Val_Symbolic 2678%Z); RegVal_Base (Val_Symbolic 2679%Z); RegVal_Base (Val_Symbolic 2680%Z); RegVal_Base (Val_Symbolic 2681%Z); RegVal_Base (Val_Symbolic 2682%Z); RegVal_Base (Val_Symbolic 2683%Z); RegVal_Base (Val_Symbolic 2684%Z); RegVal_Base (Val_Symbolic 2685%Z); RegVal_Base (Val_Symbolic 2686%Z); RegVal_Base (Val_Symbolic 2687%Z); RegVal_Base (Val_Symbolic 2688%Z); RegVal_Base (Val_Symbolic 2689%Z); RegVal_Base (Val_Symbolic 2690%Z); RegVal_Base (Val_Symbolic 2691%Z); RegVal_Base (Val_Symbolic 2692%Z)]) Mk_annot :t:
  WriteReg "_V" [] (RegVal_Vector [RegVal_Base (Val_Symbolic 2661%Z); RegVal_Base (Val_Symbolic 2662%Z); RegVal_Base (Val_Symbolic 2660%Z); RegVal_Base (Val_Symbolic 2664%Z); RegVal_Base (Val_Symbolic 2665%Z); RegVal_Base (Val_Symbolic 2666%Z); RegVal_Base (Val_Symbolic 2667%Z); RegVal_Base (Val_Symbolic 2668%Z); RegVal_Base (Val_Symbolic 2669%Z); RegVal_Base (Val_Symbolic 2670%Z); RegVal_Base (Val_Symbolic 2671%Z); RegVal_Base (Val_Symbolic 2672%Z); RegVal_Base (Val_Symbolic 2673%Z); RegVal_Base (Val_Symbolic 2674%Z); RegVal_Base (Val_Symbolic 2675%Z); RegVal_Base (Val_Symbolic 2676%Z); RegVal_Base (Val_Symbolic 2677%Z); RegVal_Base (Val_Symbolic 2678%Z); RegVal_Base (Val_Symbolic 2679%Z); RegVal_Base (Val_Symbolic 2680%Z); RegVal_Base (Val_Symbolic 2681%Z); RegVal_Base (Val_Symbolic 2682%Z); RegVal_Base (Val_Symbolic 2683%Z); RegVal_Base (Val_Symbolic 2684%Z); RegVal_Base (Val_Symbolic 2685%Z); RegVal_Base (Val_Symbolic 2686%Z); RegVal_Base (Val_Symbolic 2687%Z); RegVal_Base (Val_Symbolic 2688%Z); RegVal_Base (Val_Symbolic 2689%Z); RegVal_Base (Val_Symbolic 2690%Z); RegVal_Base (Val_Symbolic 2691%Z); RegVal_Base (Val_Symbolic 2692%Z)]) Mk_annot :t:
  Smt (DefineConst 2694%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 32%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x10%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  WriteReg "R1" [] (RegVal_Base (Val_Symbolic 2694%Z)) Mk_annot :t:
  Smt (DeclareConst 2695%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "_PC" [] (RegVal_Base (Val_Symbolic 2695%Z)) Mk_annot :t:
  Smt (DefineConst 2696%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 2695%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x4%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  WriteReg "_PC" [] (RegVal_Base (Val_Symbolic 2696%Z)) Mk_annot :t:
  tnil
.
