import time

from igent.agents import get_agents
from igent.logging_config import logger
from igent.tools.read_json import read_json
from igent.utils import (
    EXECUTION_TIMES_CSV,
    MAX_ITEMS,
    load_scenario,
    process_pair,
    update_json_list,
    update_runtime,
)

from .workflow import Workflow, WorkflowConfig


class Matcher1CriticMatcher2Workflow(Workflow):
    """Workflow for Matcher1-Critic-Matcher2 configuration (p1m1m2c)."""

    def _get_csv_columns(self) -> list[str]:
        return [
            "registration_id",
            "matcher1_critic_time_seconds",
            "matcher2_time_seconds",
        ]

    async def _process_registration(
        self,
        run_id: str,
        registration: dict,
        offers: list[dict],
        incentives: list[dict] | None,
    ) -> list[dict] | None:
        # Phase 1: Matcher1 and Critic
        group1 = await get_agents(
            model=self.config.model,
            stream=self.config.stream,
            prompts={
                "matcher1": self.prompts["a_matcher"],
                "critic": self.prompts["critic"],
            },
        )
        message1 = (
            "Matcher1: Match based on instructions in system prompt.\n"
            f"REGISTRATION: ```{[registration]}```\n"
            f"OFFERS: ```{offers}```\n"
            "Critic: Review Matcher1's output and say 'APPROVE' if acceptable.\n"
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
            logger.warning(
                "Matcher1-Critic failed for registration %s. Skipping.", run_id
            )
            return None

        update_json_list(self.matches_file, result1["json_output"], logger)
        matches = await read_json(self.matches_file)
        offers = await self._update_capacity(matches, run_id)
        if offers is None:
            return None

        # Phase 2: Matcher2
        group2 = await get_agents(
            model=self.config.model,
            stream=self.config.stream,
            prompts={"matcher2": self.prompts["b_matcher"]},
        )
        filtered_match = next(
            (m for m in matches if m.get("registration_id") == run_id),
            None,
        )
        if not filtered_match:
            logger.warning("No match found for registration ID: %s", run_id)
            return None

        message2 = (
            "Matcher2: Enrich matches with pricing and subsidies:\n"
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
            logger.warning("Matcher2 failed for registration %s. Continuing.", run_id)
            return offers

        update_json_list(self.pos_file, result2["json_output"], logger)
        update_runtime(
            run_id,
            t_matcher1_critic=t_matcher1_critic,
            t_matcher2=t_matcher2,
            filepath=self.stats_file,
        )
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
    constellation: str = "p1m1m2c",
):
    """Run the workflow for processing registrations with (matcher1-critic-matcher2) configuration.

    This is a convenience wrapper around Matcher1CriticMatcher2Workflow class.
    """
    config = WorkflowConfig(
        model=model,
        stream=stream,
        business_line=business_line,
        registrations_file=registrations_file,
        offers_file=offers_file,
        incentives_file=incentives_file,
        matches_file=matches_file,
        pos_file=pos_file,
        max_items=max_items,
        stats_file=stats_file,
        constellation=constellation,
    )
    workflow = Matcher1CriticMatcher2Workflow(config)
    await workflow.run()


async def run_workflow_from_scenario(
    scenario_file: str,
    model: str,
    stream: bool = False,
    max_items: int = MAX_ITEMS,
    constellation: str = "p1m1m2c",
):
    """Run the workflow using a scenario configuration file.

    This is a convenience function that combines scenario-based data management
    with constellation-based workflow configuration.

    Args:
        scenario_file: Path to the scenario YAML file (e.g., "data/sbus/scenarios/overlap_only.yaml")
        model: Model name to use (e.g., "openai_gpt4o", "zai_glm4_5_air")
        stream: Whether to stream responses
        max_items: Maximum number of registrations to process
        constellation: Workflow constellation (e.g., "p1m1m2c", "p1m1c1m2c2")

    Example:
        >>> await run_workflow_from_scenario(
        ...     scenario_file="data/sbus/scenarios/overlap_only.yaml",
        ...     model="zai_glm4_5_air",
        ...     constellation="p1m1m2c",
        ...     max_items=10
        ... )
    """
    from igent.workflows import run_workflow as unified_run_workflow

    scenario = load_scenario(scenario_file)

    await unified_run_workflow(
        model=model,
        stream=stream,
        business_line="sbus",  # Extract from scenario if needed
        registrations_file=scenario["registrations"],
        offers_file=scenario["offers"],
        matches_file=scenario["output"]["matches"],
        pos_file=scenario["output"]["pos"],
        stats_file=scenario["output"]["stats"],
        max_items=max_items,
        constellation=constellation,
    )
