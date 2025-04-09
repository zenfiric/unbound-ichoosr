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
    configuration: str = "p1m1c1_p2m2c2",
):
    """Run the workflow for processing registrations with (matcher1-critic1) -> (matcher2-critic2) configuration."""
    # Add configuration prefix to file paths
    stats_file = Path(stats_file)
    stats_file = (
        stats_file.parent / f"{configuration}_{business_line}_{model}_{stats_file.name}"
    )
    matches_file = Path(matches_file)
    matches_file = (
        matches_file.parent
        / f"{configuration}_{business_line}_{model}_{matches_file.name}"
    )
    pos_file = Path(pos_file)
    pos_file = (
        pos_file.parent / f"{configuration}_{business_line}_{model}_{pos_file.name}"
    )

    init_csv_file(
        stats_file=stats_file,
        columns=["registration_id", "pair1_time_seconds", "pair2_time_seconds"],
    )

    prompts = await load_prompts(
        business_line
    )  # No variant needed for this configuration
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

        # Pair 1: matcher1 and critic1
        pair1 = await get_agents(
            model=model,
            stream=stream,
            prompts={
                "matcher1": prompts["a_matcher"],
                "critic1": prompts["a_critic"],
            },
        )
        message1 = (
            f"Matcher1: Match based on instructions in system prompt.\n"
            f"SAVE the output to '{matches_file}' using save_json_tool.\n"
            f"REGISTRATION: ```{[registration]}```\n"
            f"OFFERS: ```{offers}```\n"
            f"Critic1: Review Matcher1's output and say 'APPROVE' if acceptable.\n"
        )
        start_time = time.time()
        success1 = await process_pair(
            pair=pair1,
            message=message1,
            registration_id=registration_id,
            pair_name="Pair 1 (Matcher1-Critic1)",
            output_file=matches_file,
            logger=logger,
        )
        pair1_time = time.time() - start_time
        logger.info("Pair 1 execution time: %.3f seconds", pair1_time)

        # Save Pair 1 time
        update_execution_times(
            registration_id, pair1_time=pair1_time, stats_file=stats_file
        )

        if not success1:
            logger.warning("Pair 1 failed for registration %s. Skipping.", i)
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

        # Pair 2: matcher2 and critic2
        pair2 = await get_agents(
            model=model,
            stream=stream,
            prompts={
                "matcher2": prompts["b_matcher"],
                "critic2": prompts["b_critic"],
            },
        )
        filtered_match = next(
            (
                m
                for m in matches
                if m.get("registration_id") == registration_id
                or m.get("RegistrationNumber") == registration_id
            ),
            None,
        )
        if not filtered_match:
            logger.warning("No match found for registration ID: %s", registration_id)
            continue
        message2 = (
            f"Matcher2: Enrich matches with pricing and subsidies:\n"
            f"SAVE the output to '{pos_file}' using save_json_tool.\n"
            f"MATCHES: ```{[filtered_match]}```\n"
            f"OFFERS: ```{offers}```\n"
            f"Critic2: Review Matcher2's output and say 'APPROVE' if acceptable.\n"
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
            pair_name="Pair 2 (Matcher2-Critic2)",
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
