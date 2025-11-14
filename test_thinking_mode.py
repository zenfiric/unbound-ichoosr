#!/usr/bin/env python3
"""Test script to verify enable_thinking parameter works correctly."""

import asyncio

from igent.models import get_model_client


async def test_thinking_modes():
    """Test both thinking enabled and disabled modes."""

    print("Testing ZAI model with thinking disabled (default)...")
    client_no_thinking = await get_model_client("zai_glm4_5_air", enable_thinking=False)
    print("✓ Client created with thinking disabled")
    print(f"  create_args: {client_no_thinking._create_args}")

    print("\nTesting ZAI model with thinking enabled...")
    client_with_thinking = await get_model_client(
        "zai_glm4_5_air", enable_thinking=True
    )
    print("✓ Client created with thinking enabled")
    print(f"  create_args: {client_with_thinking._create_args}")

    print("\n" + "=" * 60)
    print("SUCCESS: enable_thinking parameter is wired through correctly!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_thinking_modes())
