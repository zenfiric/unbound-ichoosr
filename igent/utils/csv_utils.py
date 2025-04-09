import os

import pandas as pd

EXECUTION_TIMES_CSV = "execution_times.csv"


def init_csv(filepath: str = EXECUTION_TIMES_CSV, columns: list = None):
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
) -> None:
    """Update execution times in CSV file using pandas with flexible time arguments."""
    if not os.path.exists(filepath):
        columns = ["registration_id"]
        if t_group is not None:
            columns.append("group_time_seconds")
        if t_pair1 is not None:
            columns.append("pair1_time_seconds")
        if t_pair2 is not None:
            columns.append("pair2_time_seconds")
        if t_matcher1 is not None:
            columns.append("matcher1_time_seconds")
        if t_matcher2 is not None:
            columns.append("matcher2_time_seconds")
        if t_matcher1_critic is not None:
            columns.append("matcher1_critic_time_seconds")
        init_csv(filepath, columns=columns)

    df = pd.read_csv(filepath)

    if run_id in df["registration_id"].values:
        if t_group is not None and "group_time_seconds" in df.columns:
            df.loc[df["registration_id"] == run_id, "group_time_seconds"] = (
                f"{t_group:.3f}"
            )
        if t_pair1 is not None and "pair1_time_seconds" in df.columns:
            df.loc[df["registration_id"] == run_id, "pair1_time_seconds"] = (
                f"{t_pair1:.3f}"
            )
        if t_pair2 is not None and "pair2_time_seconds" in df.columns:
            df.loc[df["registration_id"] == run_id, "pair2_time_seconds"] = (
                f"{t_pair2:.3f}"
            )
        if t_matcher1 is not None and "matcher1_time_seconds" in df.columns:
            df.loc[df["registration_id"] == run_id, "matcher1_time_seconds"] = (
                f"{t_matcher1:.3f}"
            )
        if t_matcher2 is not None and "matcher2_time_seconds" in df.columns:
            df.loc[df["registration_id"] == run_id, "matcher2_time_seconds"] = (
                f"{t_matcher2:.3f}"
            )
        if (
            t_matcher1_critic is not None
            and "matcher1_critic_time_seconds" in df.columns
        ):
            df.loc[df["registration_id"] == run_id, "matcher1_critic_time_seconds"] = (
                f"{t_matcher1_critic:.3f}"
            )
    else:
        new_row = {"registration_id": run_id}
        if t_group is not None:
            new_row["group_time_seconds"] = f"{t_group:.3f}"
        if t_pair1 is not None:
            new_row["pair1_time_seconds"] = f"{t_pair1:.3f}"
        if t_pair2 is not None:
            new_row["pair2_time_seconds"] = f"{t_pair2:.3f}"
        if t_matcher1 is not None:
            new_row["matcher1_time_seconds"] = f"{t_matcher1:.3f}"
        if t_matcher2 is not None:
            new_row["matcher2_time_seconds"] = f"{t_matcher2:.3f}"
        if t_matcher1_critic is not None:
            new_row["matcher1_critic_time_seconds"] = f"{t_matcher1_critic:.3f}"
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(filepath, index=False)
