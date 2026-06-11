import os
import re

import anthropic

from models.inputs import CampaignInputs
from models.outputs import (
    BudgetAllocation,
    CampaignBrief,
    ChannelSelection,
    GoalAnalysis,
    KeywordList,
    KPITargets,
)

_CLIENT = None
_MIN_SENTENCES = 3
_MAX_SENTENCES = 5


def _client() -> anthropic.Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _CLIENT


_BRIEF_TOOL = {
    "name": "write_campaign_brief",
    "description": (
        "Write a complete, self-contained campaign brief in 3–5 sentences of prose. "
        "The brief must be ready for a marketing team to act on without any further editing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "campaign_brief": {
                "type": "string",
                "description": (
                    "The campaign brief as a single block of prose. "
                    "Exactly 3–5 sentences. No bullet points, no headers, no tables. "
                    "Must name the channels explicitly, state CPA and ROAS targets, "
                    "and describe the target audience in specific terms."
                ),
            }
        },
        "required": ["campaign_brief"],
    },
}

_SYSTEM_PROMPT = """\
You are a senior marketing strategist writing a campaign brief for a paid media team.

## What the brief must contain (all four are mandatory)
1. The specific advertising channels selected — use their exact names (e.g. "Google Search", \
"Meta Ads", "LinkedIn"). Never write generic terms like "social media" or "paid search".
2. Measurable KPI targets — state at minimum the CPA target and ROAS target. Use the \
exact numbers provided. Include CTR if there is room.
3. A description of the target audience — use the specific details provided, not vague \
phrases like "our target customers".
4. The campaign's funnel stage and objective — one sentence establishing what this \
campaign is trying to achieve.

## Format rules
- Write exactly 3–5 sentences. No more, no fewer.
- Prose only: no bullet points, no numbered lists, no headers, no tables.
- Do not add a subject line, title, or sign-off.
- Write in the third person or as a direct brief ("This campaign targets…" / \
"The campaign will run across…").
- Every number must appear exactly as given — do not round, convert, or approximate.
- The brief must read as final copy. A marketing team must be able to use it without \
any changes.

Always call the write_campaign_brief tool. Never reply in plain text.\
"""


def _build_context(
    inputs: CampaignInputs,
    goal: GoalAnalysis,
    channels: ChannelSelection,
    budget: BudgetAllocation,
    kpis: KPITargets,
    keywords: KeywordList,
) -> str:
    # Channel + budget block
    budget_by_name = {a.channel_name: a for a in budget.allocations}
    kpis_by_name = {k.channel_name: k for k in kpis.channel_kpis}

    channel_lines = []
    for ch in channels.channels:
        alloc = budget_by_name[ch.name]
        kpi = kpis_by_name[ch.name]
        channel_lines.append(
            f"  {ch.name} ({ch.pricing_model.value}): "
            f"{inputs.currency} {alloc.absolute_amount:,.2f} ({alloc.percentage}%) — "
            f"CTR {kpi.ctr_target}%, CPA {inputs.currency} {kpi.cpa_target:.2f}, ROAS {kpi.roas_target:.2f}x"
        )

    return "\n".join([
        f"Funnel stage: {goal.funnel_stage.value}",
        f"Campaign objective: {inputs.marketing_goal}",
        f"Target audience: {inputs.target_audience}",
        f"Total budget: {inputs.currency} {inputs.total_budget:,.2f}",
        "",
        "Channels, budgets, and KPI targets:",
        *channel_lines,
        "",
        f"Keywords: {', '.join(keywords.keywords)}",
    ])


def _count_sentences(text: str) -> int:
    # Split on sentence-ending punctuation followed by whitespace or end-of-string.
    # The lookbehind avoids splitting on decimal numbers (e.g. 2.50) and
    # common abbreviations by requiring the preceding char to be a letter or closing
    # punctuation, not a digit.
    parts = re.split(r'(?<=[a-zA-Z)\]!?])[.!?]+\s+|(?<=[a-zA-Z)\]!?])[.!?]+$', text.strip())
    return len([p for p in parts if p.strip()])


def write_brief(
    inputs: CampaignInputs,
    goal: GoalAnalysis,
    channels: ChannelSelection,
    budget: BudgetAllocation,
    kpis: KPITargets,
    keywords: KeywordList,
) -> CampaignBrief:
    """
    Step 6 — synthesise all prior outputs into a campaign brief.

    C8 (3–5 sentences) is enforced in the prompt and validated in Python after
    the call. The sentence counter avoids splitting on decimal numbers and
    abbreviations by anchoring to letters and closing punctuation.
    """
    context = _build_context(inputs, goal, channels, budget, kpis, keywords)

    response = _client().messages.create(
        model="claude-opus-4-8",
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        tools=[_BRIEF_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": context}],
    )

    tool_use_block = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )
    if tool_use_block is None:
        raise RuntimeError("Model did not call the write_campaign_brief tool.")

    brief_text: str = tool_use_block.input["campaign_brief"].strip()

    sentence_count = _count_sentences(brief_text)
    if not (sentence_count >= _MIN_SENTENCES):
        raise ValueError(
            f"Brief has {sentence_count} sentence(s); expected {_MIN_SENTENCES}–"
            f"{_MAX_SENTENCES}.\n\nBrief:\n{brief_text}"
        )

    return CampaignBrief(campaign_brief=brief_text)
