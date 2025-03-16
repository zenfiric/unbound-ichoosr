import json
import os
from datetime import datetime
from typing import Any

import aiofiles
import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

from igent.tools import (
    read_json_tool, read_xlsx_tool
)

load_dotenv(override=True)

model_config_path = os.getenv("MODEL_CONFIG_PATH", "static/model_config.yaml")


async def get_agent(
    state_path: str, system_message: str = "You are a helpful assistant."
) -> AssistantAgent:
    """Get the assistant agent, load state from file."""
    # Get model client from config.
    # async with aiofiles.open(model_config_path, "r") as file:
    #     content = await file.read()
    #     content = os.path.expandvars(content)
    #     model_config = yaml.safe_load(content)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    # model_client = ChatCompletionClient.load_component(model_config)
    model_client = OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)
    current_datetime = datetime.now().strftime("%B %d, %Y, %H:%M:%S")
    system_message = system_message.format(current_datetime=current_datetime)
    # Create the assistant agent.
    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
        system_message=system_message,
        tools=[read_json_tool, read_xlsx_tool],
    )
    # Load state from file.
    if not os.path.exists(state_path):
        return agent  # Return agent without loading state.
    async with aiofiles.open(state_path, "r") as file:
        state = json.loads(await file.read())
    await agent.load_state(state)
    return agent


async def get_history(history_path: str) -> list[dict[str, Any]]:
    """Get chat history from file."""
    if not os.path.exists(history_path):
        return []
    async with aiofiles.open(history_path, "r") as file:
        return json.loads(await file.read())


async def load_model_config(config_path: str) -> dict[str, Any]:
    async with aiofiles.open(config_path, "r") as file:
        content = await file.read()
        content = os.path.expandvars(content)  # Replace environment variables
        model_config = yaml.safe_load(content)

    return model_config
