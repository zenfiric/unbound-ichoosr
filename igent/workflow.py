import os
import time
from pathlib import Path

import pandas as pd

from igent.agents import get_agents
from igent.logging_config import logger
from igent.prompts import load_prompts
from igent.tools.read_json import read_json
from igent.tools.update_supplier_capacity import update_supplier_capacity
from igent.utils import process_pair

# Constants
MAX_ITEMS = 10

# CSV file path
EXECUTION_TIMES_CSV = "execution_times.csv"


def init_csv_file(stats_file: str = EXECUTION_TIMES_CSV):
    """Initialize CSV file with headers if it doesn't exist"""
    if not os.path.exists(stats_file):
        df = pd.DataFrame(
            columns=["registration_id", "pair1_time_seconds", "pair2_time_seconds"]
        )
        df.to_csv(stats_file, index=False)


def update_execution_times(
    registration_id: str,
    pair1_time: float = None,
    pair2_time: float = None,
    stats_file: str = EXECUTION_TIMES_CSV,
):
    """Update execution times in CSV file using pandas"""
    # Read existing data
    df = pd.read_csv(stats_file)

    # Check if registration_id exists
    if registration_id in df["registration_id"].values:
        # Update existing row
        if pair1_time is not None:
            df.loc[df["registration_id"] == registration_id, "pair1_time_seconds"] = (
                f"{pair1_time:.3f}"
            )
        if pair2_time is not None:
            df.loc[df["registration_id"] == registration_id, "pair2_time_seconds"] = (
                f"{pair2_time:.3f}"
            )
    else:
        # Add new row
        new_row = {
            "registration_id": registration_id,
            "pair1_time_seconds": (
                f"{pair1_time:.3f}" if pair1_time is not None else None
            ),
            "pair2_time_seconds": (
                f"{pair2_time:.3f}" if pair2_time is not None else None
            ),
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # Save updated dataframe
    df.to_csv(stats_file, index=False)


async def run_workflow(
    model: str,
    stream: bool = False,
    business_line: str = "sbus",
    registrations_file: str = "registrations.json",
    offers_file: str = "offers.json",
    incentives_file: str | None = None,
    matches_file: str = "matches.json",
    pos_file: str = "pos.json",
    max_items: int = MAX_ITEMS,
    stats_file: str = EXECUTION_TIMES_CSV,
):
    stats_file = Path(stats_file)
    stats_file = stats_file.parent / f"{business_line}_{model}_{stats_file.name}"
    init_csv_file(stats_file=stats_file)

    prompts = await load_prompts(business_line)
    registrations = await read_json(registrations_file)
    if not isinstance(registrations, list):
        logger.error("Registrations file must contain a list.")
        return

    max_items = min(max_items, len(registrations))
    if not max_items:
        logger.warning("No registrations to process.")
        return

    logger.info("Processing %s registrations...", max_items)
    offers = await read_json(offers_file)
    incentives = await read_json(incentives_file) if incentives_file else None

    for i, registration in enumerate(registrations[:max_items], 1):
        registration_id = registration.get("RegistrationNumber", "unknown")
        logger.info(
            "Processing registration %s/%s (ID: %s)", i, max_items, registration_id
        )

        # Pair 1: Matcher + Critic with timing
        pair1 = await get_agents(
            model=model,
            stream=stream,
            matcher_prompt=prompts["a_matcher"],
            critic_prompt=prompts["a_critic"],
        )
        message1 = (
            f"Match based on instructions in system prompt.\n"
            f"On approval, SAVE the output to '{matches_file}' using save_json_tool.\n"
            f"REGISTRATION: ```{[registration]}```\n"
            f"OFFERS: ```{offers}```\n"
        )
        start_time = time.time()
        success1 = await process_pair(
            pair=pair1,
            message=message1,
            registration_id=registration_id,
            pair_name="Pair 1",
            output_file=matches_file,
            logger=logger,
        )
        pair1_time = time.time() - start_time
        logger.info("Pair 1 execution time: %.3f seconds", pair1_time)

        # Save Pair 1 time
        update_execution_times(registration_id, pair1_time, stats_file=stats_file)

        if not success1:
            logger.warning("Pair 1 failed for registration %s. Skipping.", i)
            continue

        # Update supplier capacity after Pair 1 approval
        matches = await read_json(matches_file)
        logger.debug("Current match for update: %s", matches)
        try:
            result = await update_supplier_capacity(matches, offers_file)
            logger.info("Capacity update: %s", result)
            offers = await read_json(offers_file)
            logger.debug("Updated offers: %s", offers)
        except ValueError as e:
            logger.error("Error updating capacity: %s", e)
            continue

        # Pair 2: Subsidy Matcher + Subsidy Critic with timing
        pair2 = await get_agents(
            model=model,
            stream=stream,
            matcher_prompt=prompts["b_matcher"],
            critic_prompt=prompts["b_critic"],
        )
        filtered_match = next(
            (m for m in matches if m["registration_id"] == registration_id), None
        )
        if not filtered_match:
            logger.warning("No match found for registration ID: %s", registration_id)
            continue
        message2 = (
            f"Enrich matches with pricing and subsidies:\n"
            f"On approval, SAVE the output to '{pos_file}' using save_json_tool.\n"
            f"MATCHES: ```{[filtered_match]}```\n"
            f"OFFERS: ```{offers}```\n"
        )
        message2 += (
            f"INCENTIVES: ```{incentives}```\n"
            if incentives
            else "INCENTIVES: Use fetch_incentives_tool to fetch incentives based on zip code.\n"
        )

        start_time = time.time()
        success2 = await process_pair(
            pair=pair2,
            message=message2,
            registration_id=registration_id,
            pair_name="Pair 2",
            output_file=pos_file,
            logger=logger,
        )
        pair2_time = time.time() - start_time
        logger.info("Pair 2 execution time: %.3f seconds", pair2_time)

        # Update with Pair 2 time
        update_execution_times(
            registration_id, pair2_time=pair2_time, stats_file=stats_file
        )

        if not success2:
            logger.warning("Pair 2 failed for registration %s. Continuing.", i)

    logger.info("Processed %s registrations successfully.", max_items)
