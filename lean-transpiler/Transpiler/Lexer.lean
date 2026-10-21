import Transpiler.AST

namespace Transpiler

structure Token where
  text : String
  line : Nat
  column : Nat
  deriving Repr, Inhabited

private def identStart (c : Char) := c.isAlpha || c == '_'
private def identRest (c : Char) := identStart c || c.isDigit

/-- C lexer, independent of Lean's tokenizer. Retains directives and exact literals. -/
def lex (source : String) : Except String (Array Token) := do
  let cs := source.toList.toArray
  let mut out := #[]
  let mut i := 0
  let mut line := 1
  let mut col := 1
  while i < cs.size do
    let c := cs[i]!
    let next := cs[i+1]?.getD '\x00'
    if c.isWhitespace then
      i := i + 1
      if c == '\n' then line := line + 1; col := 1 else col := col + 1
    else if c == '/' && next == '/' then
      while i < cs.size && cs[i]! != '\n' do i := i + 1; col := col + 1
    else if c == '/' && next == '*' then
      let start := line
      i := i + 2; col := col + 2
      while i < cs.size && !(cs[i]! == '*' && cs[i+1]?.getD '\x00' == '/') do
        if cs[i]! == '\n' then line := line + 1; col := 1 else col := col + 1
        i := i + 1
      if i == cs.size then throw s!"{start}: unterminated block comment"
      i := i + 2; col := col + 2
    else
      let start := i
      let startCol := col
      if c == '#' then
        while i < cs.size && cs[i]! != '\n' do
          if cs[i]! == '\\' && cs[i+1]?.getD '\x00' == '\n' then
            throw s!"{line}:{col}: multiline preprocessing directives are unsupported; preprocess first"
          i := i + 1
      else if identStart c then
        i := i + 1
        while i < cs.size && identRest cs[i]! do i := i + 1
      else if c.isDigit || (c == '.' && next.isDigit) then
        i := i + 1
        while i < cs.size && (identRest cs[i]! || cs[i]! == '.' ||
            ((cs[i]! == '+' || cs[i]! == '-') &&
              ['e', 'E', 'p', 'P'].contains cs[i-1]!)) do i := i + 1
      else if c == '"' || c == '\'' then
        i := i + 1
        while i < cs.size && cs[i]! != c do
          if cs[i]! == '\n' then throw s!"{line}:{startCol}: newline in literal"
          if cs[i]! == '\\' then i := i + 1
          i := i + 1
        if i >= cs.size then throw s!"{line}:{startCol}: unterminated literal"
        i := i + 1
      else
        let two := String.ofList [c, next]
        let three := two.push (cs[i+2]?.getD '\x00')
        if ["<<=", ">>=", "..."].contains three then i := i + 3
        else if ["->", "++", "--", "<<", ">>", "<=", ">=", "==", "!=", "&&", "||",
            "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^="].contains two then i := i + 2
        else if "{}[]();,:?~!%^&*+-=/<>.|".contains c then i := i + 1
        else throw s!"{line}:{col}: unsupported character {c}"
      let text := String.ofList ((cs.extract start i).toList)
      out := out.push ⟨text, line, startCol⟩
      col := col + i - start
  return out.push ⟨"<eof>", line, col⟩

end Transpiler
