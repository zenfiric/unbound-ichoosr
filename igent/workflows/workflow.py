from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from igent.logging_config import logger
from igent.prompts import load_prompts
from igent.tools.read_json import read_json
from igent.tools.update_supplier_capacity import update_supplier_capacity
from igent.utils import EXECUTION_TIMES_CSV, MAX_ITEMS, init_csv


@dataclass
class WorkflowConfig:
    """Configuration for the workflow."""

    model: str
    business_line: str = "sbus"
    registrations_file: str = "registrations.json"
    offers_file: str = "offers.json"
    incentives_file: Optional[str] = None
    matches_file: str = "matches.json"
    pos_file: str = "pos.json"
    stats_file: str = EXECUTION_TIMES_CSV
    max_items: int = MAX_ITEMS
    stream: bool = False
    configuration: str = (
        "p1m1m2c"  # Options: p1m1m2c, p1m1c1m2c2, p1m1c1_p2m2c2, p1m1_p2m2
    )


class Workflow(ABC):
    """Abstract base class for running matching workflows."""

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.prompts = None
        self.stats_file = self._construct_filepath(config.stats_file)
        self.matches_file = self._construct_filepath(config.matches_file)
        self.pos_file = self._construct_filepath(config.pos_file)

    def _construct_filepath(self, filename: str) -> Path:
        """Construct a filepath with configuration, business line, and model prefix."""
        path = Path(filename)
        return (
            path.parent
            / f"{self.config.business_line}_{self.config.configuration}_{self.config.model}_{path.name}"
        )

    async def _load_data(self) -> Tuple[List[Dict], List[Dict], Optional[List[Dict]]]:
        """Load registrations, offers, and incentives data."""
        registrations = await read_json(self.config.registrations_file)
        if not isinstance(registrations, list):
            logger.error("Registrations file must contain a list.")
            raise ValueError("Invalid registrations format")

        offers = await read_json(self.config.offers_file)
        incentives = (
            await read_json(self.config.incentives_file)
            if self.config.incentives_file
            else None
        )
        return registrations, offers, incentives

    async def _initialize(self):
        """Initialize CSV and load prompts."""
        init_csv(
            filepath=self.stats_file,
            columns=self._get_csv_columns(),
        )
        variant = (
            "one_critic"
            if self.config.configuration == "p1m1m2c"
            else "no_critic" if self.config.configuration == "p1m1_p2m2" else None
        )
        self.prompts = await load_prompts(self.config.business_line, variant=variant)

    @abstractmethod
    def _get_csv_columns(self) -> List[str]:
        """Define CSV columns for runtime stats."""
        pass

    async def run(self):
        """Run the workflow."""
        await self._initialize()
        try:
            registrations, offers, incentives = await self._load_data()
        except ValueError:
            return

        max_items = min(self.config.max_items, len(registrations))
        if not max_items:
            logger.warning("No registrations to process.")
            return

        logger.info("Processing %d registrations...", max_items)

        for i, registration in enumerate(registrations[:max_items], 1):
            run_id = registration.get("RegistrationNumber", "unknown")
            logger.info("Processing registration %d/%d (ID: %s)", i, max_items, run_id)

            offers = await self._process_registration(
                run_id, registration, offers, incentives
            )
            if offers is None:  # Error occurred
                continue

        logger.info("Processed %d registrations successfully.", max_items)

    @abstractmethod
    async def _process_registration(
        self,
        run_id: str,
        registration: Dict,
        offers: List[Dict],
        incentives: Optional[List[Dict]],
    ) -> Optional[List[Dict]]:
        """Process a single registration."""
        pass

    async def _update_capacity(
        self, matches: List[Dict], run_id: str
    ) -> Optional[List[Dict]]:
        """Update supplier capacity and reload offers."""
        logger.debug("Current match for update: %s", matches)
        try:
            result = await update_supplier_capacity(matches, self.config.offers_file)
            logger.info("Capacity update: %s", result)
            offers = await read_json(self.config.offers_file)
            logger.debug("Updated offers: %s", offers)
            return offers
        except ValueError as e:
            logger.error("Error updating capacity for registration %s: %s", run_id, e)
            return None
