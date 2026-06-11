import os
from typing import List, Optional

import anthropic

from models.inputs import CampaignInputs
from models.outputs import Channel, ChannelSelection, GoalAnalysis, PricingModel

_CLIENT = None


def _client() -> anthropic.Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _CLIENT


_SELECT_TOOL = {
    "name": "select_channels",
    "description": (
        "Select the best advertising channels for a campaign given its funnel stage, "
        "target audience, budget, and product type."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "channels": {
                "type": "array",
                "description": "The selected channels, ordered from highest to lowest priority.",
                "minItems": 1,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": (
                                "The channel name, e.g. 'Google Search', 'Meta Ads', "
                                "'LinkedIn', 'TikTok', 'YouTube', 'Google Display'."
                            ),
                        },
                        "pricing_model": {
                            "type": "string",
                            "enum": ["CPC", "CPM", "CPA"],
                            "description": (
                                "The pricing model conventionally used to buy this channel: "
                                "CPC (cost-per-click), CPM (cost-per-thousand impressions), "
                                "or CPA (cost-per-acquisition)."
                            ),
                        },
                        "rationale": {
                            "type": "string",
                            "description": (
                                "One sentence explaining why this channel fits the specific "
                                "target audience described in the inputs."
                            ),
                        },
                    },
                    "required": ["name", "pricing_model", "rationale"],
                },
            }
        },
        "required": ["channels"],
    },
}

_SYSTEM_PROMPT = """\
You are a senior performance marketing strategist. Select the best advertising \
channels for a campaign based on funnel stage, target audience, budget, and product type.

## Channel-to-funnel-stage guidance

Awareness (goal: reach, brand exposure):
  Prefer: Meta Ads (CPM), YouTube (CPM), TikTok (CPM), Google Display (CPM)
  Avoid: intent-based channels where there is no existing demand to capture

Consideration (goal: engagement, education, comparison):
  Prefer: Google Search (CPC), LinkedIn (CPM or CPC), Meta Ads (CPC), YouTube (CPM)
  Avoid: pure reach channels with no engagement mechanic

Conversion (goal: purchase, signup, direct action):
  Prefer: Google Search (CPC), Google Shopping (CPC), Retargeting (CPA), LinkedIn (CPC)
  Avoid: broad awareness channels that cannot be tied to direct response

## Pricing model conventions (use these unless there is a strong reason not to)
- Google Search → CPC
- Google Shopping → CPC
- Google Display / Programmatic → CPM
- Meta Ads (Facebook / Instagram) → CPM for awareness, CPC for conversion
- LinkedIn → CPM for awareness/consideration, CPC for conversion
- TikTok → CPM
- YouTube → CPM
- Retargeting (any platform) → CPA
- Affiliate / influencer → CPA

## Hard rules (you must follow these)
1. Select between 1 and 3 channels. Never more than 3.
2. If the total budget is very low, select at most 2 channels.
3. If the product type is B2B, prefer LinkedIn over TikTok. If both would otherwise \
be selected, drop TikTok and keep LinkedIn.
4. If no existing channels are provided, ignore prior usage entirely and recommend \
from scratch based solely on funnel stage and audience.
5. Each rationale sentence must reference the specific audience described — never \
use generic phrases like "this channel reaches many users".

Always call the select_channels tool. Never reply in plain text.\
"""


def _build_user_message(
    inputs: CampaignInputs,
    goal: GoalAnalysis,
) -> str:
    lines = [
        f"Funnel stage: {goal.funnel_stage.value}",
        f"Funnel stage rationale: {goal.funnel_stage_rationale}",
        f"Target audience: {inputs.target_audience}",
        f"Total budget: {inputs.currency} {inputs.total_budget:,.2f}",
        f"Product type: {inputs.product_type or 'Not specified'}",
    ]

    if inputs.existing_channels:
        lines.append(f"Existing channels: {', '.join(inputs.existing_channels)}")
    else:
        lines.append("Existing channels: None — start fresh, no prior-usage bias.")

    return "\n".join(lines)


def _enforce_constraints(
    channels: List[Channel],
    total_budget: float,
    product_type: Optional[str],
) -> List[Channel]:
    # C4: B2B — remove TikTok when LinkedIn is present.
    if product_type and product_type.upper() == "B2B":
        has_linkedin = any("linkedin" in c.name.lower() for c in channels)
        if has_linkedin:
            channels = [c for c in channels if "tiktok" not in c.name.lower()]

    # C5/E5: budget very low → max 2 channels. C1: absolute max 3.
    channel_cap = 2 if total_budget < 1_000 else 3
    return channels[:channel_cap]


def select_channels(inputs: CampaignInputs, goal: GoalAnalysis) -> ChannelSelection:
    """
    Step 2 — select up to 3 advertising channels for the campaign.

    Constraints C1, C4, and C5/E5 are enforced in the prompt and again
    in _enforce_constraints() to guarantee the output regardless of model behaviour.
    """
    response = _client().messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        tools=[_SELECT_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": _build_user_message(inputs, goal)}],
    )

    tool_use_block = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )
    if tool_use_block is None:
        raise RuntimeError("Model did not call the select_channels tool.")

    raw_channels: List[dict] = tool_use_block.input["channels"]

    channels = [
        Channel(
            name=ch["name"],
            pricing_model=PricingModel(ch["pricing_model"]),
            rationale=ch["rationale"],
        )
        for ch in raw_channels
    ]

    channels = _enforce_constraints(channels, inputs.total_budget, inputs.product_type)

    return ChannelSelection(channels=channels)
