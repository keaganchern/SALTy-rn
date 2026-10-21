From isla Require Import opsem.

Definition a800001d2 : isla_trace :=
  AssumeReg "elen" [] (RegVal_Base (Val_Bits (BV 1%N 0x1%Z))) Mk_annot :t:
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
  ReadReg "vlenb" [] (RegVal_Base (Val_Bits (BV 64%N 0x20%Z))) Mk_annot :t:
  ReadReg "elen" [] (RegVal_Base (Val_Bits (BV 1%N 0x1%Z))) Mk_annot :t:
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
  ReadReg "vr2" [] (RegVal_Base (Val_Symbolic 20%Z)) Mk_annot :t:
  Smt (DefineConst 22%Z (Unop (Extract 7%N 0%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 23%Z (Unop (Extract 15%N 8%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 24%Z (Unop (Extract 23%N 16%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 25%Z (Unop (Extract 31%N 24%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 26%Z (Unop (Extract 39%N 32%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 27%Z (Unop (Extract 47%N 40%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 28%Z (Unop (Extract 55%N 48%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 29%Z (Unop (Extract 63%N 56%N) (Val (Val_Symbolic 20%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  ReadReg "vstart" [] (RegVal_Base (Val_Bits (BV 16%N 0x0%Z))) Mk_annot :t:
  ReadReg "vlen" [] (RegVal_Base (Val_Bits (BV 4%N 0x3%Z))) Mk_annot :t:
  ReadReg "vl" [] (RegVal_Base (Val_Symbolic 0%Z)) Mk_annot :t:
  Smt (DefineConst 33%Z (Binop ((Bvarith Bvsub)) (Unop (ZeroExtend 64%N) (Val (Val_Symbolic 0%Z) Mk_annot) Mk_annot) (Val (Val_Bits (BV 128%N 0x1%Z)) Mk_annot) Mk_annot)) Mk_annot :t:
  Smt (DefineConst 36%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x0%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
  tcases [
    Smt (Assert (Val (Val_Symbolic 36%Z) Mk_annot)) Mk_annot :t:
    Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x1%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x2%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x3%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x4%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x5%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x6%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (DefineConst 69%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 17%Z) Mk_annot) Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 16%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 15%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 14%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 13%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 12%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 11%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 10%Z) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
    WriteReg "vr16" [] (RegVal_Base (Val_Symbolic 69%Z)) Mk_annot :t:
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
    Smt (Assert (Unop (Not) (Val (Val_Symbolic 36%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    Smt (DefineConst 70%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x1%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
    tcases [
      Smt (Assert (Val (Val_Symbolic 70%Z) Mk_annot)) Mk_annot :t:
      Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x2%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x3%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x4%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x5%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x6%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      Smt (DefineConst 103%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 17%Z) Mk_annot) Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 16%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 15%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 14%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 13%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 12%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 11%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 22%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
      WriteReg "vr16" [] (RegVal_Base (Val_Symbolic 103%Z)) Mk_annot :t:
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
      Smt (Assert (Unop (Not) (Val (Val_Symbolic 70%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      Smt (DefineConst 104%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x2%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
      tcases [
        Smt (Assert (Val (Val_Symbolic 104%Z) Mk_annot)) Mk_annot :t:
        Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x3%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
        Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x4%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
        Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x5%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
        Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x6%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
        Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
        Smt (DefineConst 137%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 17%Z) Mk_annot) Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 16%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 15%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 14%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 13%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 12%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 23%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 22%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
        WriteReg "vr16" [] (RegVal_Base (Val_Symbolic 137%Z)) Mk_annot :t:
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
        Smt (Assert (Unop (Not) (Val (Val_Symbolic 104%Z) Mk_annot) Mk_annot)) Mk_annot :t:
        Smt (DefineConst 138%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x3%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
        tcases [
          Smt (Assert (Val (Val_Symbolic 138%Z) Mk_annot)) Mk_annot :t:
          Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x4%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
          Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x5%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
          Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x6%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
          Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
          Smt (DefineConst 171%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 17%Z) Mk_annot) Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 16%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 15%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 14%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 13%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 24%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 23%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 22%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
          WriteReg "vr16" [] (RegVal_Base (Val_Symbolic 171%Z)) Mk_annot :t:
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
          Smt (Assert (Unop (Not) (Val (Val_Symbolic 138%Z) Mk_annot) Mk_annot)) Mk_annot :t:
          Smt (DefineConst 172%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x4%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
          tcases [
            Smt (Assert (Val (Val_Symbolic 172%Z) Mk_annot)) Mk_annot :t:
            Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x5%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
            Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x6%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
            Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
            Smt (DefineConst 205%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 17%Z) Mk_annot) Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 16%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 15%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 14%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 25%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 24%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 23%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 22%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
            WriteReg "vr16" [] (RegVal_Base (Val_Symbolic 205%Z)) Mk_annot :t:
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
            Smt (Assert (Unop (Not) (Val (Val_Symbolic 172%Z) Mk_annot) Mk_annot)) Mk_annot :t:
            Smt (DefineConst 206%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x5%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
            tcases [
              Smt (Assert (Val (Val_Symbolic 206%Z) Mk_annot)) Mk_annot :t:
              Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x6%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
              Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
              Smt (DefineConst 239%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 17%Z) Mk_annot) Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 16%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 15%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 26%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 25%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 24%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 23%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 22%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
              WriteReg "vr16" [] (RegVal_Base (Val_Symbolic 239%Z)) Mk_annot :t:
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
              Smt (Assert (Unop (Not) (Val (Val_Symbolic 206%Z) Mk_annot) Mk_annot)) Mk_annot :t:
              Smt (DefineConst 240%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x6%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
              tcases [
                Smt (Assert (Val (Val_Symbolic 240%Z) Mk_annot)) Mk_annot :t:
                Smt (Assert (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
                Smt (DefineConst 273%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 17%Z) Mk_annot) Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 16%Z) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 27%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 26%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 25%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 24%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 23%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 22%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
                WriteReg "vr16" [] (RegVal_Base (Val_Symbolic 273%Z)) Mk_annot :t:
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
                Smt (Assert (Unop (Not) (Val (Val_Symbolic 240%Z) Mk_annot) Mk_annot)) Mk_annot :t:
                Smt (DefineConst 274%Z (Binop ((Bvcomp Bvsgt)) (Val (Val_Bits (BV 128%N 0x7%Z)) Mk_annot) (Val (Val_Symbolic 33%Z) Mk_annot) Mk_annot)) Mk_annot :t:
                tcases [
                  Smt (Assert (Val (Val_Symbolic 274%Z) Mk_annot)) Mk_annot :t:
                  Smt (DefineConst 307%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Val (Val_Symbolic 17%Z) Mk_annot) Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 28%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 27%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 26%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 25%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 24%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 23%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 22%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
                  WriteReg "vr16" [] (RegVal_Base (Val_Symbolic 307%Z)) Mk_annot :t:
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
                  Smt (Assert (Unop (Not) (Val (Val_Symbolic 274%Z) Mk_annot) Mk_annot)) Mk_annot :t:
                  Smt (DefineConst 341%Z (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Manyop (Bvmanyarith Bvor) [Binop ((Bvarith Bvshl)) (Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 29%Z) Mk_annot) Mk_annot) Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 28%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 27%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 26%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 25%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 24%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 23%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot) (Val (Val_Bits (BV 65536%N 0x20%Z)) Mk_annot) Mk_annot; Unop (ZeroExtend 65504%N) (Unop (ZeroExtend 24%N) (Val (Val_Symbolic 22%Z) Mk_annot) Mk_annot) Mk_annot] Mk_annot)) Mk_annot :t:
                  WriteReg "vr16" [] (RegVal_Base (Val_Symbolic 341%Z)) Mk_annot :t:
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
