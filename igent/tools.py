import json
import os
from pathlib import Path
from typing import Literal

import aiofiles
import pandas as pd
import requests
from autogen_core.tools import FunctionTool


def fetch_incentives(
    zip_code: str = "55401",
    owner_status: Literal["homeowner", "renter"] = "homeowner",
    household_income: int | str = 100000,
    household_size: int | str = 2,
) -> str:
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


async def read_txt(file_path: str) -> str:
    """Reads the contents of a text file asynchronously.

    Args:
        file_path (str): Path to the text file to read.

    Returns:
        str: Contents of the file as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there's an error reading the file.
    """
    try:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as file:
            content = await file.read()
        return content
    except FileNotFoundError as fnf_err:
        raise FileNotFoundError(f"File not found: {file_path}") from fnf_err
    except IOError as io_err:
        raise IOError(f"Error reading file {file_path}") from io_err


read_txt_tool = FunctionTool(
    read_txt,
    description="Reads the contents of a text file asynchronously and returns it as a string.",
)


async def read_json(file_path: str) -> list[dict]:
    """Reads data from a JSON file."""
    async with aiofiles.open(file_path, "r") as file:
        content = await file.read()
        return json.loads(content)


read_json_tool = FunctionTool(
    read_json,
    description="Reads data from a JSON file.",
)


async def read_csv(file_path: str) -> list[dict]:
    """Read a CSV file and return its contents as a list of dictionaries."""
    df = pd.read_csv(file_path, dtype=str)
    numeric_columns = [
        "Proposal_OptimalAmountOfPanels",
        "Product_AmountOfPanels",
        "Product_EstimatedRoofSizeFt",
        "Product_HomeSize",
        "Product_NumberOfStories",
        "Contact_Zip",
    ]
    for col in df.columns:
        if col in numeric_columns or col.lower().endswith(
            ("size", "amount", "number", "zip")
        ):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.to_dict(orient="records")


read_csv_tool = FunctionTool(
    read_csv,
    description="Reads data from a CSV file and converts likely numeric columns automatically.",
)


async def save_json(data: str | list[dict], file_path: str = "output.json") -> str:
    print(f"save_json called with file_path: {file_path}, data type: {type(data)}")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as json_err:
            raise ValueError("Invalid JSON string provided") from json_err

    if not isinstance(data, list):
        raise ValueError("Data must be a list of dictionaries")

    abs_path = os.path.abspath(file_path)
    print(f"Absolute path: {abs_path}")
    Path(abs_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        async with aiofiles.open(abs_path, "r") as file:
            existing_data = json.loads(await file.read())
            if not isinstance(existing_data, list):
                existing_data = []
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Read error: {e}")
        existing_data = []

    # Use both "RegistrationNumber" and "registration_id" as possible keys
    data_dict = {}
    for entry in existing_data:
        if isinstance(entry, dict):
            key = entry.get("RegistrationNumber") or entry.get("registration_id")
            if key:
                data_dict[key] = entry

    for entry in data:
        if isinstance(entry, dict):
            key = entry.get("RegistrationNumber") or entry.get("registration_id")
            if key:
                data_dict[key] = entry
            else:
                existing_data.append(entry)

    # Combine deduplicated data with entries lacking keys
    final_data = list(data_dict.values()) if data_dict else data

    async with aiofiles.open(abs_path, "w") as file:
        await file.write(json.dumps(final_data, indent=2))

    result = f"Successfully saved data to {file_path}"
    return result


save_json_tool = FunctionTool(
    save_json,
    description="Updates a JSON file with a new list of dictionaries, replacing entries with the same registration_id. Creates file and directories if they don't exist.",
)


async def pop_json(source_file: str, popped_file: str) -> dict:
    """Pops the first element from a JSON list in source_file, saves the rest back,
    and stores the popped element to popped_file using save_json.

    Args:
        source_file (str): Path to the JSON file containing the list to pop from.
        popped_file (str): Path to save the popped element.

    Returns:
        dict: The popped element.

    Raises:
        FileNotFoundError: If source_file doesn't exist.
        ValueError: If source_file is empty or not a list.
    """
    try:
        async with aiofiles.open(source_file, "r", encoding="utf-8") as file:
            data = json.loads(await file.read())
    except FileNotFoundError as fnf_err:
        raise FileNotFoundError(f"Source file not found: {source_file}") from fnf_err
    except json.JSONDecodeError as json_err:
        raise ValueError(f"Invalid JSON in source file: {source_file}") from json_err

    if not isinstance(data, list):
        raise ValueError(f"Source file {source_file} must contain a list")
    if not data:
        raise ValueError(f"Source file {source_file} is empty")

    popped_element = data.pop(0)
    async with aiofiles.open(source_file, "w", encoding="utf-8") as file:
        await file.write(json.dumps(data, indent=2))

    await save_json([popped_element], popped_file)

    return popped_element


pop_json_tool = FunctionTool(
    pop_json,
    description="Pops the first element from a JSON list in source_file, saves the rest back, and stores the popped element to popped_file using save_json.",
)


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


def incentives():
    import requests

    url = "https://api.rewiringamerica.org/api/v1/incentives/programs?language=en"

    headers = {"Authorization": "Bearer YOUR_KEY_HERE"}

    response = requests.get(url, headers=headers)

    print(response.text)
