#!/usr/bin/env python3

import json
import random
import sys
import argparse
from pathlib import Path

def sample_registrations():
    """
    Sample n random registrations from an input JSON file and write them to an output file.
    """
    parser = argparse.ArgumentParser(description='Sample JSON data from input file')
    parser.add_argument('--input', type=str, required=True, help='Path to input JSON file')
    parser.add_argument('--output', type=str, required=True, help='Path to output JSON file')
    parser.add_argument('--sample', type=int, required=False, default=100, help='Number of samples to take')
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    sample_size = int(args.sample)

    try:
        with open(input_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        if isinstance(data, list):
            sample_data = random.sample(data, sample_size)

            with open(output_path, 'w', encoding='utf-8') as output_file:
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
