import logging

import colorlog

from igent.agents import get_agents
from igent.prompts import load_prompts
from igent.tools.read_json import read_json
from igent.tools.update_supplier_capacity import update_supplier_capacity
from igent.utils import process_pair

# Suppress autogen_core and httpx INFO logs
logging.getLogger("autogen_core").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Constants
MAX_ITEMS = 10

# Configure colorlog
handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)s:%(message)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
)
logger = logging.getLogger("workflow")
logger.addHandler(handler)
logger.setLevel(logging.INFO)


async def run_workflow(
    model: str,
    business_line: str = "sbus",
    registrations_file: str = "registrations.json",
    offers_file: str = "offers.json",
    incentives_file: str | None = None,
    matches_file: str = "matches.json",
    pos_file: str = "final_matches.json",
):
    prompts = await load_prompts(business_line)
    registrations = await read_json(registrations_file)
    if not isinstance(registrations, list):
        logger.error("Registrations file must contain a list.")
        return

    max_items = min(MAX_ITEMS, len(registrations))
    if not max_items:
        logger.warning("No registrations to process.")
        return

    logger.info("Processing %s registrations...", max_items)
    offers = await read_json(offers_file)
    incentives = await read_json(incentives_file) if incentives_file else None

    for i, registration in enumerate(registrations[:max_items], 1):
        registration_id = registration.get("registration_id", "unknown")
        logger.info(
            "Processing registration %s/%s (ID: %s)", i, max_items, registration_id
        )

        # Pair 1: Matcher + Critic
        pair1 = await get_agents(
            model=model,
            matcher_prompt=prompts["a_matcher"],
            critic_prompt=prompts["a_critic"],
        )
        message1 = (
            f"Match based on instructions in system prompt.\n"
            f"On approval, SAVE the output to '{matches_file}' using save_json_tool.\n"
            f"REGISTRATION: ```{[registration]}```\n"
            f"OFFERS: ```{offers}```\n"
        )
        success1 = await process_pair(
            pair1, message1, registration_id, "Pair 1", matches_file
        )
        if not success1:
            logger.warning("Pair 1 failed for registration %s. Skipping.", i)
            continue

        # Update supplier capacity after Pair 1 approval
        matches = await read_json(matches_file)
        logger.debug("Current match for update: %s", matches)
        try:
            result = await update_supplier_capacity(matches, offers_file)
            logger.info("Capacity update: %s", result)
            offers = await read_json(
                offers_file
            )  # Refresh offers with updated capacity
            logger.debug("Updated offers: %s", offers["SupplierOffers"])
        except ValueError as e:
            logger.error("Error updating capacity: %s", e)
            continue

        # Pair 2: Subsidy Matcher + Subsidy Critic
        pair2 = await get_agents(
            model=model,
            matcher_prompt=prompts["b_matcher"],
            critic_prompt=prompts["b_critic"],
        )
        message2 = (
            f"Enrich matches with pricing and subsidies:\n"
            f"On approval, SAVE the output to '{pos_file}' using save_json_tool.\n"
            f"MATCHES: ```{matches}```\n"
            f"OFFERS: ```{offers}```\n"
            f"INCENTIVES: ```{incentives}```\n"
            if incentives
            else ""
        )
        success2 = await process_pair(
            pair2, message2, registration_id, "Pair 2", pos_file
        )
        if not success2:
            logger.warning("Pair 2 failed for registration %s. Continuing.", i)

    logger.info("Processed %s registrations successfully.", max_items)
