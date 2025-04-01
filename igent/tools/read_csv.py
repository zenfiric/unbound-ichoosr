import pandas as pd
from autogen_core.tools import FunctionTool


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
