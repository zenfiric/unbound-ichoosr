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
        "Proposal_OptimalAmountOfPanels", "Product_AmountOfPanels", 
        "Product_EstimatedRoofSizeFt", "Product_HomeSize", 
        "Product_NumberOfStories", "Contact_Zip"
    ]
    for col in df.columns:
        if col in numeric_columns or col.lower().endswith(("size", "amount", "number", "zip")):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.to_dict(orient="records")


read_csv_tool = FunctionTool(
    read_csv,
    description="Reads data from a CSV file and converts likely numeric columns automatically.",
)


async def save_json(file_path: str, data: list[dict]) -> str:
    """Saves a list of dictionaries to a JSON file."""
    async with aiofiles.open(file_path, "w") as file:
        await file.write(json.dumps(data, indent=2))
    return f"Successfully saved data to {file_path}"


save_json_tool = FunctionTool(
    save_json,
    description="Saves a list of dictionaries to a JSON file.",
)
