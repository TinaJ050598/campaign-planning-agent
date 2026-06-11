#!/usr/bin/env python3
"""
One-shot test run: a B2C project management SaaS launching in the UK.
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
        "Drive free-trial signups for a new project management tool. "
        "The brand is not yet known in the UK market."
    ),
    brand_description=(
        "Flowdesk is a B2C project management SaaS launched in 2024. "
        "It targets freelancers and small creative teams. "
        "The product is new with no existing UK customer base."
    ),
    target_audience=(
        "UK-based freelancers and small creative teams (2–10 people), "
        "aged 25–40, who currently use spreadsheets or Notion and are "
        "looking for a simpler task and project tracking tool."
    ),
    total_budget=3000.00,
    product_price=19.00,          # monthly subscription price
    target_market_language="English",
    existing_channels=[],         # brand new — no prior channels
    product_type="B2C",
)

HR  = "─" * 62
HRH = "═" * 62

def section(n, title):
    print(f"\n{HR}\n  Step {n} — {title}\n{HR}")

print(f"\n{HRH}")
print("  CAMPAIGN PLANNING AGENT — TEST RUN")
print(f"  Scenario: Flowdesk | B2C SaaS | UK | 3,000 budget")
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
