import asyncio
import json
import os
from logging import Logger
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

# CSV file path
EXECUTION_TIMES_CSV = "execution_times.csv"


def init_csv_file(stats_file: str = EXECUTION_TIMES_CSV, columns: list = None):
    """Initialize CSV file with headers if it doesn't exist."""
    if not os.path.exists(stats_file):
        if columns is None:
            columns = [
                "registration_id",
                "group_time_seconds",
            ]  # Default for single-group cases
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
):
    """Update execution times in CSV file using pandas with flexible time arguments."""
    # Read existing data or initialize if file doesn't exist
    if not os.path.exists(stats_file):
        # Default columns based on provided arguments
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
        init_csv_file(stats_file, columns=columns)

    df = pd.read_csv(stats_file)

    # Check if registration_id exists
    if registration_id in df["registration_id"].values:
        # Update existing row
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
    else:
        # Add new row
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
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # Save updated dataframe
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
    """Process a pair or group, return success and JSON output from matcher."""
    if count_tokens(message) > TOKEN_LIMIT:
        logger.warning(
            "Message for %s exceeds %d tokens. Truncating...", pair_name, TOKEN_LIMIT
        )
        message = truncate_message(message, TOKEN_LIMIT - 1000)

    logger.info("Running %s for registration %s", pair_name, registration_id)
    success = False
    matcher_output = ""
    json_output = None

    async for msg in run_with_backoff(
        pair, [TextMessage(content=message, source="user")], logger=logger
    ):
        if isinstance(msg, TextMessage):
            if msg.source == "user":
                logger.debug("User: %s", msg.content[:100])
            elif "matcher" in msg.source.lower():
                logger.info("matcher: %s", msg.content)
                matcher_output += msg.content
                # Extract JSON from matcher's output
                try:
                    json_start = matcher_output.find("```json") + 7
                    json_end = matcher_output.rfind("```")
                    if json_start > 6 and json_end > json_start:
                        json_str = matcher_output[json_start:json_end].strip()
                        json_output = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse JSON from matcher output: %s", e)
            elif "critic" in msg.source.lower():
                logger.info("critic: %s", msg.content)
                if "APPROVE" in msg.content.upper():
                    success = True
            else:
                logger.info("%s: %s", msg.source, msg.content)
        elif isinstance(msg, TaskResult):
            result = f"{pair_name} completed."
            if msg.stop_reason:
                result += f" Stop reason: {msg.stop_reason}"
                success = success or "APPROVE" in msg.stop_reason  # Fallback check
            logger.info("%s", result)

    await asyncio.sleep(1.0)  # Brief pause for consistency
    if not success:
        logger.warning(
            "%s did not approve registration %s.", pair_name, registration_id
        )
        return {"success": False, "json_output": None}

    if not json_output:
        logger.error(
            "%s approved but no valid JSON output found from matcher.", pair_name
        )
        return {"success": False, "json_output": None}

    logger.info("%s approved.", pair_name)
    return {"success": True, "json_output": json_output}
