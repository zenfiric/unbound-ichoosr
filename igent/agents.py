"""Agentic pair setup and configuration."""

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from dotenv import load_dotenv

from igent.models import get_model_client
from igent.tools import fetch_incentives_tool, save_json_tool

load_dotenv(override=True)


async def get_agents(
    model: str, stream: bool = False, prompts: dict = None
) -> RoundRobinGroupChat:
    """Initialize and configure a group chat with agents based on provided prompts."""
    if not prompts or not isinstance(prompts, dict):
        raise ValueError("Prompts must be a non-empty dictionary with agent prompts")

    model_client = await get_model_client(model)

    agents = []
    has_critic = False
    matcher_sources = []

    # Create agents based on prompts dictionary
    for agent_name, prompt in prompts.items():
        if not prompt:
            continue

        tools = [save_json_tool]
        if "matcher2" in agent_name:
            tools.append(fetch_incentives_tool)

        # Append instruction to say "APPROVE" when done
        updated_prompt = (
            f"{prompt}\n\nWhen you have completed your task and saved the output, "
            f"say 'APPROVE' to indicate completion."
        )

        agent = AssistantAgent(
            name=agent_name,
            model_client=model_client,
            system_message=updated_prompt,
            tools=tools,
            model_client_stream=stream,
            reflect_on_tool_use=True,
        )
        agents.append(agent)
        if "critic" in agent_name.lower():
            has_critic = True
        elif "matcher" in agent_name.lower():
            matcher_sources.append(agent_name)

    if not agents:
        raise ValueError("No valid agents created from prompts")

    # Define termination condition
    if has_critic:
        if "critic1" in prompts and "critic2" in prompts:
            terminations = (
                TextMentionTermination("APPROVE", sources=["critic1"])
                & TextMentionTermination("APPROVE", sources=["critic2"])
                & MaxMessageTermination(max_messages=10)
            )
        elif "critic1" in prompts:
            terminations = TextMentionTermination(
                "APPROVE", sources=["critic1"]
            ) | MaxMessageTermination(max_messages=10)
        elif "critic2" in prompts:
            terminations = TextMentionTermination(
                "APPROVE", sources=["critic2"]
            ) | MaxMessageTermination(max_messages=10)
        else:
            # Single critic (e.g., "critic" for one_critic variant)
            critic_source = next(
                (name for name in prompts if "critic" in name.lower()), None
            )
            terminations = TextMentionTermination(
                "APPROVE", sources=[critic_source]
            ) | MaxMessageTermination(max_messages=10)
    else:
        # No critics: terminate when all matchers say "APPROVE"
        if len(matcher_sources) > 1:
            terminations = (
                TextMentionTermination("APPROVE", sources=[matcher_sources[0]])
                & TextMentionTermination("APPROVE", sources=[matcher_sources[1]])
                & MaxMessageTermination(max_messages=10)
            )
        else:
            terminations = TextMentionTermination(
                "APPROVE", sources=matcher_sources
            ) | MaxMessageTermination(max_messages=10)

    group_chat = RoundRobinGroupChat(
        agents,
        termination_condition=terminations,
    )

    return group_chat
