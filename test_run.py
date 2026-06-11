#!/usr/bin/env python3
"""
One-shot test run: GlowDrop, a B2C skincare brand running a conversion campaign.
Calls agent.run() directly — no interactive prompts.
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()

if not os.environ.get("ANTHROPIC_API_KEY"):
    sys.exit("ANTHROPIC_API_KEY not set.")

import agent
from models.inputs import CampaignInputs

inputs = CampaignInputs(
    marketing_goal=(
        "Increase first-time purchases of GlowDrop's Morning Boost Serum. "
        "The audience already knows the brand through its TikTok presence."
    ),
    brand_description=(
        "GlowDrop is a B2C skincare brand. Its product is the Morning Boost "
        "Serum, a Vitamin C face serum priced at 45 GBP. The USP is clean "
        "ingredients, dermatologist-tested, affordable luxury."
    ),
    target_audience=(
        "Women aged 22–38 in the UK and US who are interested in skincare "
        "and wellness. The brand has an existing organic TikTok following of "
        "42k, but reach is declining."
    ),
    total_budget=5000.00,         # per month
    product_price=45.00,          # price of the serum
    target_market_language="English",
    existing_channels=["Organic TikTok"],  # 42k followers, reach declining
    product_type="B2C",
)

HR  = "─" * 62
HRH = "═" * 62

def section(n, title):
    print(f"\n{HR}\n  Step {n} — {title}\n{HR}")

print(f"\n{HRH}")
print("  CAMPAIGN PLANNING AGENT — TEST RUN")
print(f"  Scenario: GlowDrop | B2C skincare | UK & US | 5,000 budget")
print(HRH)
print("\nRunning pipeline…")

try:
    result = agent.run(inputs)
except agent.ValidationError as e:
    sys.exit(f"Validation failed:\n{e}")
except agent.ClarificationNeeded as e:
    sys.exit(f"Clarification needed:\n  {e.question}")

# ── Step 1 ────────────────────────────────────────────────────
section(1, "Funnel Stage")
g = result.goal
print(f"  Stage : {g.funnel_stage.value}")
print(f"  Why   : {g.funnel_stage_rationale}")

# ── Step 2 ────────────────────────────────────────────────────
section(2, "Selected Channels")
for ch in result.channels.channels:
    print(f"  • {ch.name}  [{ch.pricing_model.value}]")
    print(f"    {ch.rationale}")

# ── Step 3 ────────────────────────────────────────────────────
section(3, "Budget Allocation")
for a in result.budget.allocations:
    print(f"  • {a.channel_name}: {a.absolute_amount:,.2f} ({a.percentage}%)")
    print(f"    {a.justification}")
pcts = [a.percentage for a in result.budget.allocations]
print(f"\n  Sum check: {sum(pcts):.1f}% (must be 100.0)")

# ── Step 4 ────────────────────────────────────────────────────
section(4, "KPI Targets")
for k in result.kpis.channel_kpis:
    print(f"  • {k.channel_name}")
    print(f"    CTR {k.ctr_target}%  |  CPA {k.cpa_target:.2f}  |  ROAS {k.roas_target:.2f}x")

# ── Step 5 ────────────────────────────────────────────────────
section(5, "Keywords")
for i, kw in enumerate(result.keywords.keywords, 1):
    print(f"  {i}. {kw}")
print(f"\n  Count check: {len(result.keywords.keywords)} (must be 5)")

# ── Step 6 ────────────────────────────────────────────────────
section(6, "Campaign Brief")
print()
brief_text = result.brief.campaign_brief
# wrap at ~70 chars
import textwrap
for line in textwrap.wrap(brief_text, width=70):
    print(f"  {line}")

print(f"\n{HRH}\n  ✓  Pipeline complete\n{HRH}\n")
