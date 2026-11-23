"""
The price of each Claude model, for the app's own spending meter (ai_budget). 22 Nov 2026.

Until now the meter had ONE set of prices (AI_PRICE_*) and used it for every call, whatever model made it: right only while every call is
the same model. The block library was made with Opus but metered at Sonnet's prices ($21 metered, $24.28 billed), and a later switch of
CLAUDE_MODEL or CLAUDE_VISION_MODEL would have needed all four prices changed by hand. Now each call is priced by the model it names
(ai_usage.model, recorded with every call), so mixing models is metered right, and history is re-priced if a price here is corrected.

Which price is used, first match wins:
  1. AI_MODEL_PRICES, a setting: JSON {"model-id": [input, output, cache_read, cache_write]} to correct a price without a code change;
  2. this table: the exact model id, or the longest table id it starts with (a dated id such as 'claude-sonnet-5-5-20261001');
  3. the AI_PRICE_* settings: for a model not in the table, and for an old row with no model recorded.

USD per million tokens. Source: the Anthropic API reference bundled with Claude Code (Nov 2026); confirm against
https://platform.claude.com/docs/en/about-claude/pricing before relying on a figure. Cache write is the 5-minute cache (the app's only kind):
1.25x the input price. A Message Batch is billed at half these prices; the meter does not know a call was batched, so a batch call is
metered at the full price: a safe over-estimate (scripts/library_batch.py).
"""

import json

# (input, output, cache read, cache write)
PRICES = {
    "claude-sonnet-5-5": (2.00, 10.00, 0.10, 2.50),
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
    # Haiku: $0.10 / $0.50 for a prompt of 100K tokens or fewer (the app's are about 15K); above that $0.50 / $2.50, which this does not model.
    # Its cache-read price is NOT given in the reference: 0.1x input is assumed (Sonnet 5.5 and Opus 5.5 are 0.05x, so this errs high).
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125),
}


def _override() -> dict:
    from app.core.config import get_settings
    raw = (getattr(get_settings(), "ai_model_prices", "") or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return {str(k): tuple(float(x) for x in v) for k, v in data.items() if isinstance(v, (list, tuple)) and len(v) == 4}
    except (ValueError, TypeError, AttributeError):
        print("   WARNING: AI_MODEL_PRICES is not valid JSON of the form {\"model\": [in, out, cache_read, cache_write]}: ignored")
        return {}


def _match(table: dict, model: str):
    if model in table:
        return table[model]
    best = max((k for k in table if model.startswith(k + "-")), key=len, default=None)
    return table[best] if best else None


def prices_for(model) -> tuple:
    """(input, output, cache_read, cache_write) in USD per million tokens for this model (see the module note for the order)."""
    if model:
        found = _match(_override(), str(model)) or _match(PRICES, str(model))
        if found:
            return found
    from app.core.config import get_settings
    s = get_settings()
    return (s.ai_price_input_per_mtok, s.ai_price_output_per_mtok, s.ai_price_cache_read_per_mtok, s.ai_price_cache_write_per_mtok)


def source_of(model) -> str:
    """Where prices_for(model) takes its figures from, for the usage report."""
    if model and _match(_override(), str(model)):
        return "AI_MODEL_PRICES"
    if model and _match(PRICES, str(model)):
        return "the table"
    return "AI_PRICE_* (not in the table)"
