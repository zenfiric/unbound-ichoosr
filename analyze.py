import argparse
import json
from collections import defaultdict


def load_json(file_path):
    """Load a JSON file from the given path."""
    with open(file_path, "r") as f:
        return json.load(f)


def check_service_area(zip_code, supplier):
    """Check if the registration's zip code is in the supplier's service area."""
    return zip_code in supplier["ServiceAreas"]


def check_capacity(supplier):
    """Check if the supplier has available capacity."""
    return supplier["Used"] < supplier["Capacity"]


def check_product_offered(product_type, panel_name, supplier):
    """Check if the supplier offers the specified product."""
    for offer in supplier["Offers"]:
        if offer["ProductType"] == product_type and offer["ProductName"] == panel_name:
            return True
    return False


def check_price_correctness(
    num_panels, payment_type, product_price, product_type, panel_name, supplier
):
    """Check if the registration's price matches the supplier's offer."""
    if not product_price:
        return False
    for offer in supplier["Offers"]:
        if offer["ProductType"] == product_type and offer["ProductName"] == panel_name:
            for price in offer["ProductPrices"]:
                if price["Quantity"] == num_panels:
                    expected_price = (
                        price["CashPrice"]
                        if payment_type == "CashPrice"
                        else price["LoanInstallment"]
                    )
                    if payment_type == "LoanInstallment":
                        return price["LoanInstallment"] > 0
                    return product_price == expected_price
    return False


def check_subsidy_eligibility(product_type, subsidies):
    """Check if the registration is eligible for subsidies."""

    def is_federal_solar_subsidy(subsidy_name):
        core_terms = ["Federal Residential Clean Energy Credit", "25D"]
        return any(term in subsidy_name for term in core_terms)

    if product_type != "Solar":
        return False
    return any(is_federal_solar_subsidy(subsidy) for subsidy in subsidies)


def analyze_distribution(matches, supplier_info, stats):
    """Analyze the distribution of registrations across suppliers."""
    total_capacity = sum(s["Capacity"] for s in supplier_info.values())
    distribution_stats = {}
    for supplier_id, reg_list in stats["distribution"].items():
        supplier = supplier_info[supplier_id]
        expected_proportion = (
            supplier["Capacity"] / total_capacity if total_capacity > 0 else 0
        )
        actual_proportion = len(reg_list) / len(matches) if matches else 0
        distribution_stats[supplier_id] = {
            "registrations": len(reg_list),
            "expected_proportion": expected_proportion,
            "actual_proportion": actual_proportion,
        }
    return distribution_stats


def analyze_registrations(matches_path, pos_path, offers_path, registrations_path):
    """Analyze registrations and compute statistics."""
    # Load data
    matches = load_json(matches_path)
    pos = load_json(pos_path)
    offers = load_json(offers_path)
    registrations = load_json(registrations_path)

    # Create supplier lookup
    supplier_info = {s["SupplierID"]: s for s in offers["SupplierOffers"]}

    # Initialize stats
    stats = {
        "service_area_match": {"total": 0, "matched": 0},
        "capacity_available": {"total": 0, "has_capacity": 0},
        "product_offered": {"total": 0, "offered": 0},
        "price_correct": {"total": 0, "correct": 0},
        "subsidy_eligible": {"total": 0, "eligible": 0},
        "distribution": defaultdict(list),
    }

    # Analyze each registration
    for match, po in zip(matches, pos):
        reg_id = match["registration_id"]
        supplier_id = match["supplier_id"]
        zip_code = match["zip_code"]
        num_panels = int(match["num_panels"])
        product_type = match["product_type"]
        panel_name = match["panel_name"]
        payment_type = match["payment_type"]
        product_price = int(po["product_price"]) if "product_price" in po else None
        subsidies = po.get("eligible_subsidies", [])

        # Find registration details
        reg = next(
            (r for r in registrations if r["RegistrationNumber"] == reg_id), None
        )
        if not reg:
            continue

        supplier = supplier_info.get(supplier_id)
        if not supplier:
            continue

        stats["service_area_match"]["total"] += 1
        stats["capacity_available"]["total"] += 1
        stats["product_offered"]["total"] += 1
        stats["price_correct"]["total"] += 1
        stats["subsidy_eligible"]["total"] += 1

        # 1. Service area check
        if check_service_area(zip_code, supplier):
            stats["service_area_match"]["matched"] += 1

        # 2. Capacity check
        if check_capacity(supplier):
            stats["capacity_available"]["has_capacity"] += 1

        # 3. Product offered check
        if check_product_offered(product_type, panel_name, supplier):
            stats["product_offered"]["offered"] += 1

        # 4. Price correctness check
        if check_price_correctness(
            num_panels, payment_type, product_price, product_type, panel_name, supplier
        ):
            stats["price_correct"]["correct"] += 1

        # 5. Subsidy eligibility check
        if check_subsidy_eligibility(product_type, subsidies):
            stats["subsidy_eligible"]["eligible"] += 1

        # 6. Distribution tracking
        stats["distribution"][supplier_id].append(reg_id)

    # 6. Distribution analysis
    distribution_stats = analyze_distribution(matches, supplier_info, stats)

    # Print statistics
    print("Statistics Report:")
    print("-----------------")

    # Service area match
    sa = stats["service_area_match"]
    print(
        f"1. Service Area Match: {sa['matched']}/{sa['total']} "
        f"({sa['matched']/sa['total']*100:.1f}%) registrations in supplier's service area"
    )

    # Capacity availability
    ca = stats["capacity_available"]
    print(
        f"2. Capacity Available: {ca['has_capacity']}/{sa['total']} "
        f"({ca['has_capacity']/sa['total']*100:.1f}%) suppliers with available capacity"
    )

    # Product offered
    po = stats["product_offered"]
    print(
        f"3. Product Offered: {po['offered']}/{sa['total']} "
        f"({po['offered']/sa['total']*100:.1f}%) registrations matched to offered products"
    )

    # Price correctness
    pc = stats["price_correct"]
    print(
        f"4. Price Correctness: {pc['correct']}/{sa['total']} "
        f"({pc['correct']/sa['total']*100:.1f}%) registrations with correct pricing"
    )

    # Subsidy eligibility
    se = stats["subsidy_eligible"]
    print(
        f"5. Subsidy Eligibility: {se['eligible']}/{sa['total']} "
        f"({se['eligible']/sa['total']*100:.1f}%) registrations with eligible subsidies"
    )

    # Distribution analysis
    print("\n6. Distribution Analysis:")
    for supplier_id, ds in distribution_stats.items():
        print(f"   Supplier {supplier_id}:")
        print(f"      Registrations: {ds['registrations']}")
        print(f"      Expected Proportion: {ds['expected_proportion']:.3f}")
        print(f"      Actual Proportion: {ds['actual_proportion']:.3f}")


def main():
    """Parse command-line arguments and run the analysis."""
    parser = argparse.ArgumentParser(description="Analyze solar registration data.")
    parser.add_argument(
        "--matches",
        default="data/demo2/p1m1m2c_sbus_openai_matches.json",
        help="Path to matches JSON file",
    )
    parser.add_argument(
        "--pos",
        default="data/demo2/p1m1m2c_sbus_openai_pos.json",
        help="Path to pos JSON file",
    )
    parser.add_argument(
        "--offers",
        default="data/demo2/sbus_mock_offers.json",
        help="Path to offers JSON file",
    )
    parser.add_argument(
        "--registrations",
        default="data/demo2/sbus_mock_registrations_10.json",
        help="Path to registrations JSON file",
    )

    args = parser.parse_args()

    analyze_registrations(args.matches, args.pos, args.offers, args.registrations)


if __name__ == "__main__":
    main()
