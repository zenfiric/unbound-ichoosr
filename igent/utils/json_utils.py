import json
from logging import Logger
from pathlib import Path
from typing import Any


def update_json_list(
    file_path: Path,
    new_entry: Any,
    logger: Logger,
    registration_key: str = "registration_id",
) -> None:
    """Update or append to a JSON list file based on registration_id or RegistrationNumber."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(new_entry, list) and len(new_entry) == 1:
        new_entry = new_entry[0]
    elif not isinstance(new_entry, dict):
        logger.error(
            "New entry must be a dict or single-item list. Skipping save: %s", new_entry
        )
        return

    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                existing_list = json.load(f)
                if not isinstance(existing_list, list):
                    logger.warning(
                        f"File {file_path} does not contain a list. Overwriting with new list."
                    )
                    existing_list = []
            except json.JSONDecodeError:
                logger.warning(
                    f"File {file_path} is corrupted. Starting with new list."
                )
                existing_list = []
    else:
        existing_list = []

    new_id = new_entry.get(registration_key) or new_entry.get("RegistrationNumber")
    if not new_id:
        logger.error(
            "New entry lacks registration_id or RegistrationNumber. Skipping save: %s",
            new_entry,
        )
        return

    updated = False
    for i, entry in enumerate(existing_list):
        existing_id = entry.get(registration_key) or entry.get("RegistrationNumber")
        if existing_id == new_id:
            existing_list[i] = new_entry
            updated = True
            break

    if not updated:
        existing_list.append(new_entry)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(existing_list, f, indent=2)
    logger.file("Updated %s with entry for ID %s: %s", file_path, new_id, new_entry)
