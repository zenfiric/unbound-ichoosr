"""Supplier capacity tracking - separate from offers data.

This module manages supplier capacity tracking in a dedicated capacity file,
keeping the offers file immutable and containing only supplier offer details.
"""

import json
import os
from pathlib import Path

import aiofiles
from autogen_core.tools import FunctionTool


async def initialize_capacity_file(
    offers_file: str, capacity_file: str
) -> dict[str, dict]:
    """Initialize capacity file from offers file if it doesn't exist.

    Args:
        offers_file: Path to the supplier offers JSON file
        capacity_file: Path to the capacity tracking JSON file

    Returns:
        Dictionary mapping SupplierID to capacity data

    Raises:
        ValueError: If offers file cannot be read or parsed
    """
    capacity_path = Path(capacity_file)

    # If capacity file exists, load and return it
    if capacity_path.exists():
        async with aiofiles.open(capacity_path, "r") as f:
            return json.loads(await f.read())

    # Otherwise, initialize from offers file
    abs_offers_path = os.path.abspath(offers_file)
    try:
        async with aiofiles.open(abs_offers_path, "r") as f:
            offers_data = json.loads(await f.read())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ValueError(f"Could not read or parse offers file at {offers_file}") from e

    if not isinstance(offers_data, dict) or "SupplierOffers" not in offers_data:
        raise ValueError("Offers file must contain a 'SupplierOffers' key with a list")

    # Extract capacity information
    capacity_data = {}
    for supplier in offers_data["SupplierOffers"]:
        supplier_id = supplier.get("SupplierID")
        if not supplier_id:
            continue

        capacity_data[supplier_id] = {
            "SupplierID": supplier_id,
            "Capacity": supplier.get("Capacity", 0),
            "Used": 0,
            "UsedPct": 0.0,
        }

    # Save the initialized capacity file
    capacity_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(capacity_path, "w") as f:
        await f.write(json.dumps(capacity_data, indent=2))

    return capacity_data


async def update_supplier_capacity(
    match_data: str | dict | list[dict],
    offers_file: str = "offers.json",
    capacity_file: str = "capacity.json",
) -> str:
    """Increments the 'Used' field by 1 for the supplier in the latest match.

    This function updates the capacity tracking file, NOT the offers file.

    Args:
        match_data: A JSON string, single match dictionary, or list of match dictionaries
        offers_file: Path to the supplier offers JSON file (used for initialization)
        capacity_file: Path to the capacity tracking JSON file

    Returns:
        Success message with the file path

    Raises:
        ValueError: If match_data format is invalid or supplier ID is not found
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

    # Initialize or load capacity data
    capacity_data = await initialize_capacity_file(offers_file, capacity_file)

    # Process only the latest match (last entry in the list)
    match = match_data[-1]
    supplier_id = match.get("supplier_id") or match.get("SupplierID")

    if not supplier_id:
        raise ValueError(f"Match missing both supplier_id and SupplierID: {match}")

    if supplier_id not in capacity_data:
        raise ValueError(f"SupplierID {supplier_id} not found in capacity data")

    supplier_capacity = capacity_data[supplier_id]
    current_used = supplier_capacity["Used"]
    capacity = supplier_capacity["Capacity"]

    # Increment Used by 1
    new_used = current_used + 1
    if new_used > capacity:
        raise ValueError(
            f"Supplier {supplier_id} capacity exceeded: {new_used} > {capacity}"
        )

    supplier_capacity["Used"] = new_used
    supplier_capacity["UsedPct"] = (
        round(new_used / capacity, 2) if capacity > 0 else 0.0
    )

    # Write the updated capacity data
    capacity_path = Path(capacity_file)
    capacity_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(capacity_path, "w") as f:
        await f.write(json.dumps(capacity_data, indent=2))

    return f"Successfully updated supplier capacity in {capacity_file}"


async def get_available_capacity(
    capacity_file: str = "capacity.json",
) -> dict[str, dict]:
    """Get current capacity data for all suppliers.

    Args:
        capacity_file: Path to the capacity tracking JSON file

    Returns:
        Dictionary mapping SupplierID to capacity data

    Raises:
        ValueError: If capacity file cannot be read
    """
    capacity_path = Path(capacity_file)
    if not capacity_path.exists():
        raise ValueError(f"Capacity file not found: {capacity_file}")

    async with aiofiles.open(capacity_path, "r") as f:
        return json.loads(await f.read())


async def reset_capacity(
    capacity_file: str = "capacity.json",
) -> str:
    """Reset all supplier capacity to 0.

    Args:
        capacity_file: Path to the capacity tracking JSON file

    Returns:
        Success message

    Raises:
        ValueError: If capacity file cannot be read
    """
    capacity_data = await get_available_capacity(capacity_file)

    for supplier_capacity in capacity_data.values():
        supplier_capacity["Used"] = 0
        supplier_capacity["UsedPct"] = 0.0

    async with aiofiles.open(capacity_file, "w") as f:
        await f.write(json.dumps(capacity_data, indent=2))

    return f"Successfully reset capacity in {capacity_file}"


# AutoGen tool registration
update_supplier_capacity_tool = FunctionTool(
    update_supplier_capacity,
    description="Increments the 'Used' field by 1 for the supplier in the latest match and updates 'UsedPct' as a percentage. Updates capacity tracking file, not offers file.",
)
