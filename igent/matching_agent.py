import json
import os
from typing import Any

import aiofiles
import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.models import ChatCompletionClient
from dotenv import load_dotenv

from igent.tools import read_json_tool, read_csv_tool

load_dotenv(override=True)

# General context and rules
general_context = """
<general_context>
iChoosr helps match potential customers with vetted suppliers on a large scale. They help them choose sustainable energy solutions including solar panels, home batteries, heat pumps, and renewable energy tariffs. They operate globally in Belgium, Japan, the Netherlands, the United Kingdom, the United States, and more. They try to balance both sides of the transaction between the registrant and suppliers by making the process efficient for both parties. Generally, the process of matching the registration to suppliers and the eligible subsidies looks like this:
- Step 1: Match the registration to the correct supplier based on <matching_rules>
- Step 2: Validate the output of the matching expert based on <matching_rules>.
- Step 3: Enrich the matching output with the right product price and select the eligible subsidies that apply for this registration based on the <subsidy_rules>.
- Step 4: Validate the output of the subsidy and price expert based on the <subsidy_rules>.
- Step 5: Generate the final JSON based on the validated matching outcome.
</general_context>
"""

matcher_role = """
<role_matching_expert>
You are a matching expert responsible for efficiently matching registrations with suppliers based on their ZIP code and requested sustainable energy solutions.
Your goal is to match the registration to the correct supplier based on <matching_rules>.

The data from a registration point of view will come from the registration data and the supplier data will come from the auction outcomes dataset. Your task is to process registrations, query the supplier offer dataset, and return the best possible match while considering registration and supplier location, and supplier capacity constraints. Ensure you always adhere to the matching rules as defined in <matching_rules>. 

Output your matches in JSON format as defined in <matching_example>:
  [{
    "registration_id": <registration_id>,
    "campaign_id": <campaign_id>,
    "supplier_id": <supplier_id>,
    "panel_name": <panel_name>,
    "panel_capacity": <panel_capacity>,
    "battery_name": <battery_name>,
    "battery_capacity": <battery_capacity>
  }]
</role_matching_expert>
<matching_rules>
Matching registrations to suppliers is a straightforward process. The aim is to ensure that a registration is matched to a supplier who has available capacity to fulfil the requirements of the registration, and who also services the same zip code as the registrant. An important point here is that suppliers have a maximum capacity. If the supplier capacity within the registrant’s zip code is met, then the registration should be matched with the next nearest supplier who has capacity to fulfil the requirements of the registration. The nearest supplier is defined by the zip code of the supplier and the registration address. When doing the matching, make sure to adhere to these matching rules:

- Registration address falls within the supplier's service area.
- The matched supplier has available capacity, as defined in the <capacity_database>.
- Registrations are distributed proportionally within overlapping suppliers' service areas; based on capacity and defined <distribution_rules>.
- The assigned supplier offers the product the registration needs (e.g. SP & BT).
</matching_rules>
<distribution_rules>
When assigning a registration that has multiple possible suppliers based on zip codes, you should: 
- Address Skew Consideration: Recognize that the connection between registration addresses and suppliers' service areas can skew distribution. Adjust allocations based on relatively (not absolute) distribute to ensure balanced distributions.
- Relative Distribution Measurement: Assess distribution by comparing each supplier's capacity to the number of registrations assigned, using the supplier capacity dataset. Based on this prioritise the relative distribution over the absolute distribution numbers. 
- Make sure to consistently check if the relatively distribution has changed or not. 
Example: If Supplier A can serve 100 registrations and Supplier B can serve 200, Supplier A should receive about 33% of registrations.
If Supplier A has 80 registrations and Supplier B has 100, Supplier A's relative assignment is 80%, and Supplier B's is 50%.
Despite fewer absolute registrations, Supplier A has a higher relative percentage. Thus, prioritize Supplier B when allocating to registrations in overlapping service areas.
</distribution_rules>
"""

critic_role = """
<role_matching_critic>
You are an expert in examining and validating the output of the <role_matching_expert> and you always ensure that every match between registration and supplier is correct and meets the <matching_rules> consistently. The output data of the <role_matching_expert> is always based on the <matching_rules> and you will receive it in JSON format. Your task is to validate if the output data is correct based on the defined rules in <matching_rules>.

Your task is to validate the output data of the <role_matching_expert>, guaranteeing the best possible match while considering registration and supplier location, and supplier capacity constraints. You can use the provided tools to read the original data files for verification.

Follow these steps to validate the matching:
1. Check if the output data is correct based on the <matching_rules>.
2a. If data is correct and distribution is proportional per <distribution_rules>, respond with 'APPROVE' to terminate.
2b. If data is incorrect or distribution is uneven, return feedback to the <role_matching_expert> highlighting the reason why the matching is wrong and how to improve it. Continue this loop until the data is correct, or after 5 iterations, submit ‘review request from a human’.

Output your feedback clearly, and if approving, restate the validated JSON.
</role_matching_critic>
<matching_rules>
Matching registrations to suppliers is a straightforward process. The aim is to ensure that a registration is matched to a supplier who has available capacity to fulfil the requirements of the registration, and who also services the same zip code as the registrant. An important point here is that suppliers have a maximum capacity. If the supplier capacity within the registrant’s zip code is met, then the registration should be matched with the next nearest supplier who has capacity to fulfil the requirements of the registration. The nearest supplier is defined by the zip code of the supplier and the registration address. When doing the matching, make sure to adhere to these matching rules:

- Registration address falls within the supplier's service area.
- The matched supplier has available capacity, as defined in the <capacity_database>.
- Registrations are distributed proportionally within overlapping suppliers' service areas; based on capacity and defined <distribution_rules>.
- The assigned supplier offers the product the registration needs (e.g. SP & BT).
</matching_rules>
<distribution_rules>
When assigning a registration that has multiple possible suppliers based on zip codes, you should: 
- Address Skew Consideration: Recognize that the connection between registration addresses and suppliers' service areas can skew distribution. Adjust allocations based on relatively (not absolute) distribute to ensure balanced distributions.
- Relative Distribution Measurement: Assess distribution by comparing each supplier's capacity to the number of registrations assigned, using the supplier capacity dataset. Based on this prioritise the relative distribution over the absolute distribution numbers. 
- Make sure to consistently check if the relatively distribution has changed or not. 
Example: If Supplier A can serve 100 registrations and Supplier B can serve 200, Supplier A should receive about 33% of registrations.
If Supplier A has 80 registrations and Supplier B has 100, Supplier A's relative assignment is 80%, and Supplier B's is 50%.
Despite fewer absolute registrations, Supplier A has a higher relative percentage. Thus, prioritize Supplier B when allocating to registrations in overlapping service areas.
</distribution_rules>
"""
async def get_agents(
    state_path: str,
    matcher_role: str = (
        "You are a matching assistant. Your task is to load data from provided files "
        "(using read_json, read_csv, or read_xlsx tools) and propose matches between records "
        "based on common fields like zip codes, sizes, or amounts. Present your matches clearly "
        "and adjust them based on feedback from the critic."
    ),
    critic_role: str = (
        "You are a critic. Evaluate the proposed matches for accuracy and relevance. "
        "Provide constructive feedback on what’s wrong or missing. Respond with 'APPROVE' "
        "if the matches are satisfactory."
    )
) -> RoundRobinGroupChat:
    """Get the assistant agent, load state from file."""
    async with aiofiles.open(state_path, "r") as file:
            content = await file.read()
            content = os.path.expandvars(content)
            model_config = yaml.safe_load(content)
    model_client = ChatCompletionClient.load_component(model_config)

    # Create the matcher agent with tools
    matcher = AssistantAgent(
        name="matcher",
        model_client=model_client,
        system_message=general_context + matcher_role,
        tools=[read_json_tool, read_csv_tool],
        model_client_stream=False,
    )

    # Create the critic agent with tools
    critic = AssistantAgent(
        name="critic",
        model_client=model_client,
        system_message=general_context + critic_role,
        tools=[read_json_tool, read_csv_tool],
        model_client_stream=False,
    )

    # Termination conditions: APPROVE or max 5 rounds (10 messages, since each round has 2 messages)
    termination = TextMentionTermination("APPROVE", sources=["critic"]) | MaxMessageTermination(max_messages=10)

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
