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
        message = truncate_message(message, TOKEN_LIMIT - 1000)

    print(f"Running {pair_name} for registration {registration_id}")
    success = False
    critic_output = ""

    async for msg in run_with_backoff(
        pair, [TextMessage(content=message, source="user")]
    ):
        if isinstance(msg, TextMessage):
            prefix = f"{msg.source}: {msg.content[:100] if msg.source == 'user' else msg.content}"
            print(prefix)
            if msg.source == "critic":
                critic_output += msg.content
                print(f"Full critic output: {msg.content}")
        elif isinstance(msg, TaskResult):
            result = f"{pair_name} completed."
            if msg.stop_reason:
                result += f" Stop reason: {msg.stop_reason}"
                success = "APPROVE" in msg.stop_reason or "APPROVE" in critic_output
            print(result)

    await asyncio.sleep(1.0)  # Increase to 1 second for file I/O
    if success:
        if not Path(output_file).exists():
            print(f"Error: '{output_file}' was not saved after approval.")
            return False
        try:
            with open(output_file, "r") as f:
                content = f.read()
                if not content.strip():
                    print(f"Error: '{output_file}' is empty despite approval.")
                    return False
                print(f"{output_file} content after save: {content}")
        except Exception as e:
            print(f"Error reading '{output_file}': {e}")
            return False
        print(f"{pair_name} approved and saved output to {output_file}.")
        return True
    else:
        print(f"{pair_name} did not approve registration {registration_id}.")
        return False
