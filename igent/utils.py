import asyncio
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


async def run_with_backoff(pair, task: list[TextMessage], max_retries: int = 3):
    """Rate limit handling with exponential backoff"""
    for attempt in range(max_retries):
        try:
            async for msg in pair.run_stream(
                task=task, cancellation_token=CancellationToken()
            ):
                yield msg
            break  # Exit loop if successful
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                raise e


async def process_pair(
    pair, message: str, registration_id: str, pair_name: str, output_file: str
) -> bool:
    if count_tokens(message) > TOKEN_LIMIT:
        print(
            f"Warning: Message for {pair_name} exceeds {TOKEN_LIMIT} tokens. Truncating..."
        )
        message = truncate_message(message, TOKEN_LIMIT - 1000)  # Leave buffer

    print(f"Running {pair_name} for registration {registration_id}")
    success = False
    async for msg in run_with_backoff(
        pair, [TextMessage(content=message, source="user")]
    ):
        if isinstance(msg, TextMessage):
            prefix = f"{msg.source}: {msg.content[:100] if msg.source == 'user' else msg.content}"
            print(prefix)
        elif isinstance(msg, TaskResult):
            result = f"{pair_name} completed."
            if msg.stop_reason:
                result += f" Stop reason: {msg.stop_reason}"
                success = "APPROVE" in msg.stop_reason
            print(result)

    await asyncio.sleep(0.1)
    if success and not Path(output_file).exists():
        print(f"Error: '{output_file}' was not saved.")
        return False
    return success
