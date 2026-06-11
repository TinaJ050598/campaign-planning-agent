import os
from typing import List

import anthropic

from models.inputs import CampaignInputs
from models.outputs import BudgetAllocation, ChannelBudget, ChannelSelection, GoalAnalysis

_CLIENT = None


def _client() -> anthropic.Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _CLIENT


_ALLOCATE_TOOL = {
    "name": "allocate_budget",
    "description": (
        "Distribute a campaign budget across selected channels. "
        "Return a percentage allocation and a justification for each channel. "
        "Do not return absolute amounts — those are computed from your percentages."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "allocations": {
                "type": "array",
                "description": (
                    "One entry per channel, in descending order of budget priority "
                    "(largest allocation first)."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "channel_name": {
                            "type": "string",
                            "description": "Must exactly match one of the provided channel names.",
                        },
                        "percentage": {
                            "type": "number",
                            "minimum": 1,
                            "maximum": 99,
                            "description": (
                                "Whole-number percentage of the total budget assigned to "
                                "this channel. All percentages across all channels must "
                                "sum to exactly 100."
                            ),
                        },
                        "justification": {
                            "type": "string",
                            "description": (
                                "One sentence explaining why this channel receives this "
                                "share, referencing its priority role in the funnel stage "
                                "relative to the other channels."
                            ),
                        },
                    },
                    "required": ["channel_name", "percentage", "justification"],
                },
            }
        },
        "required": ["allocations"],
    },
}

_SYSTEM_PROMPT = """\
You are a senior performance marketing strategist allocating a campaign budget \
across a fixed set of channels.

## Your task
Assign a percentage of the total budget to each channel. All percentages must \
sum to exactly 100. Use whole numbers only (e.g. 60, 30, 10 — not 33.33).

## Allocation principles
- The primary channel for the funnel stage receives the largest share.
- Secondary and supporting channels split the remainder in proportion to their \
expected contribution.
- Funnel stage guidance:
    Awareness: weight towards broad-reach CPM channels (display, video, social).
    Consideration: split between an intent channel and an engagement channel, \
with the intent channel leading.
    Conversion: weight heavily towards the highest-intent channel (e.g. Search, \
Shopping, Retargeting); supporting channels receive smaller shares.
- If only one channel is selected, assign it 100%.
- If two channels: the primary channel should receive at least 55%.
- If three channels: the primary should receive at least 45%, secondary at least 25%.

## Rules
1. Every channel in the provided list must appear in your allocations — no channel \
may be omitted or added.
2. Percentages must be whole numbers and must sum to exactly 100.
3. Justification must reference the channel's role relative to the other channels, \
not just describe the channel in isolation.

Always call the allocate_budget tool. Never reply in plain text.\
"""


def _build_user_message(
    inputs: CampaignInputs,
    goal: GoalAnalysis,
    channels: ChannelSelection,
) -> str:
    channel_list = "\n".join(
        f"  - {ch.name} ({ch.pricing_model.value})" for ch in channels.channels
    )
    return (
        f"Funnel stage: {goal.funnel_stage.value}\n"
        f"Total budget: {inputs.currency} {inputs.total_budget:,.2f}\n"
        f"Channels to allocate across:\n{channel_list}"
    )


def _normalise(
    raw: List[dict],
    total_budget: float,
) -> List[ChannelBudget]:
    """
    Guarantee C2: percentages sum to exactly 100.0 and absolute amounts sum to
    exactly total_budget, regardless of floating-point drift in the model's output.

    Strategy:
      1. Re-normalise raw percentages proportionally so they sum to 100.
      2. Round each to one decimal place; fix the last entry so the sum is
         exactly 100.0 (absorbing any rounding residual there).
      3. Derive absolute amounts the same way — accumulate and assign the
         remainder to the last entry.
    """
    raw_total = sum(a["percentage"] for a in raw)
    if raw_total == 0:
        raise ValueError("All channel percentages are zero — cannot allocate budget.")

    # Step 1: proportional normalisation
    normalised = [a["percentage"] / raw_total * 100 for a in raw]

    # Step 2: round to 1dp, fix last so sum == 100.0
    rounded_pcts: List[float] = [round(p, 1) for p in normalised]
    rounded_pcts[-1] = round(100.0 - sum(rounded_pcts[:-1]), 1)

    # Step 3: absolute amounts; remainder goes to last channel
    abs_amounts: List[float] = []
    running = 0.0
    for i, pct in enumerate(rounded_pcts):
        if i == len(rounded_pcts) - 1:
            abs_amounts.append(round(total_budget - running, 2))
        else:
            amt = round(total_budget * pct / 100, 2)
            running += amt
            abs_amounts.append(amt)

    return [
        ChannelBudget(
            channel_name=raw[i]["channel_name"],
            percentage=rounded_pcts[i],
            absolute_amount=abs_amounts[i],
            justification=raw[i]["justification"],
        )
        for i in range(len(raw))
    ]


def distribute_budget(
    inputs: CampaignInputs,
    goal: GoalAnalysis,
    channels: ChannelSelection,
) -> BudgetAllocation:
    """
    Step 3 — allocate total_budget across selected channels.

    The LLM decides the percentage split and justification; _normalise() enforces
    C2 (percentages sum to exactly 100%, absolute amounts sum to total_budget).
    """
    response = _client().messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        tools=[_ALLOCATE_TOOL],
        tool_choice={"type": "any"},
        messages=[
            {"role": "user", "content": _build_user_message(inputs, goal, channels)}
        ],
    )

    tool_use_block = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )
    if tool_use_block is None:
        raise RuntimeError("Model did not call the allocate_budget tool.")

    raw_allocations: List[dict] = tool_use_block.input["allocations"]

    # Validate the model returned an entry for every channel.
    # Canonical name matching — model may return slight variations
    canonical_names = {ch.name.lower(): ch.name for ch in channels.channels}
    normalised_raw = []
    for entry in raw_allocations:
        returned = entry["channel_name"].lower()
        # exact match
        if returned in canonical_names:
            normalised_raw.append({**entry, "channel_name": canonical_names[returned]})
        else:
            # substring match
            matched = next((c for c in canonical_names if c in returned or returned in c), None)
            if matched:
                normalised_raw.append({**entry, "channel_name": canonical_names[matched]})
            else:
                raise ValueError(f"Cannot match returned channel '{entry['channel_name']}' to any expected channel: {list(canonical_names.values())}")

    covered = {e["channel_name"].lower() for e in normalised_raw}
    missing = {ch.name.lower() for ch in channels.channels} - covered
    if missing:
        raise ValueError(f"Model omitted channels from allocation: {missing}")

    return BudgetAllocation(
        allocations=_normalise(normalised_raw, inputs.total_budget)
    )
