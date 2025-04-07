#!/usr/bin/env python3

import argparse
import json
import random
import sys
from pathlib import Path


def sample_registrations():
    """
    Sample n random registrations from an input JSON file and write them to an output file.
    """
    parser = argparse.ArgumentParser(description="Sample JSON data from input file")
    parser.add_argument(
        "--input", type=str, required=True, help="Path to input JSON file"
    )
    parser.add_argument(
        "--output", type=str, required=True, help="Path to output JSON file"
    )
    parser.add_argument(
        "--samples",
        type=int,
        required=False,
        default=100,
        help="Number of samples to take",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    sample_size = int(args.samples)

    try:
        with open(input_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            sample_data = random.sample(data, sample_size)

            # Add Proposal_OptimalAmountOfBatteries field to each element
            for item in sample_data:
                # Generate random value with 50% probability for "0", 25% for "1", and 25% for "2"
                rand_val = random.choices(["0", "1", "2"], weights=[0.5, 0.25, 0.25])[0]
                item["Proposal_OptimalAmountOfBatteries"] = rand_val

            with open(output_path, "w", encoding="utf-8") as output_file:
                json.dump(sample_data, output_file, indent=2)
            print(f"Successfully wrote {len(sample_data)} samples to {output_path}")
        else:
            print("The data is not a list. Please check the input file format.")
            sys.exit(1)

    except FileNotFoundError:
        print(f"Error: Could not find input file at {input_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in input file")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    sample_registrations()
