From isla Require Import opsem.
Require Import Reduction.RVV.RvvLiterals Reduction.Generated.RVV.a800001d6.

Definition a800001d6_shared : isla_trace :=
  AssumeReg "vlen" [] (RegVal_Base (Val_Bits (BV 4%N 0x3%Z))) Mk_annot :t:
  AssumeReg "misa" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000200104%Z)))]) Mk_annot :t:
  AssumeReg "rv_enable_zfinx" [] (RegVal_Base (Val_Bool false)) Mk_annot :t:
  AssumeReg "rv_enable_vext" [] (RegVal_Base (Val_Bool true)) Mk_annot :t:
  AssumeReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  AssumeReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
  AssumeReg "vlenb" [] (RegVal_Base (Val_Bits (BV 64%N 0x20%Z))) Mk_annot :t:
  AssumeReg "vtype" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x90%Z)))]) Mk_annot :t:
  Smt (DeclareConst 0%Z (Ty_BitVec 64%N)) Mk_annot :t:
  Assume (AExp_Binop ((Bvcomp Bvule)) (AExp_Val (AVal_Var "vl" []) Mk_annot) (AExp_Val (AVal_Bits (BV 64%N 0x8%Z)) Mk_annot) Mk_annot) Mk_annot :t:
  Smt (Assert (Binop ((Bvcomp Bvule)) (Val (Val_Symbolic 0%Z) Mk_annot) (Val (Val_Bits (BV 64%N 0x8%Z)) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DeclareConst 1%Z (Ty_BitVec 64%N)) Mk_annot :t:
  ReadReg "PC" [] (RegVal_Base (Val_Symbolic 1%Z)) Mk_annot :t:
  Smt (DefineConst 2%Z (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 1%Z) Mk_annot; Val (Val_Bits (BV 64%N 0x4%Z)) Mk_annot] Mk_annot)) Mk_annot :t:
  ReadReg "misa" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000200104%Z)))]) Mk_annot :t:
  ReadReg "rv_enable_zfinx" [] (RegVal_Base (Val_Bool false)) Mk_annot :t:
  ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
  ReadReg "vtype" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x90%Z)))]) Mk_annot :t:
  ReadReg "vlen" [] (RegVal_Base (Val_Bits (BV 4%N 0x3%Z))) Mk_annot :t:
  ReadReg "vlenb" [] (RegVal_Base (Val_Bits (BV 64%N 0x20%Z))) Mk_annot :t:
  Smt (DeclareConst 4%Z (Ty_BitVec 65536%N)) Mk_annot :t:
  ReadReg "vr0" [] (RegVal_Base (Val_Symbolic 4%Z)) Mk_annot :t:
  Smt (DeclareConst 8%Z (Ty_BitVec 65536%N)) Mk_annot :t:
  ReadReg "vr16" [] (RegVal_Base (Val_Symbolic 8%Z)) Mk_annot :t:
  Smt (DefineConst 10%Z (Unop (Extract 31%N 0%N) (Val (Val_Symbolic 8%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 11%Z (Unop (Extract 63%N 32%N) (Val (Val_Symbolic 8%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 12%Z (Unop (Extract 95%N 64%N) (Val (Val_Symbolic 8%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 13%Z (Unop (Extract 127%N 96%N) (Val (Val_Symbolic 8%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 14%Z (Unop (Extract 159%N 128%N) (Val (Val_Symbolic 8%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 15%Z (Unop (Extract 191%N 160%N) (Val (Val_Symbolic 8%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 16%Z (Unop (Extract 223%N 192%N) (Val (Val_Symbolic 8%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 17%Z (Unop (Extract 255%N 224%N) (Val (Val_Symbolic 8%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DeclareConst 20%Z (Ty_BitVec 65536%N)) Mk_annot :t:
  ReadReg "vr8" [] (RegVal_Base (Val_Symbolic 20%Z)) Mk_annot :t:
  Smt (DefineConst 22%Z (Unop (Extract 31%N 0%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 23%Z (Unop (Extract 63%N 32%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 24%Z (Unop (Extract 95%N 64%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 25%Z (Unop (Extract 127%N 96%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 26%Z (Unop (Extract 159%N 128%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 27%Z (Unop (Extract 191%N 160%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 28%Z (Unop (Extract 223%N 192%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 29%Z (Unop (Extract 255%N 224%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 33%Z (Unop (Extract 31%N 0%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 34%Z (Unop (Extract 63%N 32%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 35%Z (Unop (Extract 95%N 64%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 36%Z (Unop (Extract 127%N 96%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 37%Z (Unop (Extract 159%N 128%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 38%Z (Unop (Extract 191%N 160%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 39%Z (Unop (Extract 223%N 192%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 40%Z (Unop (Extract 255%N 224%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  ReadReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
  ReadReg "vl" [] (RegVal_Base (Val_Symbolic 0%Z)) Mk_annot :t:
  Smt (DefineConst 44%Z (Binop ((Bvarith Bvsub)) (Unop (ZeroExtend 64%N) (Val (Val_Symbolic 0%Z) Mk_annot) Mk_annot) (Val (Val_Bits (BV 128%N 0x1%Z)) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 47%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x0%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  tcases [
    Smt (Assert (Val (Val_Symbolic 47%Z) Mk_annot)) Mk_annot :t:
    Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x1%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x2%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x3%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x4%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x5%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x6%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (DefineConst 80%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 40%Z) Mk_annot) Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 39%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 38%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 37%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 36%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 35%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 34%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
    WriteReg "vr8" [] (RegVal_Base (Val_Symbolic 80%Z)) Mk_annot :t:
    ReadReg "rv_enable_vext" [] (RegVal_Base (Val_Bool true)) Mk_annot :t:
    ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
    ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
    WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
    ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
    ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
    WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
    WriteReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
    WriteReg "PC" [] (RegVal_Base (Val_Symbolic 2%Z)) Mk_annot :t:
    tnil;
    Smt (Assert (Unop (Not) (Val (Val_Symbolic 47%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (DefineConst 81%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x1%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    tcases [
      Smt (Assert (Val (Val_Symbolic 81%Z) Mk_annot)) Mk_annot :t:
      Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x2%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x3%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x4%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x5%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x6%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      Smt (DefineConst 114%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 40%Z) Mk_annot) Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 39%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 38%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 37%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 36%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 35%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 34%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 22%Z) Mk_annot; Val (Val_Symbolic 10%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
      WriteReg "vr8" [] (RegVal_Base (Val_Symbolic 114%Z)) Mk_annot :t:
      ReadReg "rv_enable_vext" [] (RegVal_Base (Val_Bool true)) Mk_annot :t:
      ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
      ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
      WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
      ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
      ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
      WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
      WriteReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
      WriteReg "PC" [] (RegVal_Base (Val_Symbolic 2%Z)) Mk_annot :t:
      tnil;
      Smt (Assert (Unop (Not) (Val (Val_Symbolic 81%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      Smt (DefineConst 115%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x2%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      tcases [
        Smt (Assert (Val (Val_Symbolic 115%Z) Mk_annot)) Mk_annot :t:
        Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x3%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
        Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x4%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
        Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x5%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
        Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x6%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
        Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
        Smt (DefineConst 148%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 40%Z) Mk_annot) Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 39%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 38%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 37%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 36%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 35%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 23%Z) Mk_annot; Val (Val_Symbolic 11%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 22%Z) Mk_annot; Val (Val_Symbolic 10%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
        WriteReg "vr8" [] (RegVal_Base (Val_Symbolic 148%Z)) Mk_annot :t:
        ReadReg "rv_enable_vext" [] (RegVal_Base (Val_Bool true)) Mk_annot :t:
        ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
        ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
        WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
        ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
        ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
        WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
        WriteReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
        WriteReg "PC" [] (RegVal_Base (Val_Symbolic 2%Z)) Mk_annot :t:
        tnil;
        Smt (Assert (Unop (Not) (Val (Val_Symbolic 115%Z) Mk_annot) Mk_annot)) Mk_annot :t:
        Smt (DefineConst 149%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x3%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
        tcases [
          Smt (Assert (Val (Val_Symbolic 149%Z) Mk_annot)) Mk_annot :t:
          Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x4%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
          Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x5%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
          Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x6%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
          Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
          Smt (DefineConst 182%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 40%Z) Mk_annot) Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 39%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 38%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 37%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 36%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 24%Z) Mk_annot; Val (Val_Symbolic 12%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 23%Z) Mk_annot; Val (Val_Symbolic 11%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 22%Z) Mk_annot; Val (Val_Symbolic 10%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
          WriteReg "vr8" [] (RegVal_Base (Val_Symbolic 182%Z)) Mk_annot :t:
          ReadReg "rv_enable_vext" [] (RegVal_Base (Val_Bool true)) Mk_annot :t:
          ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
          ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
          WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
          ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
          ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
          WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
          WriteReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
          WriteReg "PC" [] (RegVal_Base (Val_Symbolic 2%Z)) Mk_annot :t:
          tnil;
          Smt (Assert (Unop (Not) (Val (Val_Symbolic 149%Z) Mk_annot) Mk_annot)) Mk_annot :t:
          Smt (DefineConst 183%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x4%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
          tcases [
            Smt (Assert (Val (Val_Symbolic 183%Z) Mk_annot)) Mk_annot :t:
            Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x5%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
            Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x6%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
            Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
            Smt (DefineConst 216%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 40%Z) Mk_annot) Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 39%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 38%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 37%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 25%Z) Mk_annot; Val (Val_Symbolic 13%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 24%Z) Mk_annot; Val (Val_Symbolic 12%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 23%Z) Mk_annot; Val (Val_Symbolic 11%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 22%Z) Mk_annot; Val (Val_Symbolic 10%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
            WriteReg "vr8" [] (RegVal_Base (Val_Symbolic 216%Z)) Mk_annot :t:
            ReadReg "rv_enable_vext" [] (RegVal_Base (Val_Bool true)) Mk_annot :t:
            ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
            ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
            WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
            ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
            ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
            WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
            WriteReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
            WriteReg "PC" [] (RegVal_Base (Val_Symbolic 2%Z)) Mk_annot :t:
            tnil;
            Smt (Assert (Unop (Not) (Val (Val_Symbolic 183%Z) Mk_annot) Mk_annot)) Mk_annot :t:
            Smt (DefineConst 217%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x5%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
            tcases [
              Smt (Assert (Val (Val_Symbolic 217%Z) Mk_annot)) Mk_annot :t:
              Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x6%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
              Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
              Smt (DefineConst 250%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 40%Z) Mk_annot) Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 39%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 38%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 26%Z) Mk_annot; Val (Val_Symbolic 14%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 25%Z) Mk_annot; Val (Val_Symbolic 13%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 24%Z) Mk_annot; Val (Val_Symbolic 12%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 23%Z) Mk_annot; Val (Val_Symbolic 11%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 22%Z) Mk_annot; Val (Val_Symbolic 10%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
              WriteReg "vr8" [] (RegVal_Base (Val_Symbolic 250%Z)) Mk_annot :t:
              ReadReg "rv_enable_vext" [] (RegVal_Base (Val_Bool true)) Mk_annot :t:
              ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
              ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
              WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
              ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
              ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
              WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
              WriteReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
              WriteReg "PC" [] (RegVal_Base (Val_Symbolic 2%Z)) Mk_annot :t:
              tnil;
              Smt (Assert (Unop (Not) (Val (Val_Symbolic 217%Z) Mk_annot) Mk_annot)) Mk_annot :t:
              Smt (DefineConst 251%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x6%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
              tcases [
                Smt (Assert (Val (Val_Symbolic 251%Z) Mk_annot)) Mk_annot :t:
                Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
                Smt (DefineConst 284%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 40%Z) Mk_annot) Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 39%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 27%Z) Mk_annot; Val (Val_Symbolic 15%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 26%Z) Mk_annot; Val (Val_Symbolic 14%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 25%Z) Mk_annot; Val (Val_Symbolic 13%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 24%Z) Mk_annot; Val (Val_Symbolic 12%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 23%Z) Mk_annot; Val (Val_Symbolic 11%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 22%Z) Mk_annot; Val (Val_Symbolic 10%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
                WriteReg "vr8" [] (RegVal_Base (Val_Symbolic 284%Z)) Mk_annot :t:
                ReadReg "rv_enable_vext" [] (RegVal_Base (Val_Bool true)) Mk_annot :t:
                ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                WriteReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
                WriteReg "PC" [] (RegVal_Base (Val_Symbolic 2%Z)) Mk_annot :t:
                tnil;
                Smt (Assert (Unop (Not) (Val (Val_Symbolic 251%Z) Mk_annot) Mk_annot)) Mk_annot :t:
                Smt (DefineConst 285%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 44%Z) Mk_annot) Mk_annot)) Mk_annot :t:
                tcases [
                  Smt (Assert (Val (Val_Symbolic 285%Z) Mk_annot)) Mk_annot :t:
                  Smt (DefineConst 318%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 40%Z) Mk_annot) Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 28%Z) Mk_annot; Val (Val_Symbolic 16%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 27%Z) Mk_annot; Val (Val_Symbolic 15%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 26%Z) Mk_annot; Val (Val_Symbolic 14%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 25%Z) Mk_annot; Val (Val_Symbolic 13%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 24%Z) Mk_annot; Val (Val_Symbolic 12%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 23%Z) Mk_annot; Val (Val_Symbolic 11%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 22%Z) Mk_annot; Val (Val_Symbolic 10%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
                  WriteReg "vr8" [] (RegVal_Base (Val_Symbolic 318%Z)) Mk_annot :t:
                  ReadReg "rv_enable_vext" [] (RegVal_Base (Val_Bool true)) Mk_annot :t:
                  ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                  ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                  WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                  ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                  ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                  WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                  WriteReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
                  WriteReg "PC" [] (RegVal_Base (Val_Symbolic 2%Z)) Mk_annot :t:
                  tnil;
                  Smt (Assert (Unop (Not) (Val (Val_Symbolic 285%Z) Mk_annot) Mk_annot)) Mk_annot :t:
                  Smt (DefineConst 352%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 29%Z) Mk_annot; Val (Val_Symbolic 17%Z) Mk_annot] Mk_annot) Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 28%Z) Mk_annot; Val (Val_Symbolic 16%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 27%Z) Mk_annot; Val (Val_Symbolic 15%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 26%Z) Mk_annot; Val (Val_Symbolic 14%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 25%Z) Mk_annot; Val (Val_Symbolic 13%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 24%Z) Mk_annot; Val (Val_Symbolic 12%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 23%Z) Mk_annot; Val (Val_Symbolic 11%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits wide32) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Manyop (Bvmanyarith Bvadd) [Val (Val_Symbolic 22%Z) Mk_annot; Val (Val_Symbolic 10%Z) Mk_annot] Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
                  WriteReg "vr8" [] (RegVal_Base (Val_Symbolic 352%Z)) Mk_annot :t:
                  ReadReg "rv_enable_vext" [] (RegVal_Base (Val_Bool true)) Mk_annot :t:
                  ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                  ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                  WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                  ReadReg "mstatus" [Field "bits"] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                  ReadReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                  WriteReg "mstatus" [] (RegVal_Struct [("bits", RegVal_Base (Val_Bits (BV 64%N 0x8000000000000600%Z)))]) Mk_annot :t:
                  WriteReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
                  WriteReg "PC" [] (RegVal_Base (Val_Symbolic 2%Z)) Mk_annot :t:
                  tnil
                ]
              ]
            ]
          ]
        ]
      ]
    ]
  ]
.

Lemma a800001d6_shared_exact : a800001d6_shared = a800001d6.
Proof. reflexivity. Qed.
Print Assumptions a800001d6_shared_exact.
