import json
import os
from pathlib import Path

import aiofiles
from autogen_core.tools import FunctionTool


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
