# Campaign Planning Agent

This is Group 1's project for the *Big Data & AI in Marketing* course (Option 2: Spec-Driven Development). It is an agent that takes the basic details of a marketing campaign and produces a finished campaign brief that can be handed straight to a media buyer.

The idea: a marketer enters a brand, product, audience, goal, and budget, and the agent works out which channels to use, how to split the budget, what KPI targets are realistic, and writes it all up as a short brief. The kind of planning that normally takes hours of manual work, done in under two minutes.

Group 1 consists of:
1. Tina Jannasch
2. Jia Yi Rachel Lee
3. Isha Shah
4. Shadi Hamarneh
5. Nuria Etemadi Gayo
6. Martí Solà Puig

## What it does

The agent runs six steps in a fixed order. Each step makes one decision and explains it:

1. **`analyze_goal`**: classifies the campaign as Awareness, Consideration, or Conversion, with a one-line reason.
2. **`select_channels`**: picks up to three channels and assigns a pricing model (CPC, CPM, or CPA) to each.
3. **`distribute_budget`**: splits the budget across the channels. Percentages are normalised in Python so they always sum to exactly 100%.
4. **`calculate_kpis`**: sets CTR, CPA, and ROAS targets based on the actual product price and budget — not generic benchmarks. ROAS is always calculated in Python as product price divided by CPA target.
5. **`generate_keywords`**: produces exactly five keywords in the target market language, matched to the funnel stage.
6. **`write_brief`**: pulls everything together into a 3 to 5 sentence campaign brief ready to hand to a media buyer without editing.

Constraints are enforced twice — once in the prompt sent to the model, and again in Python after the response. This means the output stays correct even if the model does not follow the instructions perfectly.

## Example used

To test the agent end to end, we used a fictional skincare brand called **GlowDrop**. The scenario is:

- **Brand:** GlowDrop, a B2C skincare brand
- **Product:** Morning Boost Serum, a Vitamin C face serum priced at GBP 45
- **Audience:** Women aged 22 to 38 in the UK and US, interested in skincare and wellness
- **Goal:** Increase first-time purchases
- **Budget:** GBP 5,000 per month
- **Existing channels:** Organic TikTok only (42k followers, reach declining)
- **Product type:** B2C

This is the exact scenario built into `test_run.py`, so running that file reproduces the GlowDrop example without entering anything manually. It is also the example documented in the report under Section 5.

One thing to note: the agent calls the model live each time it runs, so the exact outputs (channels, KPI figures, keywords) may differ slightly between runs. The logic and structure stay the same, but the figures are not fixed.

## Requirements

- **Python 3.9 or newer**
- **An Anthropic API key.** The agent calls the Anthropic API at every step and will not run without one. You can create a key at <https://console.anthropic.com>.

The only two dependencies are `anthropic` and `python-dotenv`, listed in `requirements.txt`.

## Setup

**1. Clone the repository**

```bash
git clone https://github.com/TinaJ050598/campaign-planning-agent.git
cd campaign-planning-agent
```

**2. (Recommended) create and activate a virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

**3. Install the dependencies**

```bash
pip install -r requirements.txt
```

**4. Add your Anthropic API key**

Create a file named `.env` in the project root with the following line:

```
ANTHROPIC_API_KEY=your_key_here
```

The agent loads this automatically. Alternatively, export the variable in your shell:

```bash
export ANTHROPIC_API_KEY=your_key_here
```

## Running the agent

**Quick demo (no input needed):**

```bash
python test_run.py
```

Runs the full pipeline on the GlowDrop example and prints all six step outputs. The easiest way to see the agent end to end without typing anything.

**Interactive mode:**

```bash
python main.py
```

Prompts you for each input one by one (marketing goal, brand description, audience, budget, product price, currency, target market language, existing channels, product type), then runs the pipeline and prints the result. Required fields are marked; optional ones can be skipped by pressing Enter.

## Project structure

```
campaign-planning-agent/
├── main.py                  # Interactive entry point
├── test_run.py              # One-shot demo run (GlowDrop scenario)
├── agent.py                 # Orchestrator, runs the 6 steps in order
├── steps/
│   ├── __init__.py
│   ├── analyze_goal.py      # Step 1: funnel stage classification
│   ├── select_channels.py   # Step 2: channel selection + pricing model
│   ├── distribute_budget.py # Step 3: budget allocation (100% normalised)
│   ├── calculate_kpis.py    # Step 4: CTR / CPA / ROAS targets
│   ├── generate_keywords.py # Step 5: exactly 5 keywords
│   └── write_brief.py       # Step 6: final campaign brief
├── models/
│   ├── __init__.py
│   ├── inputs.py            # CampaignInputs dataclass (9 input fields)
│   └── outputs.py           # Typed output objects for every step
├── validators/
│   ├── __init__.py
│   └── input_validator.py   # Checks required inputs before the pipeline runs
├── deliverables-docs/       # Project deliverables: report, presentation, demo recording
├── CLAUDE.md                # Agent specification (single source of truth)
├── REQUIREMENTS.md          # Structured requirements document
├── DESIGN.md                # Architecture, function descriptions, data flow
└── requirements.txt         # Python dependencies
```

The three specification documents (`CLAUDE.md`, `REQUIREMENTS.md`, `DESIGN.md`) were written before any code, following the spec-driven development approach.

## A few notes

- The `.env` file is not included in this repository so the API key is never committed. You will need to add your own key as described above.
- KPI targets are derived from the actual product price and budget, not from generic industry averages. ROAS is always calculated in Python as product price divided by CPA target.
- The agent evaluates each channel independently and has no access to live market data. Recommendations are based on general channel logic rather than current platform conditions. Limitations are discussed in detail in the report.

## Demo

The full demo recording can be found in the [`deliverables-docs`](deliverables-docs/) folder of this repository.