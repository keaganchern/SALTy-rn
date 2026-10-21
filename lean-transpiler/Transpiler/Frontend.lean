import Transpiler.Parser

namespace Transpiler

inductive SourceArch where
  | arm64 | arm
  deriving BEq, Repr

private partial def ppValue (arch : SourceArch) : Expr → Except String Nat
  | .ident "XNN_ARCH_ARM64" | .ident "__aarch64__" => pure (if arch == .arm64 then 1 else 0)
  | .ident "XNN_ARCH_ARM" | .ident "__arm__" => pure (if arch == .arm then 1 else 0)
  | .literal n => match n.toNat? with
    | some value => pure value
    | none => throw s!"unsupported preprocessing constant {n}"
  | .unary "!" e => return if (← ppValue arch e) == 0 then 1 else 0
  | .binary "||" a b => return if (← ppValue arch a) != 0 || (← ppValue arch b) != 0 then 1 else 0
  | .binary "&&" a b => return if (← ppValue arch a) != 0 && (← ppValue arch b) != 0 then 1 else 0
  | .binary "==" a b => return if (← ppValue arch a) == (← ppValue arch b) then 1 else 0
  | .binary "!=" a b => return if (← ppValue arch a) != (← ppValue arch b) then 1 else 0
  | .call (.ident "defined") [.ident "XNN_ARCH_ARM"]
  | .call (.ident "defined") [.ident "XNN_ARCH_ARM64"] => pure 1
  | .call (.ident "defined") [.ident n] => ppValue arch (.ident n)
  | e => throw s!"unsupported preprocessing expression {repr e}; use an external C preprocessor"

private def ppCondition (arch : SourceArch) (text : String) : Except String Bool := do
  let p ← parseC ("int condition(void) { return " ++ text ++ "; }")
  match p.items with
  | [.function { body := some (.block [.returnStmt (some e)]), .. }] =>
      return (← ppValue arch e) != 0
  | _ => throw "invalid preprocessing condition"

/-- Resolve only the source architecture conditionals used by the kernel corpus.
    Other conditional macros are rejected rather than silently treated as false.
    Lexing first keeps directives inside comments out of the preprocessing pass. -/
def selectArchitecture (source : String) (arch : SourceArch := .arm64) : Except String String := do
  let tokens ← lex source
  let mut active := true
  let mut stack : List (Bool × Bool × Bool) := [] -- parent active, branch taken, saw else
  let mut out : List String := []
  for token in tokens do
    let t := token.text.trimAscii.toString
    if t == "<eof>" then break
    if t.startsWith "#" then
      let words := ((t.drop 1).toString.trimAscii.toString.splitOn " ").filter (!·.isEmpty)
      let command := words.headD ""
      let rest := String.intercalate " " words.tail
      let rest := (rest.splitOn "//").headD "" |>.trimAscii.toString
      if ["if", "ifdef", "ifndef"].contains command then
        let cond ← if !active then pure false else
          if command == "if" then ppCondition arch rest else
            ppCondition arch ((if command == "ifndef" then "!" else "") ++ "defined(" ++ rest ++ ")")
        stack := (active, cond, false) :: stack
        active := active && cond
      else if command == "else" || command == "elif" then
        match stack with
        | [] => throw s!"{token.line}: unmatched #{command}"
        | (parent, taken, sawElse) :: tail =>
          if sawElse then throw s!"{token.line}: branch after #else"
          let cond ← if command == "else" then pure true
            else if !parent || taken then pure false else ppCondition arch rest
          active := parent && !taken && cond
          stack := (parent, taken || cond, command == "else") :: tail
      else if command == "endif" then
        match stack with
        | [] => throw s!"{token.line}: unmatched #endif"
        | (parent, _, _) :: tail => active := parent; stack := tail
      else if active then out := out ++ ["\n" ++ t ++ "\n"]
    else if active then out := out ++ [t]
  unless stack.isEmpty do throw "unterminated preprocessing conditional"
  return String.intercalate " " out

/-- SALTy source snippets carry parameter declarations in their leading comment.
    Only --kernel mode promotes that explicitly documented convention to syntax. -/
def exposeKernelParams (source : String) : String := Id.run do
  let s := source.trimAscii.toString
  unless s.startsWith "/*" do return source
  let chunks := ((s.drop 2).toString).splitOn "*/"
  let comment := (chunks.headD "").trimAscii.toString
  if comment.startsWith "struct " || comment.startsWith "union " then
    return comment ++ "\n" ++ String.intercalate "*/" chunks.tail
  return source

end Transpiler
