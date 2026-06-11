from dataclasses import dataclass
from typing import List

from models.inputs import CampaignInputs
from models.outputs import (
    BudgetAllocation,
    CampaignBrief,
    ChannelSelection,
    GoalAnalysis,
    KeywordList,
    KPITargets,
)
from steps.analyze_goal import analyze_goal
from steps.calculate_kpis import calculate_kpis
from steps.distribute_budget import distribute_budget
from steps.generate_keywords import generate_keywords
from steps.select_channels import select_channels
from steps.write_brief import write_brief
from validators.input_validator import validate_inputs


class ValidationError(Exception):
    """Raised when one or more required inputs are missing or invalid (C3, E4)."""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(f"  • {e}" for e in errors))


class ClarificationNeeded(Exception):
    """Raised when the marketing goal is too ambiguous to classify (E2)."""

    def __init__(self, question: str) -> None:
        self.question = question
        super().__init__(question)


@dataclass
class PipelineResult:
    goal: GoalAnalysis
    channels: ChannelSelection
    budget: BudgetAllocation
    kpis: KPITargets
    keywords: KeywordList
    brief: CampaignBrief


def run(inputs: CampaignInputs) -> PipelineResult:
    """
    Execute the full 6-step campaign planning pipeline in order (C9).

    Raises:
        ValidationError       — one or more inputs are missing or invalid (C3, E4).
        ClarificationNeeded   — marketing_goal is ambiguous; caller should surface
                                the question to the user and rerun with a clearer goal (E2).
        ValueError            — a step's post-processing constraint was violated
                                (e.g. CPA >= product_price, keyword count != 5).
        RuntimeError          — the model failed to call a required tool.
    """
    errors = validate_inputs(inputs)
    if errors:
        raise ValidationError(errors)

    # Step 1 — classify funnel stage
    goal = analyze_goal(inputs)
    if goal.is_ambiguous:
        raise ClarificationNeeded(goal.clarifying_question)

    # Step 2 — select channels (depends on Step 1)
    channels = select_channels(inputs, goal)

    # Step 3 — distribute budget (depends on Steps 1, 2)
    budget = distribute_budget(inputs, goal, channels)

    # Step 4 — calculate KPIs (depends on Steps 1, 2, 3)
    kpis = calculate_kpis(inputs, goal, channels, budget)

    # Step 5 — generate keywords (depends on Step 1)
    keywords = generate_keywords(inputs, goal)

    # Step 6 — write brief (depends on Steps 1–5)
    brief = write_brief(inputs, goal, channels, budget, kpis, keywords)

    return PipelineResult(
        goal=goal,
        channels=channels,
        budget=budget,
        kpis=kpis,
        keywords=keywords,
        brief=brief,
    )
