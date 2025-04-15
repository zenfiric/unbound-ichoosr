#!/usr/bin/env python3

import argparse
import json
import sys
from collections import defaultdict


def check_service_area(match, supplier_offer):
    """Check if the registration's zip code is in the supplier's service area."""
    zip_code = match.get("zip_code")
    return (
        zip_code in supplier_offer.get("ServiceAreas", []) if supplier_offer else False
    )


def check_capacity_available(supplier_offer):
    """Check if the supplier has available capacity."""
    return (
        supplier_offer.get("Used", 0) < supplier_offer.get("Capacity", 0)
        if supplier_offer
        else False
    )


def check_product_offered(match, supplier_offer):
    """Check if the supplier offers the matched product."""
    product_type = match.get("product_type")
    panel_name = match.get("panel_name")
    if supplier_offer:
        for offer in supplier_offer.get("Offers", []):
            if (
                offer["ProductType"] == product_type
                and offer["ProductName"] == panel_name
            ):
                return True
    return False


def check_price_correctness(match, pos_data, supplier_offer):
    """Check if the matched price is correct using pos.json, based on num_panels and CashPrice."""
    registration_id = match.get("registration_id")

    # Find corresponding POS entry
    pos_entry = next(
        (p for p in pos_data if p.get("registration_id") == registration_id), None
    )
    if not pos_entry:
        print(f"  No POS entry found for reg_id={registration_id}")
        return False

    num_panels = int(pos_entry.get("num_panels", 0))
    product_type = pos_entry.get("product_type", "").lower()
    panel_name = pos_entry.get("panel_name", "")
    product_price = int(pos_entry.get("product_price", 0))

    # Debug info
    print(
        f"Checking match: reg_id={registration_id}, supplier={pos_entry.get('supplier_id')}"
    )
    print(
        f"  num_panels={num_panels}, product_type={product_type}, panel_name={panel_name}"
    )
    print(f"  product_price={product_price}")

    if not supplier_offer:
        print("  No supplier offer found")
        return False

    for offer in supplier_offer.get("Offers", []):
        offer_product_type = offer.get("ProductType", "").lower()
        offer_product_name = offer.get("ProductName", "")
        print(
            f"  Checking offer: ProductType={offer_product_type}, ProductName={offer_product_name}"
        )

        if offer_product_type == product_type and offer_product_name == panel_name:
            for price in offer.get("ProductPrices", []):
                offer_quantity = int(price.get("Quantity", 0))
                print(f"    Checking price: Quantity={offer_quantity}")

                if offer_quantity == num_panels:
                    expected_price = int(price.get("CashPrice", 0))
                    print(
                        f"      expected_price={expected_price}, product_price={product_price}"
                    )
                    if product_price == expected_price:
                        print("      Price match found")
                        return True
    print("  No price match found")
    return False


def check_subsidy_eligibility(match, registration, pos_data):
    """Check if the registration is eligible for subsidies."""
    product_type = match.get("product_type")
    if registration and product_type == "Solar":
        lmi = registration.get("Contact_LowMediumIncome", 0)
        for po in pos_data:
            if po.get("ProductType") == product_type and (
                lmi == 0 or po.get("LMIAvailable", False)
            ):
                return True
    return False


def analyze_distribution(matches, registrations):
    """Analyze supplier distribution for shared zip codes."""
    shared_zip_codes = {"55407", "55419", "55447"}
    supplier_counts = defaultdict(int)

    # Get supplier capacities
    supplier_capacities = {"All Energy Solar": 7, "iSoalr": 5, "TruNorthSolar": 8}
    total_capacity = sum(supplier_capacities.values())
    expected_proportions = {
        sid: cap / total_capacity if total_capacity > 0 else 0
        for sid, cap in supplier_capacities.items()
    }

    # Count registrations in shared zip codes
    shared_zip_registrations = sum(
        1 for r in registrations if r.get("Contact_Zip") in shared_zip_codes
    )

    # Count matches in shared zip codes per supplier
    for match in matches:
        zip_code = match.get("zip_code")
        supplier_id = match.get("supplier_id")
        if zip_code in shared_zip_codes:
            supplier_counts[supplier_id] += 1

    # Prepare distribution results
    distribution = []
    for supplier_id in supplier_capacities:
        actual_count = supplier_counts.get(supplier_id, 0)
        actual_proportion = (
            actual_count / shared_zip_registrations
            if shared_zip_registrations > 0
            else 0
        )
        expected_proportion = expected_proportions.get(supplier_id, 0)
        distribution.append(
            {
                "supplier_id": supplier_id,
                "registrations": actual_count,
                "expected_proportion": expected_proportion,
                "actual_proportion": actual_proportion,
            }
        )
    return distribution, shared_zip_registrations


def analyze_registrations():
    """Main function to analyze registration matches."""
    parser = argparse.ArgumentParser(description="Analyze registration matches")
    parser.add_argument(
        "--matches", type=str, required=True, help="Path to matches JSON file"
    )
    parser.add_argument("--pos", type=str, required=True, help="Path to pos JSON file")
    parser.add_argument(
        "--offers", type=str, required=True, help="Path to offers JSON file"
    )
    parser.add_argument(
        "--registrations",
        type=str,
        required=True,
        help="Path to registrations JSON file",
    )
    args = parser.parse_args()

    try:
        # Load data
        matches = json.load(open(args.matches, "r"))
        pos_data = json.load(open(args.pos, "r"))
        offers = json.load(open(args.offers, "r"))
        registrations = json.load(open(args.registrations, "r"))

        # Normalize supplier IDs in matches and pos_data
        for match in matches:
            if match.get("supplier_id") == "iSolar":
                match["supplier_id"] = "iSoalr"
        for pos_entry in pos_data:
            if pos_entry.get("supplier_id") == "iSolar":
                pos_entry["supplier_id"] = "iSoalr"

        print(f"Total matches loaded: {len(matches)}")
        print(f"Total POS entries loaded: {len(pos_data)}")

        # Initialize counters
        total_registrations = len(matches)
        service_area_matches = 0
        capacity_available = 0
        product_offered = 0
        price_correct = 0
        subsidy_eligible = 0

        # Analyze each match
        for match in matches:
            registration_id = match.get("registration_id")
            supplier_id = match.get("supplier_id")

            # Find corresponding registration
            registration = next(
                (
                    r
                    for r in registrations
                    if r["RegistrationNumber"] == registration_id
                ),
                None,
            )

            # Find supplier offer
            supplier_offer = next(
                (s for s in offers["SupplierOffers"] if s["SupplierID"] == supplier_id),
                None,
            )

            # Evaluate statistics
            if check_service_area(match, supplier_offer):
                service_area_matches += 1
            if check_capacity_available(supplier_offer):
                capacity_available += 1
            if check_product_offered(match, supplier_offer):
                product_offered += 1
            if check_price_correctness(match, pos_data, supplier_offer):
                price_correct += 1
            if check_subsidy_eligibility(match, registration, pos_data):
                subsidy_eligible += 1

        # Distribution analysis
        distribution, shared_zip_registrations = analyze_distribution(
            matches, registrations
        )

        # Print statistics
        print("Statistics Report:")
        print("-----------------")
        print(
            f"1. Service Area Match: {service_area_matches}/{total_registrations} "
            f"({service_area_matches/total_registrations*100:.1f}%) registrations in supplier's service area"
        )
        print(
            f"2. Capacity Available: {capacity_available}/{total_registrations} "
            f"({capacity_available/total_registrations*100:.1f}%) suppliers with available capacity"
        )
        print(
            f"3. Product Offered: {product_offered}/{total_registrations} "
            f"({product_offered/total_registrations*100:.1f}%) registrations matched to offered products"
        )
        print(
            f"4. Price Correctness: {price_correct}/{total_registrations} "
            f"({price_correct/total_registrations*100:.1f}%) registrations with correct pricing"
        )
        print(
            f"5. Subsidy Eligibility: {subsidy_eligible}/{total_registrations} "
            f"({subsidy_eligible/total_registrations*100:.1f}%) registrations with eligible subsidies"
        )
        print("\n6. Distribution Analysis (Shared Zip Codes):")
        for dist in distribution:
            print(f"   Supplier {dist['supplier_id']}:")
            print(f"      Registrations: {dist['registrations']}")
            print(f"      Expected Proportion: {dist['expected_proportion']:.3f}")
            print(f"      Actual Proportion: {dist['actual_proportion']:.3f}")
        print(f"   Total Shared Zip Registrations: {shared_zip_registrations}")

    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in one of the input files")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    analyze_registrations()
