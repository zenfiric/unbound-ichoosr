"""Pydantic schemas for structured output from agents."""

from typing import Any

from pydantic import BaseModel, Field, RootModel


class MatchItem(BaseModel):
    """Single match item for Matcher1 (Phase A) - matches registrations to suppliers."""

    registration_id: str = Field(..., description="Registration identifier")
    campaign_name: str = Field(..., description="Campaign name")
    supplier_id: str = Field(..., description="Matched supplier identifier")
    zip_code: str = Field(..., description="Registration ZIP code")
    panel_name: str = Field(..., description="Solar panel product name")
    num_panels: str = Field(..., description="Number of panels requested")
    panel_capacity: str = Field(..., description="Panel capacity in watts")
    battery_name: Any = Field(..., description="Battery product name or null")
    battery_capacity: Any = Field(..., description="Battery capacity or null")


class MatcherOutput(RootModel[list[MatchItem]]):
    """List of matches from Matcher1."""

    root: list[MatchItem]


class EnrichedMatchItem(BaseModel):
    """Single enriched match item for Matcher2 (Phase B) - enriches matches with pricing and subsidies."""

    registration_id: str = Field(..., description="Registration identifier")
    campaign_name: str = Field(..., description="Campaign name")
    supplier_id: str = Field(..., description="Matched supplier identifier")
    zip_code: str = Field(..., description="Registration ZIP code")
    panel_name: str = Field(..., description="Solar panel product name")
    panel_capacity: str = Field(..., description="Panel capacity in watts")
    battery_name: Any = Field(..., description="Battery product name or null")
    battery_capacity: Any = Field(..., description="Battery capacity or null")
    num_panels: str = Field(..., description="Number of panels requested")
    product_type: str = Field(..., description="Product type (e.g., 'Solar')")
    product_price: str = Field(..., description="Cash price for the product")
    eligible_subsidies: list[str] = Field(
        default_factory=list, description="List of eligible incentive names"
    )
    payment_type: str = Field(..., description="Payment method")


class EnrichedMatchOutput(RootModel[list[EnrichedMatchItem]]):
    """List of enriched matches from Matcher2."""

    root: list[EnrichedMatchItem]
