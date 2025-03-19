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
    # Read the CSV with all columns as strings to preserve raw data
    df = pd.read_csv(file_path, dtype=str)

    # Dynamically convert columns that are likely numeric based on common patterns
    numeric_columns = [
        "Proposal_OptimalAmountOfPanels", "Product_AmountOfPanels", 
        "Product_EstimatedRoofSizeFt", "Product_HomeSize", 
        "Product_NumberOfStories", "Contact_Zip"  # Add more as needed
    ]
    for col in df.columns:
        if col in numeric_columns or col.lower().endswith(("size", "amount", "number", "zip")):
            df[col] = pd.to_numeric(df[col], errors="coerce")  # Convert to numeric, NaN if invalid

    return df.to_dict(orient="records")


read_csv_tool = FunctionTool(
    read_csv,
    description="Reads data from a CSV file and converts likely numeric columns automatically.",
)
