"""
How each Claude model is asked to think, in one place (the first piece of switching models by a setting, 20 Nov 2026).

The plans are long JSON and the code checks them afterwards, so up-front thinking is turned OFF where the model allows it: thinking tokens share
max_tokens with the answer (at Sonnet 5.5's default effort a plan once used all 16,000 tokens on thinking and was never written). What each
model accepts differs (the claude-api reference, Nov 2026):
  * Sonnet 5.5: {"type": "disabled"} is a 400; "between_tools" turns it off (at effort high or below).
  * Haiku 5.5: "disabled" is accepted at effort high or below (its default is medium).
  * Opus 5.5: thinking cannot be disabled at all; the effort is the only control, so it runs at "low".
Sent through extra_body, because the pinned SDK (0.34.0) predates these parameters.
"""

_BY_MODEL = {
    "claude-sonnet-5-5": {"thinking": {"type": "between_tools"}},
    "claude-haiku-5-5": {"thinking": {"type": "disabled"}},
    "claude-opus-5-5": {"output_config": {"effort": "low"}},
}
_DEFAULT = {"thinking": {"type": "disabled"}}          # earlier models (Sonnet 5, Opus 4.x) accept "disabled"


def thinking_body(model: str) -> dict:
    """The extra_body for a Messages call on this model (a fresh dict: callers may not share and change it). CLAUDE_THINKING_OVERRIDE (a JSON
    object, for test runs) replaces it, e.g. '{"thinking": {"type": "adaptive"}, "output_config": {"effort": "medium"}}'."""
    import copy
    import json
    import os
    raw = os.environ.get("CLAUDE_THINKING_OVERRIDE", "").strip()
    if raw:
        try:
            val = json.loads(raw)
            if isinstance(val, dict):
                return val
        except ValueError:
            pass
    return copy.deepcopy(_BY_MODEL.get(str(model or ""), _DEFAULT))
