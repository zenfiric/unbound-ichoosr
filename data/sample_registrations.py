#!/usr/bin/env python3

import argparse
import json
import random
import sys
from pathlib import Path


def sample_registrations():
    """
    Sample n random registrations from an input JSON file, ensure 50% have specific zip codes
    in Contact_Zip, and the other 50% have zip codes present in both registrations and supplier
    service areas, then write them to an output file.
    """
    parser = argparse.ArgumentParser(description="Sample JSON data from input file")
    parser.add_argument(
        "--input", type=str, required=True, help="Path to input JSON file"
    )
    parser.add_argument(
        "--output", type=str, required=True, help="Path to output JSON file"
    )
    parser.add_argument(
        "--offers", type=str, required=True, help="Path to supplier offers JSON file"
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
    offers_path = Path(args.offers)
    sample_size = int(args.samples)

    try:
        # Load registrations
        with open(input_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            print(
                "The registrations data is not a list. Please check the input file format."
            )
            sys.exit(1)

        # Load supplier offers
        with open(offers_path, "r", encoding="utf-8") as file:
            offers_data = json.load(file)

        # Extract all supplier service area zip codes
        supplier_zip_codes = set()
        for supplier in offers_data.get("SupplierOffers", []):
            supplier_zip_codes.update(supplier.get("ServiceAreas", []))

        # Get zip codes present in registrations
        registration_zip_codes = {
            item.get("Contact_Zip") for item in data if item.get("Contact_Zip")
        }

        # Define target zip codes
        target_zip_codes = ["55407", "55419", "55447"]

        # Find non-target zip codes that are in both registrations and supplier service areas
        available_zip_codes = list(
            registration_zip_codes & supplier_zip_codes - set(target_zip_codes)
        )

        if not available_zip_codes:
            print(
                "Warning: No non-target zip codes found in both registrations and supplier service areas. Using target zip codes only."
            )
            available_zip_codes = target_zip_codes

        # Sample registrations
        samples = random.sample(data, min(sample_size, len(data)))
        num_target_zips = sample_size // 2

        # Shuffle indices to assign zip codes
        indices = list(range(len(samples)))
        random.shuffle(indices)
        target_indices = indices[:num_target_zips]
        non_target_indices = indices[num_target_zips:]

        # Assign target zip codes to first 50%
        for i in target_indices:
            samples[i]["Contact_Zip"] = random.choice(target_zip_codes)

        # Assign non-target zip codes to second 50%, ensuring they are valid
        for i in non_target_indices:
            samples[i]["Contact_Zip"] = random.choice(available_zip_codes)

        # Assign random Proposal_OptimalAmountOfBatteries
        for item in samples:
            rand_val = random.choices(["0", "1", "2"], weights=[0.5, 0.25, 0.25])[0]
            item["Proposal_OptimalAmountOfBatteries"] = rand_val

        # Write output
        with open(output_path, "w", encoding="utf-8") as output_file:
            json.dump(samples, output_file, indent=2)
        print(f"Successfully wrote {len(samples)} samples to {output_path}")
        print(
            f"Assigned {num_target_zips} registrations with Contact_Zip in {target_zip_codes}"
        )
        print(
            f"Assigned {len(samples) - num_target_zips} registrations with Contact_Zip in {available_zip_codes}"
        )

    except FileNotFoundError as e:
        print(f"Error: Could not find file - {str(e)}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in one of the input files")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    sample_registrations()
