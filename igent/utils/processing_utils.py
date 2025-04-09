import asyncio
import json
from logging import Logger
from typing import Any

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from openai import RateLimitError

from .token_utils import (  # Import from token_utils
    TOKEN_LIMIT,
    count_tokens,
    truncate_message,
)


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
    pair, message: str, run_id: str, pair_name: str, logger: Logger
) -> dict[str, Any]:
    """Process a pair or group, return success and JSON output(s) from matcher(s)."""
    if count_tokens(message) > TOKEN_LIMIT:
        logger.warning(
            "Message for %s exceeds %d tokens. Truncating...", pair_name, TOKEN_LIMIT
        )
        message = truncate_message(message, TOKEN_LIMIT - 1000)

    logger.info("Running %s for registration %s", pair_name, run_id)
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
            "%s did not complete successfully for registration %s.", pair_name, run_id
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
