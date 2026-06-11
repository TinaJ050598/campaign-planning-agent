from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CampaignInputs:
    marketing_goal: str
    brand_description: str
    target_audience: str
    total_budget: float
    product_price: float
    target_market_language: str
    existing_channels: List[str] = field(default_factory=list)
    product_type: Optional[str] = None  # "B2B" or "B2C"
    currency: str = "GBP"  # e.g. GBP, EUR, USD
