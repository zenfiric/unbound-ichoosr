import asyncio
import json
import re
from logging import Logger
from typing import Any

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import StructuredMessage, TextMessage
from autogen_core import CancellationToken
from openai import RateLimitError

from .token_utils import (  # Import from token_utils
    TOKEN_LIMIT,
    count_tokens,
    truncate_message,
)


async def run_with_backoff(
    pair,
    task: list[TextMessage],
    max_retries: int = 3,
    logger: Logger | None = None,
) -> Any:
    """Rate limit handling with exponential backoff"""
    for attempt in range(max_retries):
        try:
            if logger:
                logger.debug(
                    "Starting pair.run_stream (attempt %d/%d)", attempt + 1, max_retries
                )
            msg_count = 0
            async for msg in pair.run_stream(
                task=task, cancellation_token=CancellationToken()
            ):
                msg_count += 1
                if logger and msg_count % 5 == 0:
                    logger.debug("Received %d messages so far...", msg_count)
                yield msg
            if logger:
                logger.debug(
                    "Completed pair.run_stream, received %d total messages", msg_count
                )
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
    logger.debug(
        "Starting agent conversation with message length: %d chars", len(message)
    )
    success = False
    matcher_output = ""
    json_output = None
    is_group = "Matcher1-Critic-Matcher2" in pair_name
    matcher1_output = ""
    matcher2_output = ""
    json_outputs = {"matches": None, "pos": None} if is_group else None

    logger.debug("Calling run_with_backoff for %s", pair_name)
    async for msg in run_with_backoff(
        pair, [TextMessage(content=message, source="user")], logger=logger
    ):
        if isinstance(msg, StructuredMessage):
            # Handle structured output from agents with output_content_type
            if "matcher" in msg.source.lower():
                # Extract the root list from the Pydantic RootModel
                structured_data = (
                    msg.content.root
                    if hasattr(msg.content, "root")
                    else msg.content.model_dump()
                )
                logger.info("matcher (structured): %s", structured_data)

                if is_group and "matcher1" in msg.source.lower():
                    json_outputs["matches"] = structured_data
                    success = json_outputs["matches"] is not None
                elif is_group and "matcher2" in msg.source.lower():
                    json_outputs["pos"] = structured_data
                    if json_outputs["pos"] is not None:
                        success = True
                else:
                    json_output = structured_data
                    if json_output is not None:
                        success = True
            else:
                logger.info("%s (structured): %s", msg.source, msg.content)
        elif isinstance(msg, TextMessage):
            if msg.source == "user":
                logger.debug("User: %s", msg.content[:100])
            elif "matcher" in msg.source.lower():
                content = msg.content
                if is_group and "matcher1" in msg.source.lower():
                    logger.info("matcher1: %s", content)
                    matcher1_output += content
                    json_outputs["matches"] = _extract_json_before_approve(
                        matcher1_output, logger, "Matcher1"
                    )
                elif is_group and "matcher2" in msg.source.lower():
                    logger.info("matcher2: %s", content)
                    matcher2_output += content
                    json_outputs["pos"] = _extract_json_before_approve(
                        matcher2_output, logger, "Matcher2"
                    )
                    if json_outputs["pos"] is not None:
                        success = True
                else:
                    logger.info("matcher: %s", content)
                    matcher_output += content
                    json_output = _extract_json_before_approve(
                        matcher_output, logger, "Matcher"
                    )
                    if json_output is not None:
                        success = True
                        # Early termination: We have valid JSON, no need to wait for APPROVE
                        logger.debug(
                            "Got valid JSON early, continuing to wait for APPROVE or completion"
                        )
            elif "critic" in msg.source.lower():
                logger.info("critic: %s", msg.content)
                if "APPROVE" in msg.content.upper():
                    success = (
                        True
                        if not is_group
                        else (json_outputs["matches"] and json_outputs["pos"])
                    )
            else:
                logger.info("%s: %s", msg.source, msg.content)
        elif isinstance(msg, TaskResult):
            result = f"{pair_name} completed."
            if msg.stop_reason:
                result += f" Stop reason: {msg.stop_reason}"
                if "APPROVE" in msg.stop_reason.upper():
                    success = (
                        True
                        if not is_group
                        else (json_outputs["1"] and json_outputs["pos"])
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


# === Helper Function ===
def _extract_json_before_approve(
    output: str, logger: Logger, source_name: str
) -> dict | list | None:
    """
    Extracts JSON from output that may contain:
      - ```json ... ```
      - or plain JSON followed by APPROVE
    Stops at the first 'APPROVE' (case-insensitive) to avoid including it.
    """
    if not output.strip():
        return None

    # Split output at the first occurrence of 'APPROVE' (case-insensitive)
    approve_index = -1
    for approve_variant in ["APPROVE", "approve", "Approve"]:
        idx = output.upper().find(approve_variant)
        if idx != -1 and (approve_index == -1 or idx < approve_index):
            approve_index = idx

    parse_content = output[:approve_index].strip() if approve_index != -1 else output

    # Look for ```json ... ```
    json_match = re.search(r"```json\s*(.*?)\s*```", parse_content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse JSON from %s (inside backticks): %s", source_name, e
            )
            return None

    # Fallback: Try to parse the entire content before APPROVE as JSON (common in gpt-5)
    try:
        parsed = json.loads(parse_content)
        if isinstance(parsed, (list, dict)):
            return parsed
    except json.JSONDecodeError:
        pass

    # Last resort: look for first [ or { and try to parse from there
    start_idx = parse_content.find("[")
    if start_idx == -1:
        start_idx = parse_content.find("{")
    if start_idx != -1:
        try:
            # Find matching closing bracket
            json_str = _extract_braced_content(parse_content[start_idx:])
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

    logger.debug("%s: No valid JSON found in output (before APPROVE).", source_name)
    return None


def _extract_braced_content(s: str) -> str:
    """Extract content between first { or [ and matching } or ]"""
    if not s:
        return s
    start_char = s[0]
    if start_char not in "[{":
        return s
    end_char = "}" if start_char == "{" else "]"
    stack = 1
    i = 1
    while i < len(s) and stack > 0:
        if s[i] == start_char:
            stack += 1
        elif s[i] == end_char:
            stack -= 1
        i += 1
    return s[:i] if stack == 0 else s
