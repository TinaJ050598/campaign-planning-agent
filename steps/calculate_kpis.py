import os
from typing import Dict, List

import anthropic

from models.inputs import CampaignInputs
from models.outputs import (
    BudgetAllocation,
    ChannelKPIs,
    ChannelSelection,
    GoalAnalysis,
    KPITargets,
)

_CLIENT = None


def _client() -> anthropic.Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _CLIENT


_KPI_TOOL = {
    "name": "set_kpi_targets",
    "description": (
        "Set CTR and CPA targets for each channel, derived from the product price, "
        "budget allocation, funnel stage, and channel type. "
        "Do not provide ROAS — that is computed separately."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "channel_kpis": {
                "type": "array",
                "description": "One entry per channel.",
                "items": {
                    "type": "object",
                    "properties": {
                        "channel_name": {
                            "type": "string",
                            "description": "Must exactly match one of the provided channel names.",
                        },
                        "ctr_target": {
                            "type": "number",
                            "minimum": 0.01,
                            "description": (
                                "Click-through rate target as a percentage. "
                                "E.g. 3.5 means 3.5%. Must be specific to this channel "
                                "type and funnel stage — not a generic industry average."
                            ),
                        },
                        "cpa_target": {
                            "type": "number",
                            "minimum": 0.01,
                            "description": (
                                "Target cost per acquisition in the same currency as product_price. "
                                "Must be derived as a fraction of product_price, "
                                "adjusted for funnel stage and channel efficiency. "
                                "Must be less than product_price."
                            ),
                        },
                    },
                    "required": ["channel_name", "ctr_target", "cpa_target"],
                },
            }
        },
        "required": ["channel_kpis"],
    },
}

_SYSTEM_PROMPT = """\
You are a senior performance marketing analyst. Set realistic KPI targets for each \
advertising channel based solely on the numbers provided — never use generic industry \
benchmarks.

## What you must derive each KPI from

CTR target:
- Base it on channel type and funnel stage.
- Conversion-stage search ads: typically 3–8%.
- Conversion-stage social (Meta, LinkedIn): typically 0.8–2%.
- Consideration-stage search: typically 2–5%.
- Consideration-stage social: typically 0.5–1.5%.
- Awareness-stage display / video / social: typically 0.05–0.5%.
- Retargeting: typically 1–4%.
- Pick a specific number within the range that reflects this audience and product — \
do not default to the midpoint.

CPA target:
- Derive it as a fraction of product_price. The fraction depends on funnel stage and \
channel efficiency:
    Conversion stage, high-intent channel (Search, Shopping, Retargeting): 15–25% of \
product price.
    Conversion stage, social channel: 20–35% of product price.
    Consideration stage: 25–45% of product price (fewer direct conversions expected).
    Awareness stage: 40–60% of product price (conversion is indirect and delayed).
- CPA must always be less than product_price. If product_price is very low (< 15), \
use a tighter fraction (10–20%) so the economics remain viable.
- Adjust upward (worse efficiency) if the channel's absolute budget is very low \
(< 200), because low spend prevents algorithm optimisation.

Low-budget adjustment (E3):
- If total_budget is very low (under 10x the product price), increase all CPA targets by 20–30% above the normal \
fraction, and reduce CTR targets by 20–30%, to reflect reduced scale and algorithm \
learning constraints.

Rules:
1. Every channel in the provided list must appear in your output.
2. Use the exact channel names as given.
3. CPA must be less than product_price for every channel.
4. Do not invent a ROAS value — it is not part of this tool.

Always call the set_kpi_targets tool. Never reply in plain text.\
"""


def _build_user_message(
    inputs: CampaignInputs,
    goal: GoalAnalysis,
    channels: ChannelSelection,
    budget: BudgetAllocation,
) -> str:
    # Build a lookup from channel name → absolute_amount for easy merging.
    budget_by_name: Dict[str, float] = {
        alloc.channel_name: alloc.absolute_amount for alloc in budget.allocations
    }

    channel_lines = []
    for ch in channels.channels:
        alloc = budget_by_name.get(ch.name, 0.0)
        channel_lines.append(
            f"  - {ch.name} | pricing model: {ch.pricing_model.value} "
            f"| budget: {inputs.currency} {alloc:,.2f}"
        )

    return (
        f"Funnel stage: {goal.funnel_stage.value}\n"
        f"Product price: {inputs.currency} {inputs.product_price:,.2f}\n"
        f"Total budget: {inputs.currency} {inputs.total_budget:,.2f}\n"
        f"Target audience: {inputs.target_audience}\n"
        f"Channels:\n" + "\n".join(channel_lines)
    )


def _compute_roas(product_price: float, cpa_target: float) -> float:
    # ROAS = expected revenue / spend = product_price / cpa_target
    # (one conversion at product_price acquired for cpa_target spend)
    return round(product_price / cpa_target, 2)


def calculate_kpis(
    inputs: CampaignInputs,
    goal: GoalAnalysis,
    channels: ChannelSelection,
    budget: BudgetAllocation,
) -> KPITargets:
    """
    Step 4 — compute per-channel KPI targets.

    The LLM derives ctr_target and cpa_target from product_price, funnel stage,
    channel type, and budget size (C6, E3). roas_target is computed deterministically
    in Python as product_price / cpa_target to guarantee formula consistency.
    """
    response = _client().messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        tools=[_KPI_TOOL],
        tool_choice={"type": "any"},
        messages=[
            {
                "role": "user",
                "content": _build_user_message(inputs, goal, channels, budget),
            }
        ],
    )

    tool_use_block = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )
    if tool_use_block is None:
        raise RuntimeError("Model did not call the set_kpi_targets tool.")

    raw: List[dict] = tool_use_block.input["channel_kpis"]

    # Guard: every channel must be present.
    provided = {entry["channel_name"].lower() for entry in raw}
    expected = {ch.name.lower() for ch in channels.channels}
    missing = expected - provided
    if missing:
        raise ValueError(f"Model omitted channels from KPI output: {missing}")

    kpis = []
    for entry in raw:
        cpa = entry["cpa_target"]
        if cpa >= inputs.product_price:
            raise ValueError(
                f"CPA target {cpa} for '{entry['channel_name']}' equals or exceeds "
                f"product price {inputs.product_price}. Check model output."
            )
        kpis.append(
            ChannelKPIs(
                channel_name=entry["channel_name"],
                ctr_target=round(entry["ctr_target"], 2),
                cpa_target=round(cpa, 2),
                roas_target=_compute_roas(inputs.product_price, cpa),
            )
        )

    return KPITargets(channel_kpis=kpis)
