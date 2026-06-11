#!/usr/bin/env python3
import os
import sys
from typing import List, Optional

from dotenv import load_dotenv

import agent
from agent import ClarificationNeeded, ValidationError
from models.inputs import CampaignInputs
from models.outputs import BudgetAllocation, ChannelSelection, KPITargets, KeywordList

load_dotenv()


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

def _prompt(label: str, required: bool = True) -> str:
    marker = "" if required else " (optional, press Enter to skip)"
    while True:
        value = input(f"  {label}{marker}: ").strip()
        if value:
            return value
        if not required:
            return ""
        print(f"    ✗ This field is required. Please enter a value.")


def _prompt_float(label: str) -> float:
    while True:
        raw = input(f"  {label}: ").strip()
        try:
            value = float(raw.replace(",", "").replace("£", "").replace("€", "").replace("$", ""))
            if value <= 0:
                print("    ✗ Must be greater than zero.")
                continue
            return value
        except ValueError:
            print("    ✗ Please enter a valid number (e.g. 2500 or 1999.99).")


def _prompt_list(label: str) -> List[str]:
    raw = input(f"  {label} (optional, comma-separated, press Enter to skip): ").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _prompt_product_type() -> Optional[str]:
    while True:
        raw = input("  Product type (B2B / B2C, press Enter to skip): ").strip()
        if not raw:
            return None
        upper = raw.upper()
        if upper in ("B2B", "B2C"):
            return upper
        print("    ✗ Enter 'B2B', 'B2C', or press Enter to skip.")


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _hr(char: str = "─", width: int = 60) -> str:
    return char * width


def _print_step(number: int, title: str) -> None:
    print(f"\n{_hr()}")
    print(f"  Step {number} — {title}")
    print(_hr())


def _print_channels(channels: ChannelSelection) -> None:
    for ch in channels.channels:
        print(f"  • {ch.name} [{ch.pricing_model.value}]")
        print(f"    {ch.rationale}")


def _print_budget(budget: BudgetAllocation, currency: str = "") -> None:
    for alloc in budget.allocations:
        print(
            f"  • {alloc.channel_name}: "
            f"{currency} {alloc.absolute_amount:,.2f} ({alloc.percentage}%)"
        )
        print(f"    {alloc.justification}")


def _print_kpis(kpis: KPITargets, currency: str = "") -> None:
    for k in kpis.channel_kpis:
        print(f"  • {k.channel_name}")
        print(f"    CTR {k.ctr_target}%  |  CPA {currency} {k.cpa_target:.2f}  |  ROAS {k.roas_target:.2f}x")


def _print_keywords(keywords: KeywordList) -> None:
    for i, kw in enumerate(keywords.keywords, 1):
        print(f"  {i}. {kw}")


def _print_result(result: agent.PipelineResult, currency: str = "") -> None:
    _print_step(1, "Funnel Stage")
    print(f"  Stage : {result.goal.funnel_stage.value}")
    print(f"  Why   : {result.goal.funnel_stage_rationale}")

    _print_step(2, "Selected Channels")
    _print_channels(result.channels)

    _print_step(3, "Budget Allocation")
    _print_budget(result.budget, currency)

    _print_step(4, "KPI Targets")
    _print_kpis(result.kpis, currency)

    _print_step(5, "Keywords")
    _print_keywords(result.keywords)

    _print_step(6, "Campaign Brief")
    print()
    print(f"  {result.brief.campaign_brief}")
    print()
    print(_hr("═"))


# ---------------------------------------------------------------------------
# Input collection
# ---------------------------------------------------------------------------

def _collect_inputs() -> CampaignInputs:
    print("\n" + _hr("═"))
    print("  Campaign Planning Agent")
    print(_hr("═"))
    print("\nEnter the details below. Required fields are marked accordingly.\n")

    marketing_goal = _prompt("Marketing goal")
    brand_description = _prompt("Brand description")
    target_audience = _prompt("Target audience")
    total_budget = _prompt_float("Total budget")
    product_price = _prompt_float("Product / service price")
    currency = _prompt("Currency (e.g. GBP, EUR, USD)", required=False) or "GBP"
    target_market_language = _prompt("Target market language (e.g. English, French)")
    existing_channels = _prompt_list("Existing channels")
    product_type = _prompt_product_type()

    return CampaignInputs(
        marketing_goal=marketing_goal,
        brand_description=brand_description,
        target_audience=target_audience,
        total_budget=total_budget,
        product_price=product_price,
        target_market_language=target_market_language,
        existing_channels=existing_channels,
        product_type=product_type,
        currency=currency,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "Error: ANTHROPIC_API_KEY is not set. "
            "Add it to a .env file or export it in your shell.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        inputs = _collect_inputs()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)

    print("\nRunning pipeline…\n")

    try:
        result = agent.run(inputs)
    except ValidationError as exc:
        print("\nInput validation failed:\n")
        for err in exc.errors:
            print(f"  • {err}")
        sys.exit(1)
    except ClarificationNeeded as exc:
        print("\nThe marketing goal is ambiguous. Please answer this question and run again:\n")
        print(f"  {exc.question}")
        sys.exit(0)
    except (ValueError, RuntimeError) as exc:
        print(f"\nPipeline error: {exc}", file=sys.stderr)
        sys.exit(1)

    _print_result(result, inputs.currency)


if __name__ == "__main__":
    main()
