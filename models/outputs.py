from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class FunnelStage(str, Enum):
    AWARENESS = "Awareness"
    CONSIDERATION = "Consideration"
    CONVERSION = "Conversion"


class PricingModel(str, Enum):
    CPC = "CPC"
    CPM = "CPM"
    CPA = "CPA"


@dataclass
class GoalAnalysis:
    funnel_stage: Optional[FunnelStage]
    funnel_stage_rationale: Optional[str]
    clarifying_question: Optional[str] = None

    @property
    def is_ambiguous(self) -> bool:
        return self.clarifying_question is not None


@dataclass
class Channel:
    name: str
    pricing_model: PricingModel
    rationale: str


@dataclass
class ChannelSelection:
    channels: List[Channel]


@dataclass
class ChannelBudget:
    channel_name: str
    percentage: float       # normalised to sum exactly to 100 across all channels
    absolute_amount: float  # derived as total_budget × (percentage / 100)
    justification: str


@dataclass
class BudgetAllocation:
    allocations: List[ChannelBudget]


@dataclass
class ChannelKPIs:
    channel_name: str
    ctr_target: float   # percentage, e.g. 2.5 means 2.5%
    cpa_target: float   # cost per acquisition in campaign currency
    roas_target: float  # ratio: product_price / cpa_target


@dataclass
class KPITargets:
    channel_kpis: List[ChannelKPIs]


@dataclass
class KeywordList:
    keywords: List[str]  # exactly 5 entries, in target_market_language


@dataclass
class CampaignBrief:
    campaign_brief: str  # 3–5 sentences of prose, ready for a marketing team
