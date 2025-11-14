#!/usr/bin/env python3
"""Reset supplier capacity tracking files to 0.

This script resets the 'Used' and 'UsedPct' fields for all suppliers
in capacity tracking files to 0, preparing them for a fresh workflow run.

Note: Capacity tracking is now separate from offers files. Offers files
remain immutable and are not modified by this script.

Usage:
    python scripts/reset_capacity.py data/sbus/capacity/capacity.json
    python scripts/reset_capacity.py --all
"""
import argparse
import json
from pathlib import Path


def reset_capacity(capacity_file: str) -> None:
    """Reset capacity in a capacity tracking file to 0."""
    with open(capacity_file, "r") as f:
        capacity_data = json.load(f)

    if not isinstance(capacity_data, dict):
        print(f"❌ Invalid capacity file format: {capacity_file}")
        return

    # Reset all supplier capacities
    for supplier_capacity in capacity_data.values():
        if isinstance(supplier_capacity, dict):
            supplier_capacity["Used"] = 0
            supplier_capacity["UsedPct"] = 0.0

    with open(capacity_file, "w") as f:
        json.dump(capacity_data, f, indent=2)

    print(f"✓ Reset capacity in {capacity_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Reset supplier capacity to 0 in capacity tracking files"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Capacity files to reset (or use --all for all files)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Reset all capacity files in data/sbus/capacity/",
    )

    args = parser.parse_args()

    if args.all:
        capacity_dir = Path("data/sbus/capacity")
        files = list(capacity_dir.glob("*.json"))
        if not files:
            print("No capacity files found in data/sbus/capacity/")
            return
    elif args.files:
        files = [Path(f) for f in args.files]
    else:
        print("Please specify files to reset or use --all")
        parser.print_help()
        return

    print(f"Resetting capacity for {len(files)} file(s)...\n")
    for file_path in files:
        reset_capacity(str(file_path))

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
