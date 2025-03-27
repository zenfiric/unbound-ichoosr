import json
import os
from typing import Any

import aiofiles
import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.models import ChatCompletionClient
from dotenv import load_dotenv

from igent.tools import read_csv_tool, read_json_tool, save_json_tool

load_dotenv(override=True)


async def get_agents(
    config_path: str, matcher_prompt: str = None, critic_prompt: str = None
) -> RoundRobinGroupChat:
    """Initialize and configure a group chat with matcher and critic agents.

    Args:
        state_path (str): Path to the YAML configuration file containing model settings.
        matcher_prompt (str, optional): System message for the matcher agent. Defaults to None.
        critic_prompt (str, optional): System message for the critic agent. Defaults to None.

    Returns:
        RoundRobinGroupChat: A group chat with matcher and critic agents,
            with termination conditions (APPROVE from critic | max 10 messages).
    """
    async with aiofiles.open(config_path, "r") as file:
        content = await file.read()
        content = os.path.expandvars(content)
        model_config = yaml.safe_load(content)
    model_client = ChatCompletionClient.load_component(model_config)

    matcher = AssistantAgent(
        name="matcher",
        model_client=model_client,
        system_message=matcher_prompt,
        tools=[read_json_tool, read_csv_tool],
        model_client_stream=False,
        reflect_on_tool_use=True,
    )

    critic = AssistantAgent(
        name="critic",
        model_client=model_client,
        system_message=critic_prompt,
        tools=[read_json_tool, read_csv_tool, save_json_tool],
        model_client_stream=False,
        reflect_on_tool_use=True,
    )

    # Termination conditions: APPROVE or max 5 rounds (10 messages)
    termination = TextMentionTermination(
        "APPROVE", sources=["critic"]
    ) | MaxMessageTermination(max_messages=10)

    # Chain the agents
    group_chat = RoundRobinGroupChat(
        [matcher, critic],
        termination_condition=termination,
    )

    return group_chat


async def get_history(history_path: str) -> list[dict[str, Any]]:
    """Get chat history from file."""
    if not os.path.exists(history_path):
        return []
    async with aiofiles.open(history_path, "r") as file:
        return json.loads(await file.read())
