import os

import pandas as pd

EXECUTION_TIMES_CSV = "execution_times.csv"


def init_csv(
    filepath: str = EXECUTION_TIMES_CSV, columns: list[str] | None = None
) -> None:
    """Initialize CSV file with headers if it doesn't exist."""
    if not os.path.exists(filepath):
        if columns is None:
            columns = ["registration_id", "group_time_seconds"]
        df = pd.DataFrame(columns=columns)
        df.to_csv(filepath, index=False)


def update_runtime(
    run_id: str,
    filepath: str = EXECUTION_TIMES_CSV,
    t_group: float = None,
    t_pair1: float = None,
    t_pair2: float = None,
    t_matcher1: float = None,
    t_matcher2: float = None,
    t_matcher1_critic: float = None,
    **kwargs,
) -> None:
    """Update execution times in CSV file using pandas with flexible time arguments.

    Accepts both legacy named parameters (t_group, t_pair1, etc.) and
    flexible **kwargs for constellation-specific timing columns.

    Example:
        # Legacy style
        update_runtime(run_id, t_matcher1=1.5, t_matcher2=2.3)

        # New style with kwargs
        update_runtime(run_id, matcher1_critic_time=1.5, matcher2_time=2.3)
    """
    # Build timing data from both named args and kwargs
    timing_data = {}

    # Legacy parameter mapping
    legacy_params = {
        "t_group": "group_time_seconds",
        "t_pair1": "pair1_time_seconds",
        "t_pair2": "pair2_time_seconds",
        "t_matcher1": "matcher1_time_seconds",
        "t_matcher2": "matcher2_time_seconds",
        "t_matcher1_critic": "matcher1_critic_time_seconds",
    }

    for param_name, column_name in legacy_params.items():
        value = locals()[param_name]
        if value is not None:
            timing_data[column_name] = value

    # Add kwargs (add _seconds suffix if not present)
    for key, value in kwargs.items():
        if value is not None:
            column_name = f"{key}_seconds" if not key.endswith("_seconds") else key
            timing_data[column_name] = value

    # Initialize CSV if needed
    if not os.path.exists(filepath):
        columns = ["registration_id"] + list(timing_data.keys())
        init_csv(filepath, columns=columns)

    df = pd.read_csv(filepath)

    # Add any new columns that don't exist yet
    for column in timing_data.keys():
        if column not in df.columns:
            df[column] = None

    # Update or insert row
    if run_id in df["registration_id"].values:
        # Update existing row
        for column, value in timing_data.items():
            df.loc[df["registration_id"] == run_id, column] = f"{value:.3f}"
    else:
        # Insert new row
        new_row = {"registration_id": run_id}
        for column, value in timing_data.items():
            new_row[column] = f"{value:.3f}"
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(filepath, index=False)
