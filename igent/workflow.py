from igent.agents import get_agents
from igent.prompts import load_prompts
from igent.tools.read_json import read_json
from igent.tools.update_supplier_capacity import update_supplier_capacity
from igent.utils import process_pair

# Constants
MAX_ITEMS = 10


async def run_workflow(
    model: str,
    business_line: str = "sbus",
    registrations_file: str = "registrations.json",
    offers_file: str = "offers.json",
    incentives_file: str = "incentives.json",
    matches_file: str = "matches.json",
    final_matches_file: str = "final_matches.json",
):
    prompts = await load_prompts(business_line)
    registrations = await read_json(registrations_file)
    if not isinstance(registrations, list):
        print("Error: Registrations file must contain a list.")
        return

    max_items = min(MAX_ITEMS, len(registrations))
    if not max_items:
        print("No registrations to process.")
        return

    print(f"Processing {max_items} registrations...")
    offers = await read_json(offers_file)
    incentives = await read_json(incentives_file)

    for i, registration in enumerate(registrations[:max_items], 1):
        registration_id = registration.get("registration_id", "unknown")
        print(f"\nProcessing registration {i}/{max_items} (ID: {registration_id})")

        # Pair 1: Matcher + Critic
        pair1 = await get_agents(
            model=model,
            matcher_prompt=prompts["a_matcher"],
            critic_prompt=prompts["a_critic"],
        )
        message1 = (
            f"Match registrations to suppliers:\n"
            f"REGISTRATION: ```{[registration]}```\n"
            f"OFFERS: ```{offers}```\n"
            f"On approval, SAVE the output to '{matches_file}' using save_json_tool."
        )
        success1 = await process_pair(
            pair1, message1, registration_id, "Pair 1", matches_file
        )
        if not success1:
            print(f"Pair 1 failed for registration {i}. Skipping.")
            continue

        # Update supplier capacity after Pair 1 approval
        matches = await read_json(matches_file)
        print(f"Current match for update: {matches}")  # Debug
        try:
            result = await update_supplier_capacity(matches, offers_file)
            print(f"Capacity update: {result}")
            offers = await read_json(
                offers_file
            )  # Refresh offers with updated capacity
            print(f"Updated offers: {offers['SupplierOffers']}")  # Debug
        except ValueError as e:
            print(f"Error updating capacity: {e}")
            continue

        # Pair 2: Subsidy Matcher + Subsidy Critic
        pair2 = await get_agents(
            model=model,
            matcher_prompt=prompts["b_matcher"],
            critic_prompt=prompts["b_critic"],
        )
        message2 = (
            f"Enrich matches with pricing and subsidies:\n"
            f"MATCHES: ```{matches}```\n"
            f"OFFERS: ```{offers}```\n"
            f"INCENTIVES: ```{incentives}```\n"
            f"On approval, SAVE the output to '{final_matches_file}' using save_json_tool."
        )
        success2 = await process_pair(
            pair2, message2, registration_id, "Pair 2", final_matches_file
        )
        if not success2:
            print(f"Pair 2 failed for registration {i}. Continuing.")

    print(f"\nProcessed {max_items} registrations successfully.")
