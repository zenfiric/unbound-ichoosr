#!/usr/bin/env python3
"""
Run benchmark tests with exactly 10 samples for each model using p1m1m2c constellation.
Results will be stored in data/sbus/results/ directory with naming pattern:
  p1m1m2c_sbus_{model}_{constellation}_matches.json
  p1m1m2c_sbus_{model}_{constellation}_pos.json
  p1m1m2c_sbus_{model}_{constellation}_stats.csv
"""

import asyncio
import logging
import subprocess

from igent.workflows import run_workflow

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Models to test
MODELS = [
    "openai_gpt4o",
    "openai_gpt5",
    "openai_gpt5mini",
    "zai_glm4_6",
    "zai_glm4_5_air",
]

CONSTELLATION = "p1m1m2c"
BUSINESS_LINE = "sbus"
DATA_DIR = "./data/sbus"
SCENARIO = "overlap_only"
MAX_ITEMS = 10


def reset_capacity():
    """Reset supplier capacity before each model run."""
    logger.info("Resetting supplier capacity...")
    try:
        subprocess.run(
            ["python", "scripts/reset_capacity.py", "--all"],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info("✓ Capacity reset complete")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Capacity reset failed: {e.stderr}")
        logger.info("Continuing anyway...")


async def run_model_benchmark(model: str):
    """Run benchmark for a single model."""
    logger.info(f"\n{'='*70}")
    logger.info(f"Starting benchmark for model: {model}")
    logger.info(f"{'='*70}\n")

    # Reset capacity before each model run
    reset_capacity()

    try:
        await run_workflow(
            constellation=CONSTELLATION,
            model=model,
            business_line=BUSINESS_LINE,
            data_dir=DATA_DIR,
            scenario=SCENARIO,
            max_items=MAX_ITEMS,
            enable_thinking=False,
            stream=False,
        )

        logger.info(f"\n✅ Completed benchmark for {model}\n")

    except Exception as e:
        logger.error(f"\n❌ Error running benchmark for {model}: {e}\n")
        raise


async def main():
    """Run benchmarks for all models sequentially."""
    logger.info(f"Starting benchmarks for {len(MODELS)} models")
    logger.info("Configuration:")
    logger.info(f"  - Constellation: {CONSTELLATION}")
    logger.info(f"  - Business Line: {BUSINESS_LINE}")
    logger.info(f"  - Scenario: {SCENARIO}")
    logger.info(f"  - Samples per model: {MAX_ITEMS}")
    logger.info(f"  - Output directory: {DATA_DIR}/results/")

    # Run each model sequentially
    for model in MODELS:
        await run_model_benchmark(model)

    logger.info("\n" + "=" * 70)
    logger.info("All benchmarks completed!")
    logger.info("=" * 70)
    logger.info(f"\nResults saved to: {DATA_DIR}/results/")


if __name__ == "__main__":
    asyncio.run(main())
