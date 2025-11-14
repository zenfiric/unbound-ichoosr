import time

from igent.agents import get_agents
from igent.logging_config import logger
from igent.prompts import load_prompts
from igent.tools.capacity_tracker import update_supplier_capacity
from igent.tools.read_json import read_json
from igent.utils import (
    EXECUTION_TIMES_CSV,
    MAX_ITEMS,
    construct_file_path,
    init_csv,
    process_pair,
    update_json_list,
    update_runtime,
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
    stats_file = construct_file_path(stats_file, configuration, business_line, model)
    matches_file = construct_file_path(
        matches_file, configuration, business_line, model
    )
    pos_file = construct_file_path(pos_file, configuration, business_line, model)

    init_csv(
        filepath=stats_file,
        columns=[
            "registration_id",
            "matcher1_critic_time_seconds",
            "matcher2_time_seconds",
        ],
    )

    prompts = await load_prompts(business_line, variant="one_critic_no_mock")
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
        run_id = registration.get("RegistrationNumber", "unknown")
        logger.info("Processing registration %s/%s (ID: %s)", i, max_items, run_id)

        # Phase 1: Matcher1 and Critic
        group1 = await get_agents(
            model=model,
            stream=stream,
            prompts={
                "matcher1": prompts["a_matcher"],
                "critic": prompts["critic"],
            },
        )
        message1 = (
            f"Matcher1: Match based on instructions in system prompt.\n"
            f"REGISTRATION: ```{[registration]}```\n"
            f"OFFERS: ```{offers}```\n"
            f"Critic: Review Matcher1's output and say 'APPROVE' if acceptable.\n"
        )
        start_time = time.time()
        result1 = await process_pair(
            pair=group1,
            message=message1,
            run_id=run_id,
            pair_name="Matcher1-Critic",
            logger=logger,
        )
        t_matcher1_critic = time.time() - start_time
        logger.info("Matcher1-Critic execution time: %.3f seconds", t_matcher1_critic)

        if not result1 or not result1["success"]:
            logger.warning("Matcher1-Critic failed for registration %s. Skipping.", i)
            continue

        update_json_list(matches_file, result1["json_output"], logger)

        matches = await read_json(matches_file)
        logger.debug("Current match for update: %s", matches)
        try:
            result_capacity = await update_supplier_capacity(matches, offers_file)
            logger.info("Capacity update: %s", result_capacity)
            offers = await read_json(offers_file)
            logger.debug("Updated offers: %s", offers)
        except ValueError as e:
            logger.error("Error updating capacity: %s", e)
            continue

        # Phase 2: Matcher2
        group2 = await get_agents(
            model=model,
            stream=stream,
            prompts={
                "matcher2": prompts["b_matcher"],
            },
        )
        filtered_match = next(
            (
                m
                for m in matches
                if m.get("registration_id") == run_id
                or m.get("RegistrationNumber") == run_id
            ),
            None,
        )
        if not filtered_match:
            logger.warning("No match found for registration ID: %s", run_id)
            continue
        message2 = (
            f"Matcher2: Enrich matches with pricing and subsidies:\n"
            f"MATCHES: ```{[filtered_match]}```\n"
            f"OFFERS: ```{offers}```\n"
        )
        message2 += (
            f"INCENTIVES: ```{incentives}```\n"
            if incentives
            else "INCENTIVES: Use fetch_incentives_tool to fetch incentives based on zip code.\n"
        )

        start_time = time.time()
        result2 = await process_pair(
            pair=group2,
            message=message2,
            run_id=run_id,
            pair_name="Matcher2",
            logger=logger,
        )
        t_matcher2 = time.time() - start_time
        logger.info("Matcher2 execution time: %.3f seconds", t_matcher2)

        if not result2 or not result2["success"]:
            logger.warning("Matcher2 failed for registration %s. Continuing.", i)
            continue

        update_json_list(pos_file, result2["json_output"], logger)
        update_runtime(
            run_id,
            t_matcher1_critic=t_matcher1_critic,
            t_matcher2=t_matcher2,
            filepath=stats_file,
        )

    logger.info("Processed %s registrations successfully.", max_items)
