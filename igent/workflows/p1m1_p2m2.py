import time
from pathlib import Path

from igent.agents import get_agents
from igent.logging_config import logger
from igent.prompts import load_prompts
from igent.tools.read_json import read_json
from igent.tools.update_supplier_capacity import update_supplier_capacity
from igent.utils import (
    EXECUTION_TIMES_CSV,
    MAX_ITEMS,
    init_csv_file,
    process_pair,
    update_execution_times,
)


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
    """Run the workflow for processing registrations with (matcher1) -> (matcher2) configuration."""
    stats_file = Path(stats_file)
    stats_file = stats_file.parent / f"{business_line}_{model}_{stats_file.name}"
    matches_file = Path(matches_file)
    matches_file = matches_file.parent / f"{business_line}_{model}_{matches_file.name}"
    pos_file = Path(pos_file)
    pos_file = pos_file.parent / f"{business_line}_{model}_{pos_file.name}"

    init_csv_file(
        stats_file=stats_file,
        columns=["registration_id", "matcher1_time_seconds", "matcher2_time_seconds"],
    )

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

        # Matcher 1
        matcher1 = await get_agents(
            model=model,
            stream=stream,
            prompts={
                "matcher1": prompts["a_matcher"],
            },
        )
        message1 = (
            f"Match based on instructions in system prompt.\n"
            f"SAVE the output to '{matches_file}' using save_json_tool.\n"
            f"REGISTRATION: ```{[registration]}```\n"
            f"OFFERS: ```{offers}```\n"
        )
        start_time = time.time()
        success1 = await process_pair(
            pair=matcher1,
            message=message1,
            registration_id=registration_id,
            pair_name="Matcher 1",
            output_file=matches_file,
            logger=logger,
        )
        matcher1_time = time.time() - start_time
        logger.info("Matcher 1 execution time: %.3f seconds", matcher1_time)

        # Save Matcher 1 time
        update_execution_times(
            registration_id, matcher1_time=matcher1_time, stats_file=stats_file
        )

        if not success1:
            logger.warning("Matcher 1 failed for registration %s. Skipping.", i)
            continue

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

        # Matcher 2
        matcher2 = await get_agents(
            model=model,
            stream=stream,
            prompts={
                "matcher2": prompts["b_matcher"],
            },
        )
        filtered_match = next(
            (m for m in matches if m["registration_id"] == registration_id), None
        )
        if not filtered_match:
            logger.warning("No match found for registration ID: %s", registration_id)
            continue
        message2 = (
            f"Enrich matches with pricing and subsidies:\n"
            f"SAVE the output to '{pos_file}' using save_json_tool.\n"
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
            pair=matcher2,
            message=message2,
            registration_id=registration_id,
            pair_name="Matcher 2",
            output_file=pos_file,
            logger=logger,
        )
        matcher2_time = time.time() - start_time
        logger.info("Matcher 2 execution time: %.3f seconds", matcher2_time)

        # Update with Matcher 2 time
        update_execution_times(
            registration_id, matcher2_time=matcher2_time, stats_file=stats_file
        )

        if not success2:
            logger.warning("Matcher 2 failed for registration %s. Continuing.", i)

    logger.info("Processed %s registrations successfully.", max_items)
