import json

import aiofiles
import pandas as pd
from autogen_core.tools import FunctionTool


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
    """Saves data to a JSON file, creating the file if it doesn't exist."""
    # Convert string data to list if needed
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON string provided")

    if not isinstance(data, list):
        raise ValueError("Data must be a list of dictionaries")

    try:
        # Try to read existing data
        async with aiofiles.open(file_path, "r") as file:
            existing_data = json.loads(await file.read())
            if not isinstance(existing_data, list):
                existing_data = []
    except FileNotFoundError:
        # If file doesn't exist, start with empty list
        existing_data = []

    # Create dictionary of existing entries
    data_dict = {
        entry["registration_id"]: entry
        for entry in existing_data
        if isinstance(entry, dict) and "registration_id" in entry
    }

    # Update with new data
    for entry in data:
        if isinstance(entry, dict) and "registration_id" in entry:
            data_dict[entry["registration_id"]] = entry

    # Write updated data
    async with aiofiles.open(file_path, "w") as file:
        await file.write(json.dumps(list(data_dict.values()), indent=2))

    return f"Successfully saved data to {file_path}"


save_json_tool = FunctionTool(
    save_json,
    description="Updates a JSON file with a new list of dictionaries, replacing entries with the same registration_id.",
)
