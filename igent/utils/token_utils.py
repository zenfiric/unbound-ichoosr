from typing import Any

import tiktoken

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
