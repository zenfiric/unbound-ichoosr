"""Agentic pair setup and configuration."""

from typing import Literal

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from dotenv import load_dotenv

from igent.models import get_model_client

load_dotenv(override=True)


async def get_teams(
    model: Literal["openai", "azure"],
    n_teams: Literal[1, 2] = 1,
    matcher1_prompt: str | None = None,
    matcher1_tools: list[str] | None = None,
    matcher2_prompt: str | None = None,
    matcher2_tools: list[str] | None = None,
    critic1_prompt: str | None = None,
    critic1_tools: list[str] | None = None,
    critic2_prompt: str | None = None,
    critic2_tools: list[str] | None = None,
    streaming: bool = False,
) -> list[RoundRobinGroupChat]:
    """
    Create a workflow of RoundRobinGroupChat teams based on provided prompts and tools.

    Options:
        1. g=2: (matcher1-critic1) -> (matcher2-critic2)
        2. g=2: (matcher1) -> (matcher2)
        3. g=1: (matcher1-critic1-matcher2-critic2)
        4. g=1: (matcher1-critic-matcher2)
    """
    teams = []
    has_matcher1 = bool(matcher1_prompt)
    has_matcher2 = bool(matcher2_prompt)
    has_critic1 = bool(critic1_prompt)
    has_critic2 = bool(critic2_prompt)

    if not any([has_matcher1, has_matcher2, has_critic1, has_critic2]):
        raise ValueError("At least one prompt must be provided")

    if n_teams not in [1, 2]:
        raise ValueError("n_teams must be 1 or 2")

    # Case 1: g=2: (matcher1-critic1) -> (matcher2-critic2)
    if n_teams == 2 and has_matcher1 and has_matcher2 and has_critic1 and has_critic2:
        teams.extend(
            [
                await get_agents(
                    model=model,
                    matcher1_prompt=matcher1_prompt,
                    matcher1_tools=matcher1_tools,
                    critic1_prompt=critic1_prompt,
                    critic1_tools=critic1_tools,
                    streaming=streaming,
                ),
                await get_agents(
                    model=model,
                    matcher2_prompt=matcher2_prompt,
                    matcher2_tools=matcher2_tools,
                    critic2_prompt=critic2_prompt,
                    critic2_tools=critic2_tools,
                    streaming=streaming,
                ),
            ]
        )

    # Case 2: g=2: (matcher1) -> (matcher2)
    elif (
        n_teams == 2
        and has_matcher1
        and has_matcher2
        and not has_critic1
        and not has_critic2
    ):
        teams.extend(
            [
                await get_agents(
                    model=model,
                    matcher1_prompt=matcher1_prompt,
                    matcher1_tools=matcher1_tools,
                    streaming=streaming,
                ),
                await get_agents(
                    model=model,
                    matcher2_prompt=matcher2_prompt,
                    matcher2_tools=matcher2_tools,
                    streaming=streaming,
                ),
            ]
        )

    # Case 3: g=1: (matcher1-critic1-matcher2-critic2)
    elif n_teams == 1 and has_matcher1 and has_matcher2 and has_critic1 and has_critic2:
        teams.append(
            await get_agents(
                model=model,
                matcher1_prompt=matcher1_prompt,
                matcher1_tools=matcher1_tools,
                matcher2_prompt=matcher2_prompt,
                matcher2_tools=matcher2_tools,
                critic1_prompt=critic1_prompt,
                critic1_tools=critic1_tools,
                critic2_prompt=critic2_prompt,
                critic2_tools=critic2_tools,
                streaming=streaming,
            )
        )

    # Case 4: g=1: (matcher1-critic-matcher2)
    elif (
        n_teams == 1
        and has_matcher1
        and has_matcher2
        and has_critic1
        and not has_critic2
    ):
        teams.append(
            await get_agents(
                model=model,
                matcher1_prompt=matcher1_prompt,
                matcher1_tools=matcher1_tools,
                matcher2_prompt=matcher2_prompt,
                matcher2_tools=matcher2_tools,
                critic1_prompt=critic1_prompt,
                critic1_tools=critic1_tools,
                streaming=streaming,
            )
        )

    # Fallback for unsupported configurations
    else:
        raise ValueError(
            f"Unsupported configuration: n_teams={n_teams}, "
            f"matchers={has_matcher1},{has_matcher2}, "
            f"critics={has_critic1},{has_critic2}"
        )

    return teams


async def get_agents(
    model: Literal["openai", "azure"],
    matcher1_prompt: str | None = None,
    matcher1_tools: list[str] | None = None,
    matcher2_prompt: str | None = None,
    matcher2_tools: list[str] | None = None,
    critic1_prompt: str | None = None,
    critic1_tools: list[str] | None = None,
    critic2_prompt: str | None = None,
    critic2_tools: list[str] | None = None,
    streaming: bool = False,
) -> RoundRobinGroupChat:
    """Create a group chat with specified agents and their respective tools."""
    model_client = await get_model_client(model)
    agents = []

    if matcher1_prompt:
        agents.append(
            AssistantAgent(
                name="matcher1",
                model_client=model_client,
                system_message=matcher1_prompt,
                tools=matcher1_tools or [],
                model_client_stream=streaming,
                reflect_on_tool_use=True,
            )
        )
    if critic1_prompt:
        agents.append(
            AssistantAgent(
                name="critic1",
                model_client=model_client,
                system_message=critic1_prompt,
                tools=critic1_tools or [],
                model_client_stream=streaming,
                reflect_on_tool_use=True,
            )
        )
    if matcher2_prompt:
        agents.append(
            AssistantAgent(
                name="matcher2",
                model_client=model_client,
                system_message=matcher2_prompt,
                tools=matcher2_tools or [],
                model_client_stream=streaming,
                reflect_on_tool_use=True,
            )
        )
    if critic2_prompt:
        agents.append(
            AssistantAgent(
                name="critic2",
                model_client=model_client,
                system_message=critic2_prompt,
                tools=critic2_tools or [],
                model_client_stream=streaming,
                reflect_on_tool_use=True,
            )
        )

    if not agents:
        raise ValueError("At least one agent required")

    critic_names = [agent.name for agent in agents if "critic" in agent.name]
    termination = (
        TextMentionTermination("APPROVE", sources=critic_names)
        | MaxMessageTermination(max_messages=5)
        if (critic1_prompt or critic2_prompt) and (matcher1_prompt or matcher2_prompt)
        else MaxMessageTermination(max_messages=1)
    )

    return RoundRobinGroupChat(agents, termination_condition=termination)
