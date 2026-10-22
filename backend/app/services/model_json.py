"""
Reading the model's reply as JSON, without losing a paid plan to a small slip.

The commonest slip in Hindi text is an UNESCAPED DOUBLE QUOTE inside a string ("बच्चा "एक" बोलता है"). json.loads then fails far from the cause with "Expecting ':' delimiter".
A plan costs about 12 cents and the reply is paid for before it is read, so: try the reply as it is; if that fails, escape the quotes that cannot be structural and try again;
if that fails too, say WHERE and WHAT (the text around the error) so the cause can be seen, and let the caller ask the model once more (plan_service).

A quote inside a string is taken to END the string only if what follows it is valid JSON: a colon, a closing bracket or brace, or a comma followed by the start of a key or a value.
Anything else is a quote INSIDE the text, and is escaped. It cannot repair every case (an inner quote followed by ', "' looks structural): then the original error is reported.
"""
import json


class ModelJSONError(ValueError):
    """The model's reply is not valid JSON and could not be repaired."""


def _next_sig(text: str, i: int) -> int:
    n = len(text)
    while i < n and text[i] in " \t\r\n":
        i += 1
    return i if i < n else -1


def _looks_structural(text: str, j: int) -> bool:
    """text[j] is the first non-space character after a quote inside a string: does what follows make the quote a real end of the string?"""
    c = text[j]
    if c in "}]:":
        return True
    if c == ",":
        k = _next_sig(text, j + 1)
        return k != -1 and (text[k] in '"{[-' or text[k].isdigit() or text.startswith(("true", "false", "null"), k))
    return False


def repair_inner_quotes(text: str) -> tuple:
    """(text with the unescaped inner quotes escaped, how many were escaped). Only quotes inside a string VALUE are ever escaped: a KEY ends at its first quote, so a structurally broken
    object (a key with no colon) is left broken and reported, not turned into valid JSON with a merged key."""
    out, stack, expect_key = [], [], False
    in_str = is_key = esc = False
    fixed, i, n = 0, 0, len(text)
    while i < n:
        ch = text[i]
        if not in_str:
            out.append(ch)
            if ch == '"':
                in_str, is_key = True, bool(stack) and stack[-1] == "{" and expect_key
            elif ch in "{[":
                stack.append(ch)
                expect_key = ch == "{"
            elif ch in "}]":
                if stack:
                    stack.pop()
                expect_key = False
            elif ch == ",":
                expect_key = bool(stack) and stack[-1] == "{"
            elif ch == ":":
                expect_key = False
        elif esc:
            out.append(ch)
            esc = False
        elif ch == "\\":
            out.append(ch)
            esc = True
        elif ch == '"':
            if is_key:
                out.append(ch)
                in_str = False
            else:
                j = _next_sig(text, i + 1)
                if j == -1 or _looks_structural(text, j):
                    out.append(ch)
                    in_str = False
                else:
                    out.append('\\"')
                    fixed += 1
        else:
            out.append(ch)
        i += 1
    return "".join(out), fixed


def parse_model_json(text: str) -> tuple:
    """(data, note). note is '' when the reply was valid as it came, otherwise what was repaired. Raises ModelJSONError, with the text around the error, when it cannot be."""
    try:
        return json.loads(text), ""
    except json.JSONDecodeError as first:
        err = first
    try:                                                               # raw line breaks inside a string are accepted by strict=False
        return json.loads(text, strict=False), "accepted raw control characters inside text"
    except json.JSONDecodeError:
        pass
    fixed, n = repair_inner_quotes(text)
    if n:
        try:
            return json.loads(fixed, strict=False), f"escaped {n} unescaped double quote(s) inside text"
        except json.JSONDecodeError:
            pass
    s, e = max(0, err.pos - 70), min(len(text), err.pos + 70)
    raise ModelJSONError(f"the model's reply is not valid JSON ({err.msg} at character {err.pos} of {len(text)}). Around it: {text[s:e]!r}") from err
