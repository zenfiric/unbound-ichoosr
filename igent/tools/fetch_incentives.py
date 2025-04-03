"""
Fetch Incentives
This tool fetches incentive programs from the Rewiring America API for the specified zip code.

Source: https://api.rewiringamerica.org/docs/routes#find-eligible-incentives
"""

import os
from typing import Literal

import requests
from autogen_core.tools import FunctionTool


def fetch_incentives(
    zip_code: str = "55401",
    owner_status: Literal["homeowner", "renter"] = "homeowner",
    household_income: int | str = 30000,
    household_size: int | str = 2,
) -> str:
    """
    Fetches incentive programs from Rewiring America API for the specified zip code.

    Args:
        zip_code: Zip code to fetch incentives for. Defaults to "55401".
        owner_status: Homeowner or renter status. Defaults to "homeowner".
        household_income: Household income. Defaults to 100000.
        household_size: Household size. Defaults to 2.

    Returns:
        JSON string containing the incentives
    """
    url = "https://api.rewiringamerica.org/api/v1/calculator"
    api_key = os.getenv("REWIRING_AMERICA_API_KEY")

    if not api_key:
        raise ValueError("REWIRING_AMERICA_API_KEY environment variable not set")

    headers = {"Authorization": f"Bearer {api_key}"}
    params = {
        "zip": zip_code,
        "owner_status": owner_status,
        "household_income": household_income,
        "household_size": household_size,
    }
    response = requests.get(url, headers=headers, params=params, timeout=15)
    return response.text


fetch_incentives_tool = FunctionTool(
    fetch_incentives,
    description="Fetches incentive programs from Rewiring America API for the specified zip code.",
)
