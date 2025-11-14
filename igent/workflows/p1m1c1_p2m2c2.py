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

from .workflow import Workflow


class Matcher1Critic1Matcher2Critic2SequentialWorkflow(Workflow):
    """Workflow for (Matcher1-Critic1) -> (Matcher2-Critic2) configuration (p1m1c1_p2m2c2)."""

    def _get_csv_columns(self) -> list[str]:
        return ["registration_id", "pair1_time_seconds", "pair2_time_seconds"]

    async def _process_registration(
        self,
        run_id: str,
        registration: dict,
        offers: list[dict],
        incentives: list[dict] | None,
    ) -> list[dict] | None:
        # Pair 1: Matcher1 and Critic1
        pair1 = await get_agents(
            model=self.config.model,
            stream=self.config.stream,
            prompts={
                "matcher1": self.prompts["a_matcher"],
                "critic1": self.prompts["a_critic"],
            },
        )
        message1 = (
            "Matcher1: Match based on instructions in system prompt.\n"
            f"REGISTRATION: ```{[registration]}```\n"
            f"OFFERS: ```{offers}```\n"
            "Critic1: Review Matcher1's output and say 'APPROVE' if acceptable.\n"
        )
        start_time = time.time()
        result1 = await process_pair(
            pair=pair1,
            message=message1,
            run_id=run_id,
            pair_name="Pair 1 (Matcher1-Critic1)",
            logger=logger,
        )
        t_pair1 = time.time() - start_time
        logger.info("Pair 1 execution time: %.3f seconds", t_pair1)

        if not result1 or not result1["success"]:
            logger.warning("Pair 1 failed for registration %s. Skipping.", run_id)
            return None

        update_json_list(self.matches_file, result1["json_output"], logger)
        update_runtime(run_id, t_pair1=t_pair1, filepath=self.stats_file)

        matches = await read_json(self.matches_file)
        offers = await self._update_capacity(matches, run_id)
        if offers is None:
            return None

        # Pair 2: Matcher2 and Critic2
        pair2 = await get_agents(
            model=self.config.model,
            stream=self.config.stream,
            prompts={
                "matcher2": self.prompts["b_matcher"],
                "critic2": self.prompts["b_critic"],
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
            return None

        message2 = (
            "Matcher2: Enrich matches with pricing and subsidies:\n"
            f"MATCHES: ```{[filtered_match]}```\n"
            f"OFFERS: ```{offers}```\n"
            "Critic2: Review Matcher2's output and say 'APPROVE' if acceptable.\n"
        )
        message2 += (
            f"INCENTIVES: ```{incentives}```\n"
            if incentives
            else "INCENTIVES: Use fetch_incentives_tool to fetch incentives based on zip code.\n"
        )

        start_time = time.time()
        result2 = await process_pair(
            pair=pair2,
            message=message2,
            run_id=run_id,
            pair_name="Pair 2 (Matcher2-Critic2)",
            logger=logger,
        )
        t_pair2 = time.time() - start_time
        logger.info("Pair 2 execution time: %.3f seconds", t_pair2)

        if not result2 or not result2["success"]:
            logger.warning("Pair 2 failed for registration %s. Continuing.", run_id)
            return offers

        update_json_list(self.pos_file, result2["json_output"], logger)
        update_runtime(run_id, t_pair2=t_pair2, filepath=self.stats_file)
        return offers


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
    stats_file = construct_file_path(stats_file, configuration, business_line, model)
    matches_file = construct_file_path(
        matches_file, configuration, business_line, model
    )
    pos_file = construct_file_path(pos_file, configuration, business_line, model)

    init_csv(
        filepath=stats_file,
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
        run_id = registration.get("RegistrationNumber", "unknown")
        logger.info("Processing registration %s/%s (ID: %s)", i, max_items, run_id)

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
            f"REGISTRATION: ```{[registration]}```\n"
            f"OFFERS: ```{offers}```\n"
            f"Critic1: Review Matcher1's output and say 'APPROVE' if acceptable.\n"
        )
        start_time = time.time()
        result1 = await process_pair(
            pair=pair1,
            message=message1,
            run_id=run_id,
            pair_name="Pair 1 (Matcher1-Critic1)",
            logger=logger,
        )
        t_pair1 = time.time() - start_time
        logger.info("Pair 1 execution time: %.3f seconds", t_pair1)

        if not result1 or not result1["success"]:
            logger.warning("Pair 1 failed for registration %s. Skipping.", i)
            continue

        update_json_list(matches_file, result1["json_output"], logger)
        update_runtime(run_id, t_pair1=t_pair1, filepath=stats_file)

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
            f"Critic2: Review Matcher2's output and say 'APPROVE' if acceptable.\n"
        )
        message2 += (
            f"INCENTIVES: ```{incentives}```\n"
            if incentives
            else "INCENTIVES: Use fetch_incentives_tool to fetch incentives based on zip code.\n"
        )

        start_time = time.time()
        result2 = await process_pair(
            pair=pair2,
            message=message2,
            run_id=run_id,
            pair_name="Pair 2 (Matcher2-Critic2)",
            logger=logger,
        )
        t_pair2 = time.time() - start_time
        logger.info("Pair 2 execution time: %.3f seconds", t_pair2)

        if not result2 or not result2["success"]:
            logger.warning("Pair 2 failed for registration %s. Continuing.", i)
            continue

        update_json_list(pos_file, result2["json_output"], logger)
        update_runtime(run_id, t_pair2=t_pair2, filepath=stats_file)

    logger.info("Processed %s registrations successfully.", max_items)
