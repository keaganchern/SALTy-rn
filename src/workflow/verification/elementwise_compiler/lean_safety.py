"""Small, self-contained lexical safety checks for generated Lean proofs."""

from __future__ import annotations


FORBIDDEN_LEAN_IDENTIFIERS = frozenset(
    {
        "admit",
        "axiom",
        "constant",
        "extern",
        "implemented_by",
        "elab_rules",
        "macro_rules",
        "native_decide",
        "opaque",
        "ofReduceBool",
        "partial",
        "run_cmd",
        "sorry",
        "sorryAx",
        "unsafe",
    }
)


class LeanLexError(ValueError):
    """A Lean source fragment could not be safely tokenized."""


def strip_lean_comments_and_strings(source: str) -> str:
    """Replace nested comments and strings with spaces while preserving offsets."""

    output = list(source)
    index = 0
    while index < len(source):
        if source.startswith("--", index):
            end = source.find("\n", index + 2)
            if end < 0:
                end = len(source)
            for position in range(index, end):
                output[position] = " "
            index = end
            continue
        if source.startswith("/-", index):
            depth = 1
            cursor = index + 2
            while cursor < len(source) and depth:
                if source.startswith("/-", cursor):
                    depth += 1
                    cursor += 2
                elif source.startswith("-/", cursor):
                    depth -= 1
                    cursor += 2
                else:
                    cursor += 1
            if depth:
                raise LeanLexError("unterminated Lean block comment")
            for position in range(index, cursor):
                if output[position] != "\n":
                    output[position] = " "
            index = cursor
            continue
        if source[index] == '"':
            cursor = index + 1
            escaped = False
            while cursor < len(source):
                character = source[cursor]
                if character == '"' and not escaped:
                    cursor += 1
                    break
                if character == "\\" and not escaped:
                    escaped = True
                else:
                    escaped = False
                cursor += 1
            else:
                raise LeanLexError("unterminated Lean string literal")
            for position in range(index, cursor):
                if output[position] != "\n":
                    output[position] = " "
            index = cursor
            continue
        index += 1
    return "".join(output)
