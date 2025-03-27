import json
import os
from pathlib import Path

import aiofiles
import pandas as pd
from autogen_core.tools import FunctionTool


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
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except IOError as e:
        raise IOError(f"Error reading file {file_path}: {str(e)}")


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
            print("Converted string to list:", data)
        except json.JSONDecodeError:
            print("JSON decode error")
            raise ValueError("Invalid JSON string provided")

    if not isinstance(data, list):
        print("Data is not a list")
        raise ValueError("Data must be a list of dictionaries")

    abs_path = os.path.abspath(file_path)
    print(f"Absolute path: {abs_path}")
    Path(abs_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        async with aiofiles.open(abs_path, "r") as file:
            existing_data = json.loads(await file.read())
            if not isinstance(existing_data, list):
                existing_data = []
        print(f"Existing data: {existing_data}")
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
                # If neither key exists, append directly to avoid losing data
                print(
                    f"Warning: Entry missing both 'RegistrationNumber' and 'registration_id': {entry}"
                )
                existing_data.append(entry)

    # Combine deduplicated data with entries lacking keys
    final_data = list(data_dict.values()) if data_dict else data

    async with aiofiles.open(abs_path, "w") as file:
        await file.write(json.dumps(final_data, indent=2))
        print(f"File written to {abs_path} with data: {final_data}")

    result = f"Successfully saved data to {file_path}"
    print(f"Returning: {result}")
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
    # Read the source JSON file
    try:
        async with aiofiles.open(source_file, "r", encoding="utf-8") as file:
            data = json.loads(await file.read())
    except FileNotFoundError:
        raise FileNotFoundError(f"Source file not found: {source_file}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in source file: {source_file}")

    # Validate data
    if not isinstance(data, list):
        raise ValueError(f"Source file {source_file} must contain a list")
    if not data:
        raise ValueError(f"Source file {source_file} is empty")

    # Pop the first element
    popped_element = data.pop(0)

    # Save the remaining list back to source_file
    async with aiofiles.open(source_file, "w", encoding="utf-8") as file:
        await file.write(json.dumps(data, indent=2))

    # Save the popped element to popped_file using save_json
    # Wrap in a list since save_json expects a list of dicts
    await save_json([popped_element], popped_file)

    return popped_element


pop_json_tool = FunctionTool(
    pop_json,
    description="Pops the first element from a JSON list in source_file, saves the rest back, and stores the popped element to popped_file using save_json.",
)
