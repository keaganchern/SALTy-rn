import Transpiler

open Transpiler

private def assertTrue (condition : Bool) (message : String) : Except String Unit :=
  if condition then pure () else throw message

private def tests : Except String Unit := do
  let rules ← loadRules
  assertTrue (rules.length == 191) "rule catalogue incomplete"
  let source := "void test_neon(const int8_t* a, int8_t* out) { int8x16_t v = vld1q_s8(a); vst1q_s8(out, v); }"
  let p ← parseC source
  let q ← transpile rules p
  let emitted := printC q
  assertTrue ((emitted.splitOn "__riscv_vle8_v_i8m1").length > 1) "load not lowered"
  assertTrue ((emitted.splitOn "test_rvv").length > 1) "entry not renamed"
  assertTrue ((emitted.splitOn "int8x16_t").length == 1) "NEON type remains"
  let again ← parseC emitted
  assertTrue (printC again == emitted) "RVV output does not roundtrip"
  let json := Lean.toJson p
  let decoded : Program ← Lean.fromJson? json
  assertTrue (p == decoded) "JSON AST loses information"
  for code in [
    "void f(void) { for (int i=0; i<4; i++) { if(i&1) continue; else break; } }",
    "void f(void) { int a[3] = {1, 2, 3}; do { a[1] += 1; } while(a[1]<4); }",
    "void f(void) { float x = -0x1.715476p+0f; int y = (1+2)*3; int z = 1-(2-3); }",
    "void f(void) { int a; int b; int c; a = b = c ? 1 : 2; }"
    , "void f(void) { for (int i=0, j=4; i<j; i++, j--) { } }"
    , "void f(void) { XNN_ALIGN(16) static const int32_t table[2] = {1,2}; }"
  ] do
    let parsed ← parseC code
    let printed := printC parsed
    assertTrue (printC (← parseC printed) == printed) s!"roundtrip failed: {code}"
  let tuple ← parseC "void test_neon(uint32_t* p) { uint32x2x2_t v; v.val[0] = vdup_n_u32(0); vst1_u32(p, v.val[0]); }"
  let tupleText := printC (← transpile rules tuple)
  assertTrue ((tupleText.splitOn "__riscv_vset_v_u32m1_u32m1x2").length > 1) "tuple write missing"
  assertTrue ((tupleText.splitOn "__riscv_vget_v_u32m1x2_u32m1").length > 1) "tuple read missing"
  let unknown ← parseC "void f(void) { vunknownq_f32(a); }"
  assertTrue ((transpile rules unknown).toOption.isNone) "unknown intrinsic silently accepted"
  let arity ← parseC "void f(void) { vaddq_s32(a); }"
  assertTrue ((transpile rules arity).toOption.isNone) "invalid intrinsic arity accepted"
  assertTrue ((parseC "void f(void) { goto label; }").toOption.isNone) "unsupported goto accepted"
  assertTrue ((parseC "void f(void) { int x = 1; ").toOption.isNone) "truncated input accepted"
  assertTrue ((lex "/* unterminated").toOption.isNone) "unterminated comment accepted"
  let selected ← selectArchitecture "#if XNN_ARCH_ARM64\nint x;\n#else\nfloat x;\n#endif\n"
  assertTrue (printC (← parseC selected) == "int x;\n") "architecture selection incorrect"
  assertTrue ((selectArchitecture "#if UNKNOWN\nint x;\n#endif").toOption.isNone) "unknown condition accepted"
  assertTrue ((selectArchitecture "#if XNN_ARCH_ARM64\nint x;").toOption.isNone) "unterminated conditional accepted"
  let defined ← selectArchitecture "#ifdef XNN_ARCH_ARM\nint x;\n#else\nfloat x;\n#endif"
  assertTrue (printC (← parseC defined) == "int x;\n") "defined macro with value zero was treated as undefined"
  let precedence ← parseC "int f(void) { return 1 + 2 * 3; }"
  match precedence.items with
  | [.function { body := some (.block [.returnStmt (some e)]), .. }] =>
    assertTrue (e == .binary "+" (.literal "1") (.binary "*" (.literal "2") (.literal "3"))) "C operator precedence lost"
  | _ => throw "unexpected expression AST"
  let bounds ← parseC "void f(void) { uint32x2x2_t v; v.val[2] = vdup_n_u32(0); }"
  assertTrue ((transpile rules bounds).toOption.isNone) "out-of-range tuple index accepted"
  let collision ← parseC "void f(void) { int salty_rvv_vld1_s8; }"
  assertTrue ((transpile rules collision).toOption.isNone) "generated helper can be shadowed"
  let sizes ← parseC "int f(void) { return sizeof(int8x16_t) + sizeof(uint32x2x2_t); }"
  let sizesText := printC (← transpile rules sizes)
  assertTrue ((sizesText.splitOn "(((size_t) 16) + ((size_t) 16))").length > 1)
    "fixed NEON sizeof value/type was not preserved"
  for (code, expected) in [
    ("void f(void) { if (x) ++x; }",
      Stmt.ifThen (.ident "x") (.expr (.unary "++" (.ident "x"))) none),
    ("void f(void) { while (x) --x; }",
      Stmt.whileLoop (.ident "x") (.expr (.unary "--" (.ident "x")))),
    ("void f(void) { if (x) *p = 1; }",
      Stmt.ifThen (.ident "x") (.expr (.binary "=" (.unary "*" (.ident "p")) (.literal "1"))) none),
    ("void f(void) { if XNN_LIKELY(x) ++x; }",
      Stmt.ifThen (.call (.ident "XNN_LIKELY") [.ident "x"])
        (.expr (.unary "++" (.ident "x"))) none)
  ] do
    let parsed ← parseC code
    match parsed.items with
    | [.function { body := some (.block [actual]), .. }] =>
      assertTrue (actual == expected) s!"condition consumed its body: {code}"
    | _ => throw s!"unexpected condition AST: {code}"
  for code in ["void f(void) { if x; }", "void f(void) { while x; }",
      "void f(void) { do {} while x; }"] do
    assertTrue ((parseC code).toOption.isNone) "missing condition parentheses accepted"
  for (expr, bytes) in [("v", 8), ("*p", 8), ("t.val[0]", 8), ("t", 16),
      ("vdup_n_u32(i++)", 8), ("(t.val[0] = v)", 8), ("(i++, v)", 8),
      ("(i ? v : v)", 8), ("identity(v)", 8)] do
    let parsed ← parseC ("uint32x2_t identity(uint32x2_t v) { return v; }\n" ++
      "size_t f(uint32x2_t v, uint32x2_t* p, uint32x2x2_t t, int i) { return sizeof " ++ expr ++ "; }")
    let lowered ← transpile rules parsed
    let expected := Expr.cast { base := .named "size_t" } (.literal (toString bytes))
    match lowered.items.getLast! with
    | .function { body := some (.block [.returnStmt (some actual)]), .. } =>
      assertTrue (actual == expected) s!"sizeof {expr} lost its source size/type"
    | _ => throw s!"unexpected sizeof lowering: {expr}"
  assertTrue ((parseC "void f(void) { for (if(1) break; ; ) {} }").toOption.isNone) "invalid for initializer accepted"

def main : IO UInt32 := do
  match tests with
  | .ok _ => IO.println "All transpiler unit tests passed"; return 0
  | .error e => (← IO.getStderr).putStrLn e; return 1
