import Transpiler.AST

namespace Transpiler

def printType (t : CType) : String :=
  let base := match t.base with
    | .named n => n
    | .record k n => k ++ " " ++ n
    | .vector v => v.spelling
  String.intercalate " " (t.qualifiers ++ [base]) ++
    String.join (t.pointers.map fun qs => " *" ++ if qs.isEmpty then "" else " " ++ String.intercalate " " qs)

partial def printExpr : Expr → String
  | .ident n | .literal n => n
  | .unary op a => "(" ++ op ++ " " ++ printExpr a ++ ")"
  | .postfix op a => "(" ++ printExpr a ++ op ++ ")"
  | .binary op a b => "(" ++ printExpr a ++ " " ++ op ++ " " ++ printExpr b ++ ")"
  | .conditional c y n => "(" ++ printExpr c ++ " ? " ++ printExpr y ++ " : " ++ printExpr n ++ ")"
  | .call f as => printExpr f ++ "(" ++ String.intercalate ", " (as.map printExpr) ++ ")"
  | .intrinsic op as =>
    let n := match op with | .neon n | .rvv n => n
    n ++ "(" ++ String.intercalate ", " (as.map printExpr) ++ ")"
  | .index b i => printExpr b ++ "[" ++ printExpr i ++ "]"
  | .member b f arrow => printExpr b ++ (if arrow then "->" else ".") ++ f
  | .cast ty e => "((" ++ printType ty ++ ") " ++ printExpr e ++ ")"
  | .sizeofType ty => "sizeof(" ++ printType ty ++ ")"
  | .initList es => "{" ++ String.intercalate ", " (es.map printExpr) ++ "}"

def printVar (v : VarDecl) : String :=
  (v.alignment.map fun e => "XNN_ALIGN(" ++ printExpr e ++ ") ").getD "" ++
  printType v.type ++ " " ++ v.name ++
    String.join (v.dimensions.map fun d => "[" ++ (d.map printExpr).getD "" ++ "]") ++
    (v.value.map fun e => " = " ++ printExpr e).getD ""

/-- A for initializer is one declaration, so repeat declarators, not base types. -/
private def printDeclGroup (vars : List VarDecl) : String :=
  match vars with
  | [] => ""
  | first :: _ =>
    let base := printType { first.type with pointers := [] }
    let tails := vars.map fun v =>
      String.join (v.type.pointers.map fun qs => "*" ++ String.intercalate " " qs ++ " ") ++
      v.name ++ String.join (v.dimensions.map fun d => "[" ++ (d.map printExpr).getD "" ++ "]") ++
      (v.value.map fun e => " = " ++ printExpr e).getD ""
    base ++ " " ++ String.intercalate ", " tails

private def pad (n : Nat) := String.ofList (List.replicate (2*n) ' ')

mutual
partial def printStmt (s : Stmt) (level : Nat := 0) : String :=
  let p := pad level
  match s with
  | .block body => p ++ "{\n" ++ String.join (body.map (fun s => printStmt s (level+1))) ++ p ++ "}\n"
  | .decl vs => String.join (vs.map fun v => p ++ printVar v ++ ";\n")
  | .expr e => p ++ printExpr e ++ ";\n"
  | .ifThen c y n => p ++ "if (" ++ printExpr c ++ ")\n" ++ printBranch y level ++
      (n.map fun s => p ++ "else\n" ++ printBranch s level).getD ""
  | .whileLoop c b => p ++ "while (" ++ printExpr c ++ ")\n" ++ printBranch b level
  | .doWhile b c => p ++ "do\n" ++ printBranch b level ++ p ++ "while (" ++ printExpr c ++ ");\n"
  | .forLoop init c step b =>
      let initText := match init with
        | .empty => ""
        | .expr e => printExpr e
        | .decl vs => printDeclGroup vs
      p ++ "for (" ++ initText ++ "; " ++ (c.map printExpr).getD "" ++ "; " ++
        (step.map printExpr).getD "" ++ ")\n" ++ printBranch b level
  | .returnStmt e => p ++ "return" ++ (e.map fun x => " " ++ printExpr x).getD "" ++ ";\n"
  | .breakStmt => p ++ "break;\n"
  | .continueStmt => p ++ "continue;\n"
  | .empty => p ++ ";\n"
  | .directive t => t ++ "\n"

private partial def printBranch (s : Stmt) (level : Nat) : String :=
  match s with
  | .block _ => printStmt s level
  | _ => printStmt (.block [s]) level
end

partial def printFields (fs : List RecordField) (level : Nat) : String :=
  String.join (fs.map fun f => match f with
    | .vars vs => String.join (vs.map fun v => pad level ++ printVar v ++ ";\n")
    | .nested kind tag fs name => pad level ++ kind ++ " " ++ tag ++ " {\n" ++
        printFields fs (level+1) ++ pad level ++ "} " ++ name ++ ";\n"
    | .directive t => t ++ "\n")

def printFunction (f : Function) : String :=
  printType f.result ++ " " ++ f.name ++ "(" ++
    (if f.params.isEmpty then "void" else String.intercalate ", " (f.params.map printVar)) ++ ")" ++
    String.join (f.attributes.map (" " ++ ·)) ++
    match f.body with | none => ";\n" | some b => "\n" ++ printStmt b

def printC (p : Program) : String :=
  String.intercalate "\n" (p.items.map fun item => match item with
    | .function f => printFunction f
    | .globals vs => String.join (vs.map fun v => printVar v ++ ";\n")
    | .record k n fs => k ++ " " ++ n ++ " {\n" ++ printFields fs 1 ++ "};\n"
    | .directive t => t ++ "\n")

end Transpiler
