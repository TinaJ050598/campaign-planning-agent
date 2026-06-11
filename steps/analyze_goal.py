import os
import anthropic
from models.inputs import CampaignInputs
from models.outputs import FunnelStage, GoalAnalysis

_CLIENT = None


def _client() -> anthropic.Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _CLIENT


# Tool schema handed to Claude so the response is always structured.
_CLASSIFY_TOOL = {
    "name": "classify_funnel_stage",
    "description": (
        "Classify a marketing goal into exactly one funnel stage, or surface a "
        "clarifying question when the goal is too ambiguous to classify."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "funnel_stage": {
                "type": "string",
                "enum": ["Awareness", "Consideration", "Conversion"],
                "description": (
                    "The funnel stage that best matches the marketing goal. "
                    "Omit this field only when clarifying_question is set."
                ),
            },
            "rationale": {
                "type": "string",
                "description": (
                    "One sentence explaining why this funnel stage was chosen, "
                    "citing specific evidence from the inputs. "
                    "Omit this field only when clarifying_question is set."
                ),
            },
            "clarifying_question": {
                "type": "string",
                "description": (
                    "A single question to ask the user when the marketing goal is "
                    "too ambiguous to classify. Set this instead of funnel_stage "
                    "and rationale."
                ),
            },
        },
        "required": [],
    },
}

_SYSTEM_PROMPT = """\
You are a senior marketing strategist. Your task is to classify a marketing goal \
into exactly one of three funnel stages:

- Awareness: the brand is new or largely unknown, and the primary objective is \
reach — getting the brand in front of as many relevant people as possible.
- Consideration: the target audience already knows the brand, and the goal is \
engagement, education, or comparison — moving prospects closer to a decision.
- Conversion: the goal is a direct, measurable action — a purchase, signup, \
free-trial start, or similar transaction.

Classification rules:
1. Read both the marketing goal AND the brand description together. Brand context \
can override what the goal text alone suggests (e.g. "grow our audience" from a \
brand-new company → Awareness, not Consideration).
2. Choose the single best-fit stage. Do not hedge with multiple stages.
3. Write one rationale sentence that cites specific evidence from the inputs.
4. If and only if the marketing goal is genuinely ambiguous — meaning you cannot \
distinguish between two or more stages with reasonable confidence — set \
clarifying_question to a single focused question that would resolve the ambiguity. \
Do not set funnel_stage or rationale in that case.

Always call the classify_funnel_stage tool. Never reply in plain text.\
"""


def analyze_goal(inputs: CampaignInputs) -> GoalAnalysis:
    """
    Step 1 — classify the marketing goal into a funnel stage.

    Returns a GoalAnalysis with funnel_stage + rationale on success, or with
    clarifying_question set (and funnel_stage=None) when the goal is ambiguous (E2).
    """
    user_message = (
        f"Marketing goal: {inputs.marketing_goal}\n"
        f"Brand description: {inputs.brand_description}"
    )

    response = _client().messages.create(
        model="claude-opus-4-8",
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        tools=[_CLASSIFY_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": user_message}],
    )

    tool_use_block = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )
    if tool_use_block is None:
        raise RuntimeError("Model did not call the classification tool.")

    result: dict = tool_use_block.input

    if "clarifying_question" in result:
        return GoalAnalysis(
            funnel_stage=None,
            funnel_stage_rationale=None,
            clarifying_question=result["clarifying_question"],
        )

    return GoalAnalysis(
        funnel_stage=FunnelStage(result["funnel_stage"]),
        funnel_stage_rationale=result["rationale"],
    )
