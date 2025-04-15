#!/usr/bin/env python3

import argparse
import json
import random
import sys
from pathlib import Path


def sample_registrations():
    """
    Sample n random registrations from an input JSON file, ensure 50% have specific zip codes
    in Contact_Zip, and write them to an output file.
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

        if not isinstance(data, list):
            print("The data is not a list. Please check the input file format.")
            sys.exit(1)

        target_zip_codes = ["55407", "55419", "55447"]
        available_zip_codes = list(
            {
                item.get("Contact_Zip")
                for item in data
                if item.get("Contact_Zip")
                and item.get("Contact_Zip") not in target_zip_codes
            }
        )
        if not available_zip_codes:
            print(
                "Warning: No non-target zip codes found in input data. Using target zip codes only."
            )
            available_zip_codes = target_zip_codes

        # Sample registrations
        samples = random.sample(data, min(sample_size, len(data)))
        num_target_zips = sample_size // 2

        indices = list(range(len(samples)))
        random.shuffle(indices)
        target_indices = indices[:num_target_zips]
        non_target_indices = indices[num_target_zips:]

        for i in target_indices:
            samples[i]["Contact_Zip"] = random.choice(target_zip_codes)

        for i in non_target_indices:
            if samples[i].get("Contact_Zip") in target_zip_codes:
                samples[i]["Contact_Zip"] = random.choice(available_zip_codes)

        for item in samples:
            rand_val = random.choices(["0", "1", "2"], weights=[0.5, 0.25, 0.25])[0]
            item["Proposal_OptimalAmountOfBatteries"] = rand_val

        with open(output_path, "w", encoding="utf-8") as output_file:
            json.dump(samples, output_file, indent=2)
        print(f"Successfully wrote {len(samples)} samples to {output_path}")
        print(
            f"Assigned {num_target_zips} registrations with Contact_Zip in {target_zip_codes}"
        )

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
