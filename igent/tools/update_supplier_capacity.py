import json
import os
from pathlib import Path

import aiofiles
from autogen_core.tools import FunctionTool


async def update_supplier_capacity(
    match_data: str | dict | list[dict], offers_file: str = "offers.json"
) -> str:
    """Increments the 'Used' field by 1 for the supplier in the latest match and updates 'UsedPct'.

    Args:
        match_data: A JSON string, single match dictionary, or list of match dictionaries with supplier_id.
        offers_file: Path to the supplier offers JSON file (default: 'offers.json').

    Returns:
        Success message with the file path.

    Raises:
        ValueError: If match_data format is invalid or supplier_id is not found.
    """
    # Handle string input by parsing JSON
    if isinstance(match_data, str):
        try:
            match_data = json.loads(match_data)
        except json.JSONDecodeError as json_err:
            raise ValueError(
                "Invalid JSON string provided for match_data"
            ) from json_err

    if isinstance(match_data, dict):
        match_data = [match_data]
    if not isinstance(match_data, list) or not all(
        isinstance(d, dict) for d in match_data
    ):
        raise ValueError("match_data must be a dictionary or list of dictionaries")

    abs_offers_path = os.path.abspath(offers_file)
    Path(abs_offers_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        async with aiofiles.open(abs_offers_path, "r") as file:
            offers_data = json.loads(await file.read())
    except (FileNotFoundError, json.JSONDecodeError):
        raise ValueError(f"Could not read or parse offers file at {offers_file}")

    if not isinstance(offers_data, dict) or "SupplierOffers" not in offers_data:
        raise ValueError("Offers file must contain a 'SupplierOffers' key with a list")

    supplier_offers = offers_data["SupplierOffers"]
    updated = False

    # Process only the latest match (last entry in the list, since save_json appends)
    match = match_data[-1]  # Take the most recent match
    supplier_id = match.get("supplier_id")

    if not supplier_id:
        raise ValueError(f"Match missing supplier_id: {match}")

    supplier_found = False
    for supplier in supplier_offers:
        if supplier.get("SupplierID") == supplier_id:
            supplier_found = True
            current_used = supplier.get("Used", 0)
            capacity = supplier.get("Capacity", 0)

            # Increment Used by 1 for this supplier only
            new_used = current_used + 1
            if new_used > capacity:
                raise ValueError(
                    f"Supplier {supplier_id} capacity exceeded: {new_used} > {capacity}"
                )

            supplier["Used"] = new_used
            supplier["UsedPct"] = round(new_used / capacity, 2) if capacity > 0 else 0
            updated = True
            break

    if not supplier_found:
        raise ValueError(f"SupplierID {supplier_id} not found in offers")
    if not updated:
        return f"No updates made to {offers_file}"

    # Write the updated offers back
    async with aiofiles.open(abs_offers_path, "w") as file:
        await file.write(json.dumps(offers_data, indent=2))

    return f"Successfully updated supplier capacity and UsedPct in {offers_file}"


update_supplier_capacity_tool = FunctionTool(
    update_supplier_capacity,
    description="Increments the 'Used' field by 1 for the supplier in the latest match and updates 'UsedPct' as a percentage.",
)
