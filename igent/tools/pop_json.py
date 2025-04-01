import json

import aiofiles
from autogen_core.tools import FunctionTool

from .save_json import save_json


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
