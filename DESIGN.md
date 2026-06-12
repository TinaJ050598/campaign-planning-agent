# Campaign Planning Agent — Design Document

---

## 1. File Structure

```
campaign-agent/
├── main.py                  # Entry point; collects inputs, runs the pipeline, prints output
├── agent.py                 # Orchestrator; calls each step in order, passes state between them
├── steps/
│   ├── __init__.py
│   ├── analyze_goal.py      # Step 1 — funnel stage classification
│   ├── select_channels.py   # Step 2 — channel selection and pricing model assignment
│   ├── distribute_budget.py # Step 3 — budget allocation across channels
│   ├── calculate_kpis.py    # Step 4 — per-channel KPI target calculation
│   ├── generate_keywords.py # Step 5 — high-intent keyword generation
│   └── write_brief.py       # Step 6 — campaign brief synthesis
├── models/
│   ├── __init__.py
│   ├── inputs.py            # CampaignInputs dataclass — all 9 input fields
│   └── outputs.py           # Output dataclasses for each step (FunnelStage, Channel, etc.)
├── validators/
│   ├── __init__.py
│   └── input_validator.py   # Checks required fields, detects missing/ambiguous inputs
├── deliverables-docs/       # Project deliverables: report, presentation, demo recording
├── CLAUDE.md
├── REQUIREMENTS.md
├── DESIGN.md
├── README.md
└── requirements.txt         # Python dependencies (anthropic SDK, etc.)
```

### Rationale for this structure

- `steps/` isolates each of the 6 processing functions so they can be developed, tested, and replaced independently.
- `models/` defines shared data contracts. Every step reads from and writes to typed objects, not raw dicts, preventing silent data mismatches across steps.
- `validators/` is separated from steps because input validation (C3, E2, E4) is a cross-cutting concern that runs before the pipeline starts, not inside individual steps.
- `agent.py` owns the pipeline order (C9) in one place — if order ever changes, only one file needs updating.

---

## 2. Function Descriptions

### 2.1 `analyze_goal(inputs: CampaignInputs) → GoalAnalysis`

**Purpose:** Classify the campaign's marketing goal into exactly one of three funnel stages: Awareness, Consideration, or Conversion.

**Inputs consumed:** `marketing_goal`, `brand_description`

**Decision logic:**
- Reads both fields together; brand context (new vs. established) may override what the goal text alone suggests.
- Applies a three-way classification:
  - Awareness — brand is new/unknown or goal centres on reach and visibility.
  - Consideration — brand is known; goal is engagement, comparison, or education.
  - Conversion — goal explicitly targets a transaction: purchase, signup, download, trial.
- If `marketing_goal` is ambiguous (E2), the function does not classify; instead it returns a single clarifying question and halts the pipeline.

**Output:** `GoalAnalysis` containing `funnel_stage` (enum) and `funnel_stage_rationale` (string).

---

### 2.2 `select_channels(inputs: CampaignInputs, goal: GoalAnalysis) → ChannelSelection`

**Purpose:** Select 1–3 advertising channels appropriate for the funnel stage and target audience.

**Inputs consumed:** `funnel_stage` (from Step 1), `target_audience`, `total_budget`, `product_type`, `existing_channels`

**Decision logic:**
- Uses funnel stage to narrow the candidate channel pool (e.g. CPM-heavy channels suit Awareness; intent-based channels suit Conversion).
- Uses `target_audience` to match channels to where the audience actually spends time.
- Applies constraint rules before finalising the list:
  - C1: hard cap at 3 channels.
  - C4: if product_type is B2B and both LinkedIn and TikTok are candidates, LinkedIn wins.
  - C5/E5: if `total_budget` very low, cap at 2 channels.
- If `existing_channels` is absent or empty (E1), selects channels entirely from scratch with no prior-usage bias.
- Assigns each selected channel a pricing model (CPC, CPM, or CPA) based on how that channel is conventionally purchased.
- Writes one sentence per channel justifying fit for the specific audience described.

**Output:** `ChannelSelection` containing a list of `Channel` objects, each with `name`, `pricing_model`, and `rationale`.

---

### 2.3 `distribute_budget(inputs: CampaignInputs, channels: ChannelSelection) → BudgetAllocation`

**Purpose:** Allocate the total campaign budget across the selected channels with explicit percentages and absolute amounts.

**Inputs consumed:** `total_budget` (from inputs), `channels` list (from Step 2), `funnel_stage` (from Step 1)

**Decision logic:**
- Ranks channels by priority within the funnel stage (primary channel receives the largest share).
- Assigns a percentage to each channel; percentages must sum to exactly 100% (C2).
- Derives `absolute_amount = total_budget × (percentage / 100)` for each channel — no rounding that would break the 100% invariant.
- Writes a justification for each allocation, explaining why that channel received its share relative to the others.

**Output:** `BudgetAllocation` containing a list of `ChannelBudget` objects, each with `channel_name`, `percentage`, `absolute_amount`, and `justification`.

---

### 2.4 `calculate_kpis(inputs: CampaignInputs, budget: BudgetAllocation) → KPITargets`

**Purpose:** Produce realistic, input-derived performance targets for each channel. No generic benchmarks permitted (C6).

**Inputs consumed:** `product_price`, `total_budget` (from inputs), `absolute_amount` per channel (from Step 3), `funnel_stage` (from Step 1), `pricing_model` per channel (from Step 2)

**Decision logic:**
- **CTR target** — estimated per channel using the channel type and funnel stage as qualitative modifiers (e.g. Conversion-stage search ads carry higher expected CTR than Awareness-stage display).
- **CPA target** — derived from `product_price`. A commercially acceptable CPA is a fraction of product price (e.g. for a 200 product, a CPA of 40–50 may be reasonable). The exact fraction is determined by the funnel stage and channel efficiency.
- **ROAS target** — derived as `(channel_absolute_amount / cpa_target) × product_price / channel_absolute_amount`, i.e. expected revenue divided by spend. This anchors ROAS to the actual budget and price rather than an assumed industry average.
- If `total_budget` is very low (E3), KPI targets are scaled down accordingly rather than left at full-budget levels.
- All three KPIs are computed per channel independently.

**Output:** `KPITargets` containing a list of `ChannelKPIs` objects, each with `channel_name`, `ctr_target`, `cpa_target`, and `roas_target`.

---

### 2.5 `generate_keywords(inputs: CampaignInputs, goal: GoalAnalysis) → KeywordList`

**Purpose:** Generate exactly 5 high-intent keywords aligned to the funnel stage and written in the target market's language.

**Inputs consumed:** `funnel_stage` (from Step 1), `target_market_language`, `marketing_goal`, `brand_description`, `target_audience`

**Decision logic:**
- Intent level is dictated by `funnel_stage`:
  - Awareness → broad, informational terms (what is X, X explained, X for beginners).
  - Consideration → comparative or category terms (best X, X vs Y, X reviews).
  - Conversion → transactional terms (buy X, X pricing, X free trial, X sign up).
- All 5 keywords must be in `target_market_language` — not translated from English if the market language differs.
- Keywords must reflect the specific product/brand context, not generic placeholders.
- Exactly 5 are returned (C7); the function must not produce 4 or 6.

**Output:** `KeywordList` containing a list of exactly 5 strings.

---

### 2.6 `write_brief(inputs: CampaignInputs, goal: GoalAnalysis, channels: ChannelSelection, budget: BudgetAllocation, kpis: KPITargets, keywords: KeywordList) → CampaignBrief`

**Purpose:** Synthesise all prior step outputs into a single, self-contained campaign brief ready for a marketing team.

**Inputs consumed:** All outputs from Steps 1–5, plus `target_audience` from original inputs.

**Decision logic:**
- Combines outputs into coherent prose — no bullet lists, no tables; running sentences only.
- Must name the selected channels explicitly (not "social media" or "paid search" generically).
- Must state at least the headline KPI targets (CPA and ROAS) so the brief sets measurable expectations.
- Must describe the target audience in specific terms sourced from the input.
- Length is 3–5 sentences (C8). If a draft exceeds 5 sentences, it is condensed; if under 3, it is expanded.
- Output requires no further editing — it is the final deliverable of the pipeline.

**Output:** `CampaignBrief` containing the `campaign_brief` prose string.

---

## 3. Data Flow Between Steps

```
CampaignInputs (all 9 fields)
        │
        ▼
[ input_validator.py ]
  - Check required fields (C3, E4)
  - Detect ambiguous goal (E2) → halt and ask clarifying question
        │
        ▼
Step 1: analyze_goal(inputs)
  Reads:  marketing_goal, brand_description
  Writes: GoalAnalysis { funnel_stage, funnel_stage_rationale }
        │
        ▼
Step 2: select_channels(inputs, goal)
  Reads:  funnel_stage ← Step 1
          target_audience, total_budget, product_type, existing_channels ← inputs
  Writes: ChannelSelection { channels[] }
        │
        ▼
Step 3: distribute_budget(inputs, channels)
  Reads:  channels[] ← Step 2
          total_budget, funnel_stage ← inputs / Step 1
  Writes: BudgetAllocation { channel_budgets[] }
        │
        ▼
Step 4: calculate_kpis(inputs, budget)
  Reads:  channel_budgets[] ← Step 3
          product_price, total_budget ← inputs
          funnel_stage ← Step 1
          pricing_model per channel ← Step 2
  Writes: KPITargets { channel_kpis[] }
        │
        ▼
Step 5: generate_keywords(inputs, goal)
  Reads:  funnel_stage ← Step 1
          target_market_language, marketing_goal,
          brand_description, target_audience ← inputs
  Writes: KeywordList { keywords[5] }
        │
        ▼
Step 6: write_brief(inputs, goal, channels, budget, kpis, keywords)
  Reads:  ALL prior step outputs
          target_audience ← inputs
  Writes: CampaignBrief { campaign_brief }
        │
        ▼
  Final Output to user
```

### Key data dependencies

| Step | Hard dependencies (must complete first) |
|---|---|
| Step 2 | Step 1 (`funnel_stage`) |
| Step 3 | Step 2 (`channels` list) |
| Step 4 | Step 2 (`pricing_model` per channel), Step 3 (`absolute_amount` per channel) |
| Step 5 | Step 1 (`funnel_stage`) |
| Step 6 | Steps 1–5 (all outputs) |

Steps 4 and 5 both depend on Step 1 but are otherwise independent of each other — they could run in parallel, but the sequential order is maintained to satisfy C9 and keep the pipeline simple.

---

## 4. Implementation Tasks (in order)

### Phase 1 — Data Models

1. Define `CampaignInputs` dataclass with all 9 input fields and their types.
2. Define output dataclasses: `GoalAnalysis`, `Channel`, `ChannelSelection`, `ChannelBudget`, `BudgetAllocation`, `ChannelKPIs`, `KPITargets`, `KeywordList`, `CampaignBrief`.
3. Define enums: `FunnelStage` (Awareness / Consideration / Conversion), `PricingModel` (CPC / CPM / CPA).

### Phase 2 — Input Validation

4. Implement `validate_inputs(inputs: CampaignInputs)` in `validators/input_validator.py`:
   - Check all required fields are present and non-empty (C3, E4).
   - Detect ambiguous `marketing_goal` and return a clarifying question string instead of raising (E2).
   - Return a list of validation errors or an empty list if inputs are clean.

### Phase 3 — Step Implementations (in pipeline order)

5. Implement `analyze_goal()` in `steps/analyze_goal.py`.
6. Implement `select_channels()` in `steps/select_channels.py` — include all constraint checks (C1, C4, C5) and E1/E5 edge cases.
7. Implement `distribute_budget()` in `steps/distribute_budget.py` — enforce C2 (100% sum) in the calculation, not just as a post-hoc check.
8. Implement `calculate_kpis()` in `steps/calculate_kpis.py` — derive all three KPIs from actual input values; apply E3 scaling for very low budgets.
9. Implement `generate_keywords()` in `steps/generate_keywords.py` — enforce exactly-5 count (C7) and language correctness.
10. Implement `write_brief()` in `steps/write_brief.py` — enforce 3–5 sentence length (C8).

### Phase 4 — Orchestration

11. Implement `agent.py` — instantiate `CampaignInputs`, call `validate_inputs`, then call Steps 1–6 in order, passing outputs forward as inputs to subsequent steps. Halt and surface errors or clarifying questions at any point.
12. Implement `main.py` — accept inputs (CLI args or interactive prompts), construct `CampaignInputs`, call `agent.run()`, print the final `CampaignBrief` and intermediate step outputs.

### Phase 5 — Integration and Testing

13. Write an end-to-end test with a complete, valid input set and assert all 6 step outputs are populated and internally consistent.
14. Write edge-case tests covering: missing required input (E4), ambiguous goal (E2), very low budget (E5), B2B product type (C4), absent existing channels (E1), very low budget (E3).
15. Manually verify that budget percentages always sum to exactly 100% and keyword list always contains exactly 5 items across multiple runs.
