from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from igent.logging_config import logger
from igent.prompts import load_prompts
from igent.tools.read_json import read_json
from igent.utils import EXECUTION_TIMES_CSV, MAX_ITEMS, init_csv


@dataclass
class WorkflowConfig:
    """Configuration for the workflow.

    Supports smart defaults that automatically construct file paths based on:
    - data_dir: Base directory for all data files
    - scenario: Name of the scenario (e.g., "overlap_only")

    If data_dir and scenario are provided, individual file paths are auto-generated.
    Otherwise, you can specify each file path explicitly for backward compatibility.
    """

    model: str
    constellation: Literal["p1m1m2c", "p1m1c1m2c2", "p1m1c1_p2m2c2", "p1m1_p2m2"] = (
        "p1m1m2c"
    )
    business_line: str = "sbus"

    # Smart defaults option 1: Use data_dir + scenario
    data_dir: str | None = None  # e.g., "data/sbus"
    scenario: str | None = None  # e.g., "overlap_only"

    # Smart defaults option 2: Explicit paths (backward compatibility)
    registrations_file: str | None = None
    offers_file: str | None = None
    incentives_file: str | None = None
    capacity_file: str | None = None
    matches_file: str | None = None
    pos_file: str | None = None
    stats_file: str | None = None

    # Execution parameters
    max_items: int = MAX_ITEMS
    stream: bool = False

    def __post_init__(self):
        """Apply smart defaults for file paths if data_dir and scenario are provided."""
        if self.data_dir and self.scenario:
            # Auto-generate paths from data_dir + scenario
            base = Path(self.data_dir)

            if self.registrations_file is None:
                self.registrations_file = str(
                    base / "registrations" / f"{self.scenario}.json"
                )

            if self.offers_file is None:
                self.offers_file = str(base / "offers" / "base_offers.json")

            if self.capacity_file is None:
                self.capacity_file = str(base / "capacity" / f"{self.scenario}.json")

            if self.matches_file is None:
                self.matches_file = str(
                    base / "results" / f"{self.constellation}_matches.json"
                )

            if self.pos_file is None:
                self.pos_file = str(base / "results" / f"{self.constellation}_pos.json")

            if self.stats_file is None:
                self.stats_file = str(
                    base / "results" / f"{self.constellation}_stats.csv"
                )

        # Apply final defaults if still None
        if self.registrations_file is None:
            self.registrations_file = "registrations.json"
        if self.offers_file is None:
            self.offers_file = "offers.json"
        if self.capacity_file is None:
            self.capacity_file = "capacity.json"
        if self.matches_file is None:
            self.matches_file = "matches.json"
        if self.pos_file is None:
            self.pos_file = "pos.json"
        if self.stats_file is None:
            self.stats_file = EXECUTION_TIMES_CSV


class Workflow(ABC):
    """Abstract base class for running matching workflows."""

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.prompts = None
        self.stats_file = self._construct_filepath(config.stats_file)
        self.matches_file = self._construct_filepath(config.matches_file)
        self.pos_file = self._construct_filepath(config.pos_file)
        self._capacity_cache: dict[str, dict] | None = None  # Cache capacity data

    def _construct_filepath(self, filename: str | Path) -> Path:
        """Construct a filepath with configuration, business line, and model prefix."""
        path = Path(filename)
        return (
            path.parent
            / f"{self.config.business_line}_{self.config.constellation}_{self.config.model}_{path.name}"
        )

    async def _load_data(self) -> tuple[list[dict], list[dict], list[dict] | None]:
        """Load registrations, offers, and incentives data in parallel."""
        import asyncio

        # Load files in parallel
        tasks = [
            read_json(self.config.registrations_file),
            read_json(self.config.offers_file),
        ]

        if self.config.incentives_file:
            tasks.append(read_json(self.config.incentives_file))

        results = await asyncio.gather(*tasks)

        registrations = results[0]
        offers = results[1]
        incentives = results[2] if len(results) > 2 else None

        if not isinstance(registrations, list):
            logger.error("Registrations file must contain a list.")
            raise ValueError("Invalid registrations format")

        # Normalize field names: RegistrationNumber -> registration_id
        for reg in registrations:
            if "RegistrationNumber" in reg and "registration_id" not in reg:
                reg["registration_id"] = reg.pop("RegistrationNumber")

        return registrations, offers, incentives

    async def _initialize(self):
        """Initialize CSV and load prompts."""
        init_csv(
            filepath=self.stats_file,
            columns=self._get_csv_columns(),
        )
        variant = (
            "one_critic"
            if self.config.constellation == "p1m1m2c"
            else "no_critic" if self.config.constellation == "p1m1_p2m2" else None
        )
        self.prompts = await load_prompts(self.config.business_line, variant=variant)

    @abstractmethod
    def _get_csv_columns(self) -> list[str]:
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
            run_id = registration.get("registration_id", "unknown")
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
        registration: dict,
        offers: list[dict],
        incentives: list[dict] | None,
    ) -> list[dict] | None:
        """Process a single registration."""
        pass

    async def _get_capacity_data(self) -> dict[str, dict]:
        """Get cached capacity data, loading if necessary."""
        if self._capacity_cache is None:
            from igent.tools.capacity_tracker import initialize_capacity_file

            self._capacity_cache = await initialize_capacity_file(
                self.config.offers_file, self.config.capacity_file
            )
            logger.debug("Loaded capacity data into cache")
        return self._capacity_cache

    async def _update_capacity(
        self, matches: list[dict], run_id: str
    ) -> list[dict] | None:
        """Update supplier capacity and reload offers."""
        logger.debug("Current match for update: %s", matches)
        try:
            # Get cached capacity data
            capacity_data = await self._get_capacity_data()

            # Process the latest match
            match = matches[-1]
            supplier_id = match.get("supplier_id") or match.get("SupplierID")

            if not supplier_id:
                raise ValueError(f"Match missing supplier_id: {match}")

            if supplier_id not in capacity_data:
                raise ValueError(f"SupplierID {supplier_id} not found in capacity")

            supplier_capacity = capacity_data[supplier_id]
            current_used = supplier_capacity["Used"]
            capacity = supplier_capacity["Capacity"]

            # Increment Used by 1
            new_used = current_used + 1
            if new_used > capacity:
                raise ValueError(
                    f"Supplier {supplier_id} capacity exceeded: {new_used} > {capacity}"
                )

            supplier_capacity["Used"] = new_used
            supplier_capacity["UsedPct"] = (
                round(new_used / capacity, 2) if capacity > 0 else 0.0
            )

            # Write updated capacity to file (async, but don't await - fire and forget)
            import asyncio
            import json
            from pathlib import Path

            import aiofiles

            capacity_path = Path(self.config.capacity_file)

            async def write_capacity():
                async with aiofiles.open(capacity_path, "w") as f:
                    await f.write(json.dumps(capacity_data, indent=2))

            asyncio.create_task(write_capacity())  # Fire and forget

            logger.info(
                "Updated capacity for %s: %d/%d (%.0f%%)",
                supplier_id,
                new_used,
                capacity,
                supplier_capacity["UsedPct"] * 100,
            )

            # Reload offers (unchanged, but needed for workflow)
            offers = await read_json(self.config.offers_file)
            return offers
        except ValueError as e:
            logger.error("Error updating capacity for registration %s: %s", run_id, e)
            return None
