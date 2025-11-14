"""Utility functions for loading and managing scenario configurations."""

from pathlib import Path

import yaml


def load_scenario(scenario_path: str) -> dict:
    """Load a scenario YAML configuration file.

    Args:
        scenario_path: Path to the scenario YAML file

    Returns:
        Dictionary containing scenario configuration

    Example:
        >>> scenario = load_scenario("data/sbus/scenarios/overlap_only.yaml")
        >>> print(scenario["registrations"])
        'registrations/overlap_only.json'
    """
    with open(scenario_path, "r") as f:
        config = yaml.safe_load(f)

    # Convert relative paths to absolute paths based on scenario file location
    scenario_dir = Path(scenario_path).parent.parent

    # Resolve relative paths in the scenario config
    if "registrations" in config:
        config["registrations"] = str(scenario_dir / config["registrations"])
    if "offers" in config:
        config["offers"] = str(scenario_dir / config["offers"])
    if "capacity" in config:
        config["capacity"] = str(scenario_dir / config["capacity"])
    if "output" in config:
        output_dir = scenario_dir / "results"
        for key in ["matches", "pos", "stats"]:
            if key in config["output"]:
                # Extract just the filename from the output path
                filename = Path(config["output"][key]).name
                config["output"][key] = str(output_dir / filename)

    return config


def list_scenarios(scenarios_dir: str = "data/sbus/scenarios") -> list[str]:
    """List all available scenario files.

    Args:
        scenarios_dir: Directory containing scenario YAML files

    Returns:
        List of scenario file paths
    """
    scenarios_path = Path(scenarios_dir)
    return [str(p) for p in scenarios_path.glob("*.yaml")]
