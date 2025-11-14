"""Configurable workflow that supports multiple constellation patterns via YAML configuration."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from igent.agents import get_agents
from igent.logging_config import logger
from igent.utils import process_pair, update_runtime
from igent.utils.batch_writer import AutoFlushBatchWriter
from igent.utils.timing import Timer

from .workflow import Workflow, WorkflowConfig


@dataclass
class PhaseConfig:
    """Configuration for a single workflow phase."""

    name: str
    description: str
    agents: list[dict]  # [{"role": "matcher1", "prompt_key": "a_matcher"}, ...]
    capacity_update_before: bool
    capacity_update_after: bool


@dataclass
class ConstellationConfig:
    """Complete constellation configuration loaded from YAML."""

    name: str
    description: str
    phases: list[PhaseConfig]
    prompts_variant: str | None
    timing_columns: list[str]


class ConfigurableWorkflow(Workflow):
    """Single configurable workflow that supports all constellation patterns.

    This class replaces the individual workflow implementations (p1m1m2c, p1m1c1m2c2, etc.)
    with a unified implementation driven by YAML configuration files.

    Example:
        >>> config = WorkflowConfig(
        ...     model="zai_glm4_5_air",
        ...     constellation="p1m1m2c",
        ...     registrations_file="data/sbus/registrations/full_dataset.json",
        ...     offers_file="data/sbus/offers/base_offers.json",
        ...     matches_file="data/sbus/results/matches.json",
        ...     pos_file="data/sbus/results/pos.json",
        ...     stats_file="data/sbus/results/stats.csv",
        ... )
        >>> workflow = ConfigurableWorkflow(config)
        >>> await workflow.run()
    """

    def __init__(self, config: WorkflowConfig):
        super().__init__(config)
        self.constellation = self._load_constellation_config()
        self._last_matches = []  # Store matches from phase 1 for phase 2
        self._batch_writer = AutoFlushBatchWriter(batch_size=5)  # Batch file writes

    def _load_constellation_config(self) -> ConstellationConfig:
        """Load constellation configuration from YAML file."""
        # Look for config file in config/constellations/
        # Use absolute path relative to this file's location
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent  # Go up to project root
        config_path = (
            project_root
            / "config"
            / "constellations"
            / f"{self.config.constellation}.yaml"
        )

        if not config_path.exists():
            raise FileNotFoundError(
                f"Constellation config not found: {config_path}\n"
                f"Available constellations: p1m1m2c, p1m1c1m2c2, p1m1_p2m2, p1m1c1_p2m2c2"
            )

        with open(config_path) as f:
            data = yaml.safe_load(f)

        # Parse phases
        phases = [
            PhaseConfig(
                name=p["name"],
                description=p.get("description", ""),
                agents=p["agents"],
                capacity_update_before=p.get("capacity_update_before", False),
                capacity_update_after=p.get("capacity_update_after", False),
            )
            for p in data["phases"]
        ]

        return ConstellationConfig(
            name=data["name"],
            description=data["description"],
            phases=phases,
            prompts_variant=data["prompts"].get("variant"),
            timing_columns=data["timing"]["columns"],
        )

    def _get_csv_columns(self) -> list[str]:
        """Return CSV column names for timing data."""
        return ["registration_id"] + self.constellation.timing_columns

    async def _initialize(self):
        """Initialize workflow with constellation-specific prompt variant."""
        # Override parent to use constellation's prompt variant
        from igent.prompts import load_prompts
        from igent.utils import init_csv

        init_csv(filepath=self.stats_file, columns=self._get_csv_columns())
        self.prompts = await load_prompts(
            self.config.business_line, variant=self.constellation.prompts_variant
        )

    async def _process_registration(
        self,
        run_id: str,
        registration: dict,
        offers: list[dict],
        incentives: list[dict] | None,
    ) -> list[dict] | None:
        """Process registration through all configured phases."""
        timing_data = {}
        timer = Timer(f"registration_{run_id}")

        for phase_idx, phase in enumerate(self.constellation.phases):
            logger.info(
                f"Starting {phase.name} for registration {run_id}: {phase.description}"
            )

            with timer.section(f"{phase.name}_total"):
                # Update capacity BEFORE phase if configured
                if phase.capacity_update_before and self._last_matches:
                    with timer.section(f"{phase.name}_capacity_update_before"):
                        offers = await self._update_capacity(self._last_matches, run_id)
                        if offers is None:
                            return None

                # Build prompts dict for this phase
                with timer.section(f"{phase.name}_setup"):
                    prompts_dict = {
                        agent["role"]: self.prompts[agent["prompt_key"]]
                        for agent in phase.agents
                    }

                    # Create agent group for this phase
                    group = await get_agents(
                        model=self.config.model,
                        stream=self.config.stream,
                        prompts=prompts_dict,
                        enable_thinking=self.config.enable_thinking,
                    )

                    # Build message based on phase and agents
                    message = self._build_phase_message(
                        phase, registration, offers, incentives, run_id
                    )

                # Execute phase (AI conversation)
                logger.debug(
                    f"About to execute {phase.name} with {len(phase.agents)} agents"
                )
                with timer.section(f"{phase.name}_agent_conversation"):
                    result = await process_pair(
                        pair=group,
                        message=message,
                        run_id=run_id,
                        pair_name=phase.name,
                        logger=logger,
                    )

            phase_time = timer.timings.get(f"{phase.name}_total", 0)
            logger.debug(f"Completed {phase.name}, took {phase_time:.3f}s")

            # Store timing with column name from config
            timing_key = self.constellation.timing_columns[phase_idx]
            timing_data[timing_key.replace("_seconds", "")] = phase_time

            # Also store detailed breakdown
            agent_conv_time = timer.timings.get(f"{phase.name}_agent_conversation", 0)
            timing_data[f"{phase.name}_agent_conversation"] = agent_conv_time

            logger.info(
                f"{phase.name} execution time: {phase_time:.3f}s (AI: {agent_conv_time:.3f}s)"
            )

            # Check phase success
            if not result or not result["success"]:
                logger.warning(f"{phase.name} failed for registration {run_id}")
                return None

            # Handle phase output
            output_data = result.get("json_output")
            if output_data:
                with timer.section(f"{phase.name}_file_write"):
                    # Determine output destination based on agent roles
                    agent_roles = [a["role"] for a in phase.agents]

                    # First matcher phase outputs to matches (batch write)
                    if any("matcher1" in role for role in agent_roles):
                        self._batch_writer.append(str(self.matches_file), output_data)
                        # For immediate access, also update in-memory cache
                        if not self._last_matches:
                            self._last_matches = []
                        # output_data is already a dict, not a list
                        if isinstance(output_data, list):
                            self._last_matches.extend(output_data)
                        else:
                            self._last_matches.append(output_data)

                    # Second matcher phase outputs to POS (batch write)
                    elif any("matcher2" in role for role in agent_roles):
                        self._batch_writer.append(str(self.pos_file), output_data)

                # Store file write timing (batch append is fast)
                file_write_time = timer.timings.get(f"{phase.name}_file_write", 0)
                timing_data[f"{phase.name}_file_write"] = file_write_time

            # Update capacity AFTER phase if configured
            if phase.capacity_update_after and self._last_matches:
                with timer.section(f"{phase.name}_capacity_update_after"):
                    offers = await self._update_capacity(self._last_matches, run_id)
                    if offers is None:
                        return None

                # Store capacity update timing
                cap_update_time = timer.timings.get(
                    f"{phase.name}_capacity_update_after", 0
                )
                timing_data[f"{phase.name}_capacity_update"] = cap_update_time

        # Record timing for all phases
        update_runtime(run_id, filepath=self.stats_file, **timing_data)

        # Log detailed timing summary
        logger.debug(timer.format_summary())

        return offers

    async def run(self):
        """Run the workflow with batch writing."""
        await super().run()

        # Flush any remaining batched writes
        pending_count = self._batch_writer.get_pending_count()
        if pending_count > 0:
            logger.info(f"Flushing {pending_count} pending writes...")
            written = await self._batch_writer.flush_all()
            logger.info(f"Wrote {written} records to disk")

    def _build_phase_message(
        self,
        phase: PhaseConfig,
        registration: dict,
        offers: list[dict],
        incentives: list[dict] | None,
        run_id: str,
    ) -> str:
        """Build user message for phase based on agents present."""
        message_parts = []
        agent_roles = [a["role"] for a in phase.agents]

        # Build message for each agent in the phase
        for agent in phase.agents:
            role = agent["role"]

            # Matcher1 instructions
            if "matcher1" in role:
                message_parts.append(
                    f"{role.capitalize()}: Match based on instructions in system prompt.\n"
                    f"REGISTRATION: ```{[registration]}```\n"
                    f"OFFERS: ```{offers}```\n"
                )

            # Critic1 or generic critic for matcher1
            elif "critic1" in role or (
                "critic" in role and any("matcher1" in r for r in agent_roles)
            ):
                message_parts.append(
                    f"{role.capitalize()}: Review Matcher1's output and say 'APPROVE' if acceptable.\n"
                )

            # Matcher2 instructions
            elif "matcher2" in role:
                # Get match from phase 1
                filtered_match = None
                if self._last_matches:
                    filtered_match = next(
                        (
                            m
                            for m in self._last_matches
                            if m.get("registration_id") == run_id
                        ),
                        None,
                    )

                incentive_text = (
                    f"INCENTIVES: ```{incentives}```\n"
                    if incentives
                    else "INCENTIVES: Use fetch_incentives_tool to fetch incentives based on zip code.\n"
                )

                message_parts.append(
                    f"{role.capitalize()}: Enrich matches with pricing and subsidies:\n"
                    f"MATCHES: ```{[filtered_match] if filtered_match else []}```\n"
                    f"OFFERS: ```{offers}```\n"
                    f"{incentive_text}"
                )

            # Critic2 or generic critic for matcher2
            elif "critic2" in role or (
                "critic" in role and any("matcher2" in r for r in agent_roles)
            ):
                message_parts.append(
                    f"{role.capitalize()}: Review Matcher2's output and say 'APPROVE' if acceptable.\n"
                )

        return "".join(message_parts)
