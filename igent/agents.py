"""Agentic pair setup and configuration."""

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from dotenv import load_dotenv

from igent.models import get_model_client
from igent.tools import fetch_incentives_tool, save_json_tool

load_dotenv(override=True)


async def get_agents(
    model: str,
    stream: bool = False,
    matcher_prompt: str | None = None,
    critic_prompt: str | None = None,
) -> RoundRobinGroupChat:
    """Initialize and configure a group chat with matcher and optionally critic agents."""
    model_client = await get_model_client(model)

    agents = []

    if matcher_prompt is not None:
        matcher = AssistantAgent(
            name="matcher",
            model_client=model_client,
            system_message=matcher_prompt,
            tools=[fetch_incentives_tool, save_json_tool],
            model_client_stream=stream,
            reflect_on_tool_use=True,
        )
        agents.append(matcher)

    if critic_prompt is not None:
        critic = AssistantAgent(
            name="critic",
            model_client=model_client,
            system_message=critic_prompt,
            tools=[save_json_tool],
            model_client_stream=stream,
            reflect_on_tool_use=True,
        )
        agents.append(critic)

    if not agents:
        raise ValueError("Please provide at least one prompt")

    if critic_prompt is not None and matcher_prompt is not None:
        terminations = TextMentionTermination(
            "APPROVE", sources=[critic.name]
        ) | MaxMessageTermination(max_messages=5)
    else:
        terminations = MaxMessageTermination(max_messages=1)

    group_chat = RoundRobinGroupChat(
        agents,
        termination_condition=terminations,
    )

    return group_chat
