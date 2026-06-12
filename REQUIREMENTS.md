# Campaign Planning Agent — Requirements Document

---

## 1. Inputs

| Input | Data Type | Required | Notes |
|---|---|---|---|
| `marketing_goal` | String | Yes | Describes what the brand wants to achieve (e.g. "increase signups", "grow brand awareness") |
| `brand_description` | String | Yes | Context about the brand — whether it is new, established, B2B, B2C, etc. |
| `target_audience` | String | Yes | Description of the intended audience (demographics, job titles, interests, geography) |
| `total_budget` | Number (currency as provided by user) | Yes | Total available spend for the campaign |
| `product_price` | Number (currency) | Yes | Price of the product or service being marketed; used to calculate CPA and ROAS |
| `currency` | String | No | Currency for budget and price values (e.g. GBP, EUR, USD); defaults to GBP if not provided |
| `target_market_language` | String | Yes | Language of the target market (used in Step 5 for keyword generation) |
| `existing_channels` | List of Strings | No | Channels the brand currently uses; if absent, agent starts from scratch |
| `product_type` | String (B2B or B2C) | No | Informs channel preference rules (e.g. B2B → prefer LinkedIn) |

---

## 2. Outputs

### 2.1 Step Outputs (in order)

#### Step 1 — `analyze_goal()`
| Output | Format |
|---|---|
| `funnel_stage` | Enum: `Awareness`, `Consideration`, or `Conversion` |
| `funnel_stage_rationale` | Single sentence string explaining the selection |

#### Step 2 — `select_channels()`
| Output | Format |
|---|---|
| `channels` | List of up to 3 objects, each containing: `name` (String), `pricing_model` (Enum: CPC / CPM / CPA), `rationale` (single sentence String) |

#### Step 3 — `distribute_budget()`
| Output | Format |
|---|---|
| `budget_allocation` | List of objects, one per channel, each containing: `channel_name` (String), `percentage` (Number, 0–100), `absolute_amount` (Number, currency), `justification` (String) |
| `allocation_check` | Implicit: percentages across all channels must sum to exactly 100% |

#### Step 4 — `calculate_kpis()`
| Output | Format |
|---|---|
| `kpi_targets` | List of objects, one per channel, each containing: `channel_name` (String), `ctr_target` (Number, expressed as %), `cpa_target` (Number, currency — derived from product price), `roas_target` (Number, ratio — derived from budget and expected return) |

#### Step 5 — `generate_keywords()`
| Output | Format |
|---|---|
| `keywords` | Exactly 5 strings; high-intent; in the language of the target market; matched to the selected funnel stage |

#### Step 6 — `write_brief()`
| Output | Format |
|---|---|
| `campaign_brief` | Prose string, 3–5 sentences; references channels, KPI targets, and target audience; no further editing required |

---

## 3. Processing Logic Per Step

### Step 1 — `analyze_goal()`
1. Read `marketing_goal` and `brand_description`.
2. Apply the following classification rules:
   - **Awareness** — brand is new or unknown; goal is reach.
   - **Consideration** — audience already knows the brand; goal is engagement.
   - **Conversion** — goal is a direct purchase or signup.
3. Assign exactly one `funnel_stage`.
4. Output a one-sentence rationale citing the specific evidence from the inputs that determined the stage.

### Step 2 — `select_channels()`
1. Use `funnel_stage` (from Step 1) and `target_audience` as primary selection criteria.
2. Apply constraint rules (see Section 4) to filter or rank candidates.
3. Select between 1 and 3 channels (max 3; max 2 if total_budget is very low relative to product price).
4. For each selected channel, assign a pricing model (CPC, CPM, or CPA) appropriate to how that channel is typically bought.
5. Write one sentence per channel explaining the fit for this specific audience.

### Step 3 — `distribute_budget()`
1. Take the `channels` list from Step 2 and `total_budget` from inputs.
2. Assign a percentage allocation to each channel; allocations must sum to exactly 100%.
3. Compute `absolute_amount = total_budget × (percentage / 100)` for each channel.
4. Justify each allocation based on the channel's priority within the chosen funnel stage (e.g. primary vs. supporting channel).

### Step 4 — `calculate_kpis()`
1. For each channel, derive KPI targets from `product_price`, `total_budget`, and each channel's `absolute_amount`. Do not use generic benchmark numbers.
2. **CTR target** — estimate per-channel based on channel type and funnel stage.
3. **CPA target** — derive from `product_price` (e.g. a typical acceptable CPA as a fraction of product price).
4. **ROAS target** — derive from the channel's budget allocation and the expected revenue return at the given CPA.

### Step 5 — `generate_keywords()`
1. Generate exactly 5 keywords.
2. Keywords must reflect the intent level of the selected `funnel_stage`:
   - Awareness → informational / broad terms
   - Consideration → comparative / category terms
   - Conversion → transactional / brand + buy terms
3. All keywords must be in `target_market_language`.

### Step 6 — `write_brief()`
1. Synthesise all prior step outputs into a single brief.
2. The brief must be 3–5 sentences.
3. It must explicitly name the selected channels, state the KPI targets, and describe the target audience.
4. The brief must be self-contained and ready to hand to a marketing team without further editing.

---

## 4. Constraints

| ID | Constraint | Applies To |
|---|---|---|
| C1 | Maximum 3 channels may be selected | Step 2 |
| C2 | Budget percentage allocations must sum to exactly 100% | Step 3 |
| C3 | If any required input is missing, agent must ask for it before proceeding | All steps |
| C4 | B2B products must prefer LinkedIn over TikTok when both are candidates | Step 2 |
| C5 | Budget is very low relative to product price: recommend a maximum of 2 channels | Step 2 |
| C6 | KPI targets must be calculated from actual inputs; generic placeholder numbers are not permitted | Step 4 |
| C7 | Keywords must be exactly 5 — no more, no fewer | Step 5 |
| C8 | Campaign brief must be 3–5 sentences | Step 6 |
| C9 | Steps must be executed in order (1 → 6); no step may be skipped | All steps |

---

## 5. Edge Cases

| ID | Condition | Required Behaviour |
|---|---|---|
| E1 | `existing_channels` is absent or empty | Start fresh; recommend channels covering the appropriate funnel stage without anchoring on prior usage |
| E2 | `marketing_goal` is ambiguous or unclear | Ask exactly one clarifying question before proceeding; do not guess the funnel stage |
| E3 | `total_budget` is very low (below a meaningful per-channel minimum) | Adjust KPI targets downward to reflect reduced scale; do not output targets that are unachievable at that spend level |
| E4 | Required input is missing at any step | Block execution of that step; prompt the user for the missing value before continuing |
| E5 | `total_budget` is very low relative to product price | Cap channel selection at 2 (intersection of C5 and general constraint C1) |
