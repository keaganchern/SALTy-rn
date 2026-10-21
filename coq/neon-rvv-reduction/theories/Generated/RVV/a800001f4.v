From isla Require Import opsem.

Definition a800001f4 : isla_trace :=
  AssumeReg "cur_privilege" [] (RegVal_Base (Val_Enum "Machine")) Mk_annot :t:
  AssumeReg "rv_pmp_count" [] (RegVal_I 0%Z 64%Z) Mk_annot :t:
  AssumeReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  AssumeReg "rv_enable_misaligned_access" [] (RegVal_Base (Val_Bool false)) Mk_annot :t:
  AssumeReg "rv_ram_base" [] (RegVal_Base (Val_Bits (BV 64%N 0x80000000%Z))) Mk_annot :t:
  AssumeReg "rv_ram_size" [] (RegVal_Base (Val_Bits (BV 64%N 0x4000000%Z))) Mk_annot :t:
  AssumeReg "rv_rom_base" [] (RegVal_Base (Val_Bits (BV 64%N 0x1000%Z))) Mk_annot :t:
  AssumeReg "rv_rom_size" [] (RegVal_Base (Val_Bits (BV 64%N 0x100%Z))) Mk_annot :t:
  AssumeReg "rv_clint_base" [] (RegVal_Base (Val_Bits (BV 64%N 0x2000000%Z))) Mk_annot :t:
  AssumeReg "rv_clint_size" [] (RegVal_Base (Val_Bits (BV 64%N 0xc0000%Z))) Mk_annot :t:
  AssumeReg "rv_htif_tohost" [] (RegVal_Base (Val_Bits (BV 64%N 0x40001000%Z))) Mk_annot :t:
  Smt (DeclareConst 0%Z (Ty_BitVec 64%N)) Mk_annot :t:
  Assume (AExp_Binop ((Bvcomp Bvuge)) (AExp_Val (AVal_Var "x12" []) Mk_annot) (AExp_Val (AVal_Bits (BV 64%N 0x80000000%Z)) Mk_annot) Mk_annot) Mk_annot :t:
  Smt (Assert (Binop ((Bvcomp Bvuge)) (Val (Val_Symbolic 0%Z) Mk_annot) (Val (Val_Bits (BV 64%N 0x80000000%Z)) Mk_annot) Mk_annot)) Mk_annot :t:
  Assume (AExp_Binop ((Bvcomp Bvule)) (AExp_Val (AVal_Var "x12" []) Mk_annot) (AExp_Val (AVal_Bits (BV 64%N 0x83fffffc%Z)) Mk_annot) Mk_annot) Mk_annot :t:
  Smt (Assert (Binop ((Bvcomp Bvule)) (Val (Val_Symbolic 0%Z) Mk_annot) (Val (Val_Bits (BV 64%N 0x83fffffc%Z)) Mk_annot) Mk_annot)) Mk_annot :t:
  Assume (AExp_Binop (Eq) (AExp_Manyop (Bvmanyarith Bvand) [AExp_Val (AVal_Var "x12" []) Mk_annot; AExp_Val (AVal_Bits (BV 64%N 0x3%Z)) Mk_annot] Mk_annot) (AExp_Val (AVal_Bits (BV 64%N 0x0%Z)) Mk_annot) Mk_annot) Mk_annot :t:
  Smt (Assert (Binop (Eq) (Manyop (Bvmanyarith Bvand) [Val (Val_Symbolic 0%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x3%Z)) Mk_annot] Mk_annot) (Val (Val_Bits (BV 64%N 0x0%Z)) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DeclareConst 1%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "PC" [] (RegVal_Base (Val_Symbolic 1%Z)) Mk_annot :t:
  Smt (DefineConst 2%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 1%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x2%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  ReadReg "x12" [] (RegVal_Base (Val_Symbolic 0%Z)) Mk_annot :t:
  Smt (DefineConst 3%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 0%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x0%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  ReadReg "rv_enable_misaligned_access" [] (RegVal_Base (Val_Bool false)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Binop (Eq) (Unop (Extract 0%N 0%N) (Binop ((Bvarith Bvlshr)) (Val (Val_Symbolic 3%Z) Mk_annot) (Val (Val_Bits (BV 64%N 0x0%Z)) Mk_annot) Mk_annot) Mk_annot) (Val (Val_Bits (BV 1%N 0x1%Z)) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Binop (Eq) (Unop (Extract 0%N 0%N) (Binop ((Bvarith Bvlshr)) (Val (Val_Symbolic 3%Z) Mk_annot) (Val (Val_Bits (BV 64%N 0x1%Z)) Mk_annot) Mk_annot) Mk_annot) (Val (Val_Bits (BV 1%N 0x1%Z)) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  ReadReg "cur_privilege" [] (RegVal_Base (Val_Enum "Machine")) Mk_annot :t:
  Smt (DeclareConst 9%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "x15" [] (RegVal_Base (Val_Symbolic 9%Z)) Mk_annot :t:
  Smt (DefineConst 10%Z (Unop (Extract 31%N 0%N) (Val (Val_Symbolic 9%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  ReadReg "rv_pmp_count" [] (RegVal_I 0%Z 64%Z) Mk_annot :t:
  Smt (DefineConst 11%Z (Unop (ZeroExtend 64%N) (Val (Val_Symbolic 3%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  ReadReg "rv_clint_base" [] (RegVal_Base (Val_Bits (BV 64%N 0x2000000%Z))) Mk_annot :t:
  ReadReg "rv_clint_size" [] (RegVal_Base (Val_Bits (BV 64%N 0xc0000%Z))) Mk_annot :t:
  Smt (Assert (Binop ((Bvcomp Bvsle)) (Val (Val_Bits (BV 128%N 0x2000000%Z)) Mk_annot) (Val (Val_Symbolic 11%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Binop ((Bvcomp Bvsle)) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 11%Z) Mk_annot; Val (Val_Bits (BV 128%N 0x4%Z)) Mk_annot] Mk_annot) (Val (Val_Bits (BV 128%N 0x20c0000%Z)) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  ReadReg "rv_htif_tohost" [] (RegVal_Base (Val_Bits (BV 64%N 0x40001000%Z))) Mk_annot :t:
  Smt (Assert (Unop (Not) (Binop (Eq) (Val (Val_Bits (BV 64%N 0x40001000%Z)) Mk_annot) (Val (Val_Symbolic 3%Z) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Unop (Not) (Binop (Eq) (Val (Val_Bits (BV 64%N 0x40001004%Z)) Mk_annot) (Val (Val_Symbolic 3%Z) Mk_annot) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 17%Z (Unop (ZeroExtend 64%N) (Val (Val_Symbolic 3%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  ReadReg "rv_ram_base" [] (RegVal_Base (Val_Bits (BV 64%N 0x80000000%Z))) Mk_annot :t:
  ReadReg "rv_rom_base" [] (RegVal_Base (Val_Bits (BV 64%N 0x1000%Z))) Mk_annot :t:
  ReadReg "rv_ram_size" [] (RegVal_Base (Val_Bits (BV 64%N 0x4000000%Z))) Mk_annot :t:
  ReadReg "rv_rom_size" [] (RegVal_Base (Val_Bits (BV 64%N 0x100%Z))) Mk_annot :t:
  Smt (Assert (Binop ((Bvcomp Bvsle)) (Val (Val_Bits (BV 128%N 0x80000000%Z)) Mk_annot) (Val (Val_Symbolic 17%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (Assert (Binop ((Bvcomp Bvsle)) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 17%Z) Mk_annot; Val (Val_Bits (BV 128%N 0x4%Z)) Mk_annot] Mk_annot) (Val (Val_Bits (BV 128%N 0x84000000%Z)) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DeclareConst 21%Z Ty_Bool) Mk_annot :t:
  WriteMem (RegVal_Base (Val_Symbolic 21%Z)) (RegVal_Poison) (RegVal_Base (Val_Symbolic 3%Z)) (RegVal_Base (Val_Symbolic 10%Z)) 4%N None Mk_annot :t:
  WriteReg "PC" [] (RegVal_Base (Val_Symbolic 2%Z)) Mk_annot :t:
  tnil
.
