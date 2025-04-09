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
    configuration: str = "p1m1m2c",
):
    """Run the workflow for processing registrations with (matcher1-critic-matcher2) configuration."""
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
        columns=["registration_id", "group_time_seconds"],
    )

    prompts = await load_prompts(business_line, variant="one_critic")
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

        # Single group with matcher1, critic, and matcher2
        group = await get_agents(
            model=model,
            stream=stream,
            prompts={
                "matcher1": prompts["a_matcher"],
                "critic": prompts["critic"],  # Single critic from one_critic variant
                "matcher2": prompts["b_matcher"],
            },
        )

        # Message for the entire group
        message = (
            f"Matcher1: Match based on instructions in system prompt.\n"
            f"SAVE the output to '{matches_file}' using save_json_tool.\n"
            f"REGISTRATION: ```{[registration]}```\n"
            f"OFFERS: ```{offers}```\n"
            f"Critic: Review Matcher1's output and say 'APPROVE' if acceptable.\n"
            f"Matcher2: After Critic approves, enrich matches with pricing and subsidies.\n"
            f"SAVE the enriched output to '{pos_file}' using save_json_tool.\n"
            f"OFFERS (updated after capacity): ```{offers}```\n"
        )
        message += (
            f"INCENTIVES: ```{incentives}```\n"
            if incentives
            else "INCENTIVES: Use fetch_incentives_tool to fetch incentives based on zip code.\n"
        )

        start_time = time.time()
        success = await process_pair(
            pair=group,
            message=message,
            registration_id=registration_id,
            pair_name="Matcher1-Critic-Matcher2 Group",
            output_file=pos_file,  # Final output goes to pos_file
            logger=logger,
        )
        group_time = time.time() - start_time
        logger.info("Group execution time: %.3f seconds", group_time)

        update_execution_times(
            registration_id, group_time=group_time, stats_file=stats_file
        )

        if not success:
            logger.warning("Group processing failed for registration %s. Skipping.", i)
            continue

        # Update supplier capacity after matcher1 and critic but before matcher2's output
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

    logger.info("Processed %s registrations successfully.", max_items)
