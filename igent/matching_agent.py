import json
import os
from typing import Any

import aiofiles
import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.models import ChatCompletionClient
from dotenv import load_dotenv

from igent.tools import (
    read_json_tool, read_xlsx_tool
)

load_dotenv(override=True)

async def get_agent(
    state_path: str,
    matcher_role: str = "You are a helpful assistant.",
    critic_role: str = "You are a critic. Provide constructive feedback. Respond with 'APPROVE' if your feedback has been addressed."
) -> AssistantAgent:
    """Get the assistant agent, load state from file."""
    # Get model client from config.
    async with aiofiles.open(state_path, "r") as file:
        content = await file.read()
        content = os.path.expandvars(content)
        model_config = yaml.safe_load(content)
    model_client = ChatCompletionClient.load_component(model_config)

    # Create the assistant agent.
    matcher = AssistantAgent(
        name="matcher",
        model_client=model_client,
        system_message=matcher_role,
        model_client_stream=False,
    )

    # Create the critic agent.
    critic = AssistantAgent(
        name="critic",
        model_client=model_client,
        system_message=critic_role,
        model_client_stream=False,
    )

    # Termination condition.
    termination = TextMentionTermination("APPROVE", sources=["critic"])

    # Chain the assistant and critic agents using RoundRobinGroupChat.
    group_chat = RoundRobinGroupChat([matcher, critic], termination_condition=termination)

    return group_chat


async def get_history(history_path: str) -> list[dict[str, Any]]:
    """Get chat history from file."""
    if not os.path.exists(history_path):
        return []
    async with aiofiles.open(history_path, "r") as file:
        return json.loads(await file.read())
