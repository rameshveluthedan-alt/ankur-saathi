"""
Reading the model's reply as JSON, without losing a paid plan to a small slip.

The commonest slip in Hindi text is an UNESCAPED DOUBLE QUOTE inside a string ("बच्चा "एक" बोलता है"). json.loads then fails far from the cause with "Expecting ':' delimiter".
A plan costs about 12 cents and the reply is paid for before it is read, so: try the reply as it is; if that fails, escape the quotes that cannot be structural and try again;
if that fails too, say WHERE and WHAT (the text around the error) so the cause can be seen, and let the caller ask the model once more (plan_service).

A quote inside a string is taken to END the string only if what follows it is valid JSON: a colon, a closing bracket or brace, or a comma followed by the start of a key or a value.
Anything else is a quote INSIDE the text, and is escaped. It cannot repair every case (an inner quote followed by ', "' looks structural): then the original error is reported.

The second slip, found on the first Generate in the cloud (24 Oct): ONE CLOSING BRACKET TOO MANY (`..."shows_hi":""}]}},{"type":"transition"...`: a teach block closed twice). json.loads fails with "Expecting ',' delimiter"
exactly AT the stray bracket: a closer where only a comma or the other kind of closer could stand. The smallest repair is to remove that one character and read again (repeated a few times, never more than a handful). It loses
no content, and what it cannot fix (a missing bracket, a missing comma, a text that is cut off) is left as it was: then the caller asks the model once more, a second full call that costs the same time and money as the first
(about 60 seconds and 14 cents).
NOT repaired on purpose: "Extra data" (a closer left over AT THE END). It looks the same whether the model wrote one harmless } too many at the end, or an EARLIER stray } closed a parent object too soon and moved a key up a
level (the first version of this repair removed the last } in that case, the text parsed, and `independent_activities_hi` had silently moved out of `classroom_management`: found by tests/test_model_json_closers.py).
A reply that parses but is a DIFFERENT plan is worse than a second call, so that case asks the model again.
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


STRAY_CLOSER_LIMIT = 8            # a handful at most: a reply with more than this is broken in a way a bracket-removal should not guess at


def repair_stray_closers(text: str) -> tuple:
    """(text without its stray closing brackets, how many were removed). Only ever acts where json.loads FIRST fails at a } or ] with "Expecting ',' delimiter" (a closer where only a comma or the other kind of closer could
    stand): that character is removed and the text is read again. Any other first error (a missing comma, a missing bracket, a cut-off text, a trailing comma, a quote problem, and "Extra data": see the module note) stops the
    repair at once, so it never edits anything it does not understand."""
    removed = 0
    for _ in range(STRAY_CLOSER_LIMIT):
        try:
            json.loads(text, strict=False)
            return text, removed
        except json.JSONDecodeError as e:
            if e.pos < len(text) and text[e.pos] in "}]" and e.msg.startswith("Expecting ',' delimiter"):
                text = text[:e.pos] + text[e.pos + 1:]
                removed += 1
                continue
            return text, removed
    return text, removed


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
    for base, quotes in ((text, 0), (fixed, n)) if n else ((text, 0),):          # a stray closing bracket, with or without the quote repair
        cleaned, k = repair_stray_closers(base)
        if k:
            try:
                data = json.loads(cleaned, strict=False)
            except json.JSONDecodeError:
                continue
            return data, f"removed {k} stray closing bracket(s)" + (f" and escaped {quotes} unescaped double quote(s) inside text" if quotes else "")
    s, e = max(0, err.pos - 70), min(len(text), err.pos + 70)
    raise ModelJSONError(f"the model's reply is not valid JSON ({err.msg} at character {err.pos} of {len(text)}). Around it: {text[s:e]!r}") from err
