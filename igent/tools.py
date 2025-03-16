import json

import aiofiles
import pandas as pd
from autogen_core.tools import FunctionTool


async def read_xlsx() -> list[dict]:
    """Reads the entire vehicle dataset from an Excel file."""
    file_path = "static/mynm_info.xlsx"
    df = pd.read_excel(file_path, dtype=str)

    # Convert numerical columns
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    return df.to_dict(orient="records")


read_xlsx_tool = FunctionTool(
    read_xlsx,
    description="Reads data from an Excel file.",
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
