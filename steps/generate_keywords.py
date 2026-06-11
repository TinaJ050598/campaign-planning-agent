import os

import anthropic

from models.inputs import CampaignInputs
from models.outputs import GoalAnalysis, KeywordList

_CLIENT = None

_REQUIRED_COUNT = 5


def _client() -> anthropic.Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _CLIENT


_KEYWORD_TOOL = {
    "name": "generate_keywords",
    "description": (
        f"Generate exactly {_REQUIRED_COUNT} high-intent keywords for a campaign. "
        "Keywords must match the funnel stage intent level and be written in the "
        "target market's language."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "array",
                "minItems": _REQUIRED_COUNT,
                "maxItems": _REQUIRED_COUNT,
                "description": (
                    f"Exactly {_REQUIRED_COUNT} keywords. Each must be a real search "
                    "phrase a target audience member would type, specific to the brand "
                    "and product described. No placeholders, no generic terms."
                ),
                "items": {"type": "string"},
            }
        },
        "required": ["keywords"],
    },
}

_SYSTEM_PROMPT = """\
You are a specialist PPC and SEO keyword strategist. Generate exactly 5 high-intent \
keywords for a campaign.

## Intent level by funnel stage

Awareness — the audience does not yet know the brand or product category:
  Use informational and discovery phrases. Examples of patterns:
    "what is [product category]"
    "[product category] explained"
    "how does [product type] work"
    "[problem the product solves]"
  Avoid branded terms or transactional modifiers.

Consideration — the audience knows the category and is evaluating options:
  Use comparative and evaluative phrases. Examples of patterns:
    "best [product category]"
    "[product category] comparison"
    "[product category] reviews"
    "[product type] vs [alternative]"
    "top [product category] for [audience segment]"
  May include the brand name alongside category terms.

Conversion — the audience is ready to act:
  Use transactional phrases with clear purchase or signup intent. Examples of patterns:
    "buy [product name]"
    "[product name] pricing"
    "[product name] free trial"
    "[product name] sign up"
    "[product name] get started"
  Should include brand name where possible.

## Rules
1. Generate exactly 5 keywords — no more, no fewer.
2. All 5 keywords must be written in the specified target market language. If the \
language is not English, do not write in English and then translate — write directly \
in that language from the start.
3. Keywords must reflect the specific brand, product, and audience described — not \
generic category placeholders.
4. Each keyword must be a realistic search phrase a real user would type into a \
search engine or social platform.
5. No two keywords may be near-duplicates of each other.

Always call the generate_keywords tool. Never reply in plain text.\
"""


def generate_keywords(inputs: CampaignInputs, goal: GoalAnalysis) -> KeywordList:
    """
    Step 5 — generate exactly 5 high-intent keywords.

    C7 (exactly 5) is enforced via the tool schema (minItems/maxItems) and a
    hard Python length check after the call.
    """
    user_message = (
        f"Funnel stage: {goal.funnel_stage.value}\n"
        f"Target market language: {inputs.target_market_language}\n"
        f"Marketing goal: {inputs.marketing_goal}\n"
        f"Brand description: {inputs.brand_description}\n"
        f"Target audience: {inputs.target_audience}"
    )

    response = _client().messages.create(
        model="claude-opus-4-8",
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        tools=[_KEYWORD_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": user_message}],
    )

    tool_use_block = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )
    if tool_use_block is None:
        raise RuntimeError("Model did not call the generate_keywords tool.")

    keywords = tool_use_block.input["keywords"]

    # Hard enforcement of C7 — schema minItems/maxItems is advisory on some model
    # versions; the Python check is the authoritative gate.
    if len(keywords) != _REQUIRED_COUNT:
        raise ValueError(
            f"Expected exactly {_REQUIRED_COUNT} keywords, got {len(keywords)}."
        )

    # Strip accidental whitespace introduced by the model.
    keywords = [kw.strip() for kw in keywords]

    return KeywordList(keywords=keywords)
