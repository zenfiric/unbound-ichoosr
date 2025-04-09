import asyncio
import json
import os
from logging import Logger
from pathlib import Path
from typing import Any

import pandas as pd
import tiktoken
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from openai import RateLimitError

TOKEN_LIMIT = 30000  # TPM limit for gpt-4o
MODEL_NAME = "gpt-4o"

# Constants
MAX_ITEMS = 10
EXECUTION_TIMES_CSV = "execution_times.csv"


def init_csv_file(stats_file: str = EXECUTION_TIMES_CSV, columns: list = None):
    """Initialize CSV file with headers if it doesn't exist."""
    if not os.path.exists(stats_file):
        if columns is None:
            columns = ["registration_id", "group_time_seconds"]
        df = pd.DataFrame(columns=columns)
        df.to_csv(stats_file, index=False)


def update_execution_times(
    registration_id: str,
    stats_file: str = EXECUTION_TIMES_CSV,
    group_time: float = None,
    pair1_time: float = None,
    pair2_time: float = None,
    matcher1_time: float = None,
    matcher2_time: float = None,
    matcher1_critic_time: float = None,
) -> None:
    """Update execution times in CSV file using pandas with flexible time arguments."""
    if not os.path.exists(stats_file):
        columns = ["registration_id"]
        if group_time is not None:
            columns.append("group_time_seconds")
        if pair1_time is not None:
            columns.append("pair1_time_seconds")
        if pair2_time is not None:
            columns.append("pair2_time_seconds")
        if matcher1_time is not None:
            columns.append("matcher1_time_seconds")
        if matcher2_time is not None:
            columns.append("matcher2_time_seconds")
        if matcher1_critic_time is not None:
            columns.append("matcher1_critic_time_seconds")
        init_csv_file(stats_file, columns=columns)

    df = pd.read_csv(stats_file)

    if registration_id in df["registration_id"].values:
        if group_time is not None and "group_time_seconds" in df.columns:
            df.loc[df["registration_id"] == registration_id, "group_time_seconds"] = (
                f"{group_time:.3f}"
            )
        if pair1_time is not None and "pair1_time_seconds" in df.columns:
            df.loc[df["registration_id"] == registration_id, "pair1_time_seconds"] = (
                f"{pair1_time:.3f}"
            )
        if pair2_time is not None and "pair2_time_seconds" in df.columns:
            df.loc[df["registration_id"] == registration_id, "pair2_time_seconds"] = (
                f"{pair2_time:.3f}"
            )
        if matcher1_time is not None and "matcher1_time_seconds" in df.columns:
            df.loc[
                df["registration_id"] == registration_id, "matcher1_time_seconds"
            ] = f"{matcher1_time:.3f}"
        if matcher2_time is not None and "matcher2_time_seconds" in df.columns:
            df.loc[
                df["registration_id"] == registration_id, "matcher2_time_seconds"
            ] = f"{matcher2_time:.3f}"
        if (
            matcher1_critic_time is not None
            and "matcher1_critic_time_seconds" in df.columns
        ):
            df.loc[
                df["registration_id"] == registration_id, "matcher1_critic_time_seconds"
            ] = f"{matcher1_critic_time:.3f}"
    else:
        new_row = {"registration_id": registration_id}
        if group_time is not None:
            new_row["group_time_seconds"] = f"{group_time:.3f}"
        if pair1_time is not None:
            new_row["pair1_time_seconds"] = f"{pair1_time:.3f}"
        if pair2_time is not None:
            new_row["pair2_time_seconds"] = f"{pair2_time:.3f}"
        if matcher1_time is not None:
            new_row["matcher1_time_seconds"] = f"{matcher1_time:.3f}"
        if matcher2_time is not None:
            new_row["matcher2_time_seconds"] = f"{matcher2_time:.3f}"
        if matcher1_critic_time is not None:
            new_row["matcher1_critic_time_seconds"] = f"{matcher1_critic_time:.3f}"
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(stats_file, index=False)


def count_tokens(messages: str | list[dict[str, Any]]) -> int:
    """Token counting utility"""
    encoding = tiktoken.encoding_for_model(MODEL_NAME)
    if isinstance(messages, str):
        return len(encoding.encode(messages))
    return sum(len(encoding.encode(msg.get("content", ""))) for msg in messages)


def truncate_message(message: str, max_tokens: int) -> str:
    """Truncate message if it exceeds token limit"""
    encoding = tiktoken.encoding_for_model(MODEL_NAME)
    tokens = encoding.encode(message)
    if len(tokens) <= max_tokens:
        return message
    truncated_tokens = tokens[:max_tokens]
    return encoding.decode(truncated_tokens)


async def run_with_backoff(
    pair, task: list[TextMessage], max_retries: int = 3, logger: Logger | None = None
):
    """Rate limit handling with exponential backoff"""
    for attempt in range(max_retries):
        try:
            async for msg in pair.run_stream(
                task=task, cancellation_token=CancellationToken()
            ):
                yield msg
            break
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                logger.warning(
                    "Rate limit exceeded. Retrying in %d seconds...", wait_time
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error("Max retries exceeded: %s", str(e))
                raise e


async def process_pair(
    pair, message: str, registration_id: str, pair_name: str, logger: Logger
) -> dict[str, Any]:
    """Process a pair or group, return success and JSON output(s) from matcher(s)."""
    if count_tokens(message) > TOKEN_LIMIT:
        logger.warning(
            "Message for %s exceeds %d tokens. Truncating...", pair_name, TOKEN_LIMIT
        )
        message = truncate_message(message, TOKEN_LIMIT - 1000)

    logger.info("Running %s for registration %s", pair_name, registration_id)
    success = False
    matcher_output = ""
    json_output = None
    is_group = "Matcher1-Critic-Matcher2" in pair_name  # Detect p1m1m2c
    matcher1_output = ""
    matcher2_output = ""
    json_outputs = {"matches": None, "pos": None} if is_group else None

    async for msg in run_with_backoff(
        pair, [TextMessage(content=message, source="user")], logger=logger
    ):
        if isinstance(msg, TextMessage):
            if msg.source == "user":
                logger.debug("User: %s", msg.content[:100])
            elif "matcher" in msg.source.lower():
                if is_group and "matcher1" in msg.source.lower():
                    logger.info("matcher1: %s", msg.content)
                    matcher1_output += msg.content
                    try:
                        json_start = matcher1_output.find("```json") + 7
                        json_end = matcher1_output.rfind("```")
                        if json_start > 6 and json_end > json_start:
                            json_str = matcher1_output[json_start:json_end].strip()
                            json_outputs["matches"] = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        logger.error("Failed to parse JSON from Matcher1 output: %s", e)
                elif is_group and "matcher2" in msg.source.lower():
                    logger.info("matcher2: %s", msg.content)
                    matcher2_output += msg.content
                    try:
                        json_start = matcher2_output.find("```json") + 7
                        json_end = matcher2_output.rfind("```")
                        if json_start > 6 and json_end > json_start:
                            json_str = matcher2_output[json_start:json_end].strip()
                            json_outputs["pos"] = json.loads(json_str)
                            success = True  # Success after Matcher2 in group
                    except json.JSONDecodeError as e:
                        logger.error("Failed to parse JSON from Matcher2 output: %s", e)
                else:  # Single matcher case (p1m1c1_p2m2c2, p1m1_p2m1)
                    logger.info("matcher: %s", msg.content)
                    matcher_output += msg.content
                    try:
                        json_start = matcher_output.find("```json") + 7
                        json_end = matcher_output.rfind("```")
                        if json_start > 6 and json_end > json_start:
                            json_str = matcher_output[json_start:json_end].strip()
                            json_output = json.loads(json_str)
                            success = True  # Success if JSON parsed (no critic case)
                    except json.JSONDecodeError as e:
                        logger.error("Failed to parse JSON from matcher output: %s", e)
            elif "critic" in msg.source.lower():
                logger.info("critic: %s", msg.content)
                if "APPROVE" in msg.content.upper():
                    success = (
                        True if not is_group else False
                    )  # APPROVE alone not enough for group
            else:
                logger.info("%s: %s", msg.source, msg.content)
        elif isinstance(msg, TaskResult):
            result = f"{pair_name} completed."
            if msg.stop_reason:
                result += f" Stop reason: {msg.stop_reason}"
                if "APPROVE" in msg.stop_reason:
                    success = (
                        True
                        if not is_group
                        else (json_outputs["matches"] and json_outputs["pos"])
                    )
            logger.info("%s", result)

    await asyncio.sleep(1.0)
    if not success:
        logger.warning(
            "%s did not complete successfully for registration %s.",
            pair_name,
            registration_id,
        )
        return {"success": False, "json_output": None}

    if is_group:
        if not json_outputs["matches"]:
            logger.error("%s failed: No valid JSON output from Matcher1.", pair_name)
            return {"success": False, "json_output": None}
        if not json_outputs["pos"]:
            logger.error("%s failed: No valid JSON output from Matcher2.", pair_name)
            return {"success": False, "json_output": None}
        logger.info("%s completed successfully.", pair_name)
        return {"success": True, "json_output": json_outputs}
    else:
        if not json_output:
            logger.error("%s failed: No valid JSON output from matcher.", pair_name)
            return {"success": False, "json_output": None}
        logger.info("%s completed successfully.", pair_name)
        return {"success": True, "json_output": json_output}


def update_json_list(
    file_path: Path,
    new_entry: Any,
    logger: Logger,
    registration_key: str = "registration_id",
) -> None:
    """Update or append to a JSON list file based on registration_id or RegistrationNumber."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Normalize new_entry: if it's a single-item list, extract the dict
    if isinstance(new_entry, list) and len(new_entry) == 1:
        new_entry = new_entry[0]
    elif not isinstance(new_entry, dict):
        logger.error(
            "New entry must be a dict or single-item list. Skipping save: %s", new_entry
        )
        return

    # Read existing list if file exists, otherwise start with an empty list
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

    # Check for registration_id or RegistrationNumber in the new entry
    new_id = new_entry.get(registration_key) or new_entry.get("RegistrationNumber")
    if not new_id:
        logger.error(
            "New entry lacks registration_id or RegistrationNumber. Skipping save: %s",
            new_entry,
        )
        return

    # Update existing entry if found, otherwise append
    updated = False
    for i, entry in enumerate(existing_list):
        existing_id = entry.get(registration_key) or entry.get("RegistrationNumber")
        if existing_id == new_id:
            existing_list[i] = new_entry
            updated = True
            break

    if not updated:
        existing_list.append(new_entry)

    # Save the updated list back to the file
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(existing_list, f, indent=2)
    logger.file("Updated %s with entry for ID %s: %s", file_path, new_id, new_entry)
