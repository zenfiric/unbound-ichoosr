# igent/utils.py
import asyncio
from logging import Logger
from pathlib import Path
from typing import Any

import tiktoken
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from openai import RateLimitError

TOKEN_LIMIT = 30000  # TPM limit for gpt-4o
MODEL_NAME = "gpt-4o"


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
    pair, message: str, registration_id: str, pair_name: str, output_file: str, logger
) -> bool:
    if count_tokens(message) > TOKEN_LIMIT:
        logger.warning(
            "Message for %s exceeds %d tokens. Truncating...", pair_name, TOKEN_LIMIT
        )
        message = truncate_message(message, TOKEN_LIMIT - 1000)

    logger.info("Running %s for registration %s", pair_name, registration_id)
    success = False
    critic_output = ""

    async for msg in run_with_backoff(
        pair, [TextMessage(content=message, source="user")], logger=logger
    ):
        if isinstance(msg, TextMessage):
            if msg.source == "user":
                logger.debug("User: %s", msg.content[:100])
            elif msg.source == "matcher":
                logger.info("matcher: %s", msg.content)  # Explicitly prefix "matcher:"
            elif msg.source == "critic":
                logger.info("critic: %s", msg.content)  # Explicitly prefix "critic:"
                critic_output += msg.content
            else:
                logger.info("%s: %s", msg.source, msg.content)
        elif isinstance(msg, TaskResult):
            result = "%s completed." % pair_name
            if msg.stop_reason:
                result += f" Stop reason: {msg.stop_reason}"
                success = "APPROVE" in msg.stop_reason or "APPROVE" in critic_output
            logger.info("%s", result)

    await asyncio.sleep(1.0)
    if success:
        if not Path(output_file).exists():
            logger.error("'%s' was not saved after approval.", output_file)
            return False
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()
                if not content.strip():
                    logger.error("'%s' is empty despite approval.", output_file)
                    return False
                logger.file("Saved to %s: %s", output_file, content)
        except Exception as e:
            logger.error("Error reading '%s': %s", output_file, str(e))
            return False
        logger.file("%s approved and saved output to %s.", pair_name, output_file)
        return True
    else:
        logger.warning(
            "%s did not approve registration %s.", pair_name, registration_id
        )
        return False
