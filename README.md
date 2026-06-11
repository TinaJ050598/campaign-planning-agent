# Campaign Planning Agent

This is our project for the *Big Data & AI in Marketing* course (Option 2: Spec-Driven Development). It's an agent that takes the basic details of a marketing campaign and produces a finished campaign brief you could hand straight to a media buyer.

The idea: a marketer enters a brand, product, audience, goal, and budget, and the agent works out which channels to use, how to split the budget, what KPI targets are realistic, and writes it all up as a short brief. The kind of planning that normally takes a couple of hours, done in under two minutes.

This repository also includes our project presentation (`Presentation_Marketing_AI.pptx`, open in PowerPoint) and a short demo video of the agent running, further down in this README.

## What it does

The agent runs six steps in a fixed order, and each step makes one decision and explains it:

1. **`analyze_goal`**: works out the funnel stage (Awareness, Consideration, or Conversion).
2. **`select_channels`**: picks up to three channels and a pricing model for each.
3. **`distribute_budget`**: splits the budget across the channels. The percentages are normalised in Python so they always add up to exactly 100%.
4. **`calculate_kpis`**: sets CTR, CPA, and ROAS targets based on the actual product price and budget, not generic benchmarks.
5. **`generate_keywords`**: produces exactly five keywords in the target market's language.
6. **`write_brief`**: pulls everything together into a 3 to 5 sentence brief.

Each step is its own function. We enforce the constraints (max three channels, budget summing to 100%, exactly five keywords, and so on) twice: once in the prompt we send the model, and again in Python afterwards. That way the output stays correct even if the model doesn't follow the instructions perfectly.

## The example we used

To test the agent end to end, we used a fictional skincare brand called **GlowDrop**. The scenario is:

- **Brand:** GlowDrop, a B2C skincare brand
- **Product:** Morning Boost Serum, a Vitamin C face serum priced at GBP 45
- **Audience:** Women aged 22 to 38 in the UK and US, interested in skincare and wellness
- **Goal:** Increase first-time purchases
- **Budget:** GBP 5,000 per month
- **Existing channels:** Organic TikTok (42k followers, reach declining)
- **Product type:** B2C

This is the exact scenario built into `test_run.py`, so running that file reproduces the GlowDrop example without entering anything. It's also the example we walk through in our report. You're welcome to run it as is, or use `main.py` to enter your own brand and see how the agent responds to a different input.

One thing to note: the agent calls the model live each time it runs, so the exact numbers (CTR, CPA, etc.) may come out slightly differently on each run. The logic and structure stay the same, but the figures are not fixed.

## Requirements

- **Python 3.9 or newer**
- **An Anthropic API key.** The agent calls the Anthropic API at every step, so it won't run without one. You can create a key at <https://console.anthropic.com>.

The only two dependencies are `anthropic` and `python-dotenv` (listed in `requirements.txt`).

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

The agent loads this automatically. Alternatively, you can export the variable in your shell instead of using a `.env` file:

```bash
export ANTHROPIC_API_KEY=your_key_here
```

## Running the agent

**Quick demo (no input needed):**

```bash
python test_run.py
```

This runs the whole pipeline on the GlowDrop example described above (a B2C skincare brand running a conversion campaign for its Morning Boost Serum at GBP 45 with a GBP 5,000 monthly budget) and prints all six step outputs. It's the easiest way to see the agent run end to end without typing anything.

**Interactive mode:**

```bash
python main.py
```

This asks you for each input one by one (marketing goal, brand description, audience, budget, product price, currency, target market language, existing channels, product type), then runs the pipeline and prints the result. Required fields are marked; the optional ones can be skipped by pressing Enter.

## Project structure

```
campaign-planning-agent/
├── main.py                  # Interactive entry point
├── test_run.py              # One-shot demo run (GlowDrop scenario)
├── agent.py                 # Orchestrator, runs the 6 steps in order
├── steps/
│   ├── analyze_goal.py      # Step 1: funnel stage classification
│   ├── select_channels.py   # Step 2: channel selection + pricing model
│   ├── distribute_budget.py # Step 3: budget allocation (100% normalised)
│   ├── calculate_kpis.py    # Step 4: CTR / CPA / ROAS targets
│   ├── generate_keywords.py # Step 5: exactly 5 keywords
│   └── write_brief.py       # Step 6: final campaign brief
├── models/
│   ├── inputs.py            # CampaignInputs dataclass (8 input fields)
│   └── outputs.py           # Typed output objects for every step
├── validators/
│   └── input_validator.py   # Checks required inputs before the pipeline runs
├── CLAUDE.md                # Agent specification (single source of truth)
├── REQUIREMENTS.md          # Structured requirements document
├── DESIGN.md                # Architecture, function descriptions, data flow
└── requirements.txt         # Python dependencies
```

The three specification documents (`CLAUDE.md`, `REQUIREMENTS.md`, `DESIGN.md`) were written before any code, following the spec-driven development approach.

## A few notes

- The `.env` file is **not** in this repository on purpose, so our API key never gets committed. You'll need to add your own key as described above.
- KPI targets come from the inputs (product price and budget), not from generic industry averages. ROAS is always calculated in Python as product price divided by CPA target, so the numbers stay consistent with each other.
- The agent looks at each channel on its own and has no access to live market data, so the recommendations are based on general channel logic rather than current conditions. We go into these limitations in more detail in the report.
## Demo




https://github.com/user-attachments/assets/5c519363-6d70-4e0f-802d-74fce33dac4c

