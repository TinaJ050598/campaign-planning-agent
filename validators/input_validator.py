from typing import List

from models.inputs import CampaignInputs

_VALID_PRODUCT_TYPES = {"B2B", "B2C"}


def validate_inputs(inputs: CampaignInputs) -> List[str]:
    """
    Validate all CampaignInputs fields. Returns a list of error strings;
    an empty list means the inputs are clean and the pipeline may proceed.
    Enforces C3 (required fields present) and E4 (block on missing input).
    """
    errors: List[str] = []

    # Required string fields
    required_strings = [
        ("marketing_goal", inputs.marketing_goal),
        ("brand_description", inputs.brand_description),
        ("target_audience", inputs.target_audience),
        ("target_market_language", inputs.target_market_language),
    ]
    for field_name, value in required_strings:
        if not value or not value.strip():
            errors.append(f"'{field_name}' is required and cannot be empty.")

    # Required numeric fields
    if inputs.total_budget is None:
        errors.append("'total_budget' is required.")
    elif inputs.total_budget <= 0:
        errors.append("'total_budget' must be greater than zero.")

    if inputs.product_price is None:
        errors.append("'product_price' is required.")
    elif inputs.product_price <= 0:
        errors.append("'product_price' must be greater than zero.")

    # Cross-field: CPA can never exceed product_price, so budget must allow at
    # least one acquisition (budget >= some small fraction of product_price).
    # We do not enforce a hard floor here — E3 handles very low budgets by
    # scaling KPI expectations — but we flag a clearly impossible situation.
    if (
        not errors
        and inputs.total_budget > 0
        and inputs.product_price > 0
        and inputs.total_budget < inputs.product_price * 0.1
    ):
        errors.append(
            f"'total_budget' ({inputs.total_budget:.2f}) is less than 10% of "
            f"'product_price' ({inputs.product_price:.2f}). The budget is too low "
            "to run a viable campaign."
        )

    # Optional product_type
    if inputs.product_type is not None:
        if inputs.product_type.upper() not in _VALID_PRODUCT_TYPES:
            errors.append(
                f"'product_type' must be one of {sorted(_VALID_PRODUCT_TYPES)}, "
                f"got '{inputs.product_type}'."
            )

    return errors
