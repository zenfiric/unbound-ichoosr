#!/usr/bin/env python3
"""Reset supplier capacity in offers files to 0.

This script resets the 'Used' and 'UsedPct' fields for all suppliers
in an offers file to 0, preparing it for a fresh workflow run.

Usage:
    python scripts/reset_capacity.py data/sbus/offers/base_offers.json
    python scripts/reset_capacity.py --all
"""
import argparse
import json
from pathlib import Path


def reset_capacity(offers_file: str) -> None:
    """Reset capacity in an offers file to 0."""
    with open(offers_file, "r") as f:
        offers = json.load(f)

    if "SupplierOffers" not in offers:
        print(f"❌ No 'SupplierOffers' found in {offers_file}")
        return

    for supplier in offers["SupplierOffers"]:
        supplier["Used"] = 0
        supplier["UsedPct"] = 0.0

    with open(offers_file, "w") as f:
        json.dump(offers, f, indent=2)

    print(f"✓ Reset capacity in {offers_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Reset supplier capacity to 0 in offers files"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Offers files to reset (or use --all for all files)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Reset all offers files in data/sbus/offers/",
    )

    args = parser.parse_args()

    if args.all:
        offers_dir = Path("data/sbus/offers")
        files = list(offers_dir.glob("*.json"))
        if not files:
            print("No offers files found in data/sbus/offers/")
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
