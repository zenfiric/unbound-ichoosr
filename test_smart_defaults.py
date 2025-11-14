#!/usr/bin/env python3
"""Test script to verify smart defaults in WorkflowConfig."""

from igent.workflows.workflow import WorkflowConfig


def test_smart_defaults():
    """Test that smart defaults correctly generate file paths."""
    print("Testing smart defaults with data_dir and scenario...")

    config = WorkflowConfig(
        model="test_model",
        constellation="p1m1m2c",
        business_line="sbus",
        data_dir="data/sbus",
        scenario="overlap_only",
        max_items=5,
    )

    # Expected paths
    expected = {
        "registrations_file": "data/sbus/registrations/overlap_only.json",
        "offers_file": "data/sbus/offers/base_offers.json",
        "capacity_file": "data/sbus/capacity/overlap_only.json",
        "matches_file": "data/sbus/results/p1m1m2c_matches.json",
        "pos_file": "data/sbus/results/p1m1m2c_pos.json",
        "stats_file": "data/sbus/results/p1m1m2c_stats.csv",
    }

    # Check each path
    success = True
    for key, expected_value in expected.items():
        actual_value = getattr(config, key)
        if actual_value == expected_value:
            print(f"✓ {key}: {actual_value}")
        else:
            print(f"✗ {key}: expected '{expected_value}', got '{actual_value}'")
            success = False

    return success


def test_explicit_paths():
    """Test that explicit paths still work (backward compatibility)."""
    print("\nTesting explicit paths (backward compatibility)...")

    config = WorkflowConfig(
        model="test_model",
        constellation="p1m1m2c",
        business_line="sbus",
        registrations_file="custom/registrations.json",
        offers_file="custom/offers.json",
        capacity_file="custom/capacity.json",
        matches_file="custom/matches.json",
        pos_file="custom/pos.json",
        stats_file="custom/stats.csv",
        max_items=5,
    )

    # Check paths weren't overridden
    expected = {
        "registrations_file": "custom/registrations.json",
        "offers_file": "custom/offers.json",
        "capacity_file": "custom/capacity.json",
        "matches_file": "custom/matches.json",
        "pos_file": "custom/pos.json",
        "stats_file": "custom/stats.csv",
    }

    success = True
    for key, expected_value in expected.items():
        actual_value = getattr(config, key)
        if actual_value == expected_value:
            print(f"✓ {key}: {actual_value}")
        else:
            print(f"✗ {key}: expected '{expected_value}', got '{actual_value}'")
            success = False

    return success


def test_partial_override():
    """Test that smart defaults + explicit paths work together."""
    print("\nTesting partial override (smart defaults + explicit paths)...")

    config = WorkflowConfig(
        model="test_model",
        constellation="p1m1m2c",
        business_line="sbus",
        data_dir="data/sbus",
        scenario="overlap_only",
        # Override just the offers file
        offers_file="custom/special_offers.json",
        max_items=5,
    )

    # Check mixed paths
    expected = {
        "registrations_file": "data/sbus/registrations/overlap_only.json",  # Smart default
        "offers_file": "custom/special_offers.json",  # Explicit override
        "capacity_file": "data/sbus/capacity/overlap_only.json",  # Smart default
        "matches_file": "data/sbus/results/p1m1m2c_matches.json",  # Smart default
        "pos_file": "data/sbus/results/p1m1m2c_pos.json",  # Smart default
        "stats_file": "data/sbus/results/p1m1m2c_stats.csv",  # Smart default
    }

    success = True
    for key, expected_value in expected.items():
        actual_value = getattr(config, key)
        if actual_value == expected_value:
            print(f"✓ {key}: {actual_value}")
        else:
            print(f"✗ {key}: expected '{expected_value}', got '{actual_value}'")
            success = False

    return success


if __name__ == "__main__":
    print("=" * 70)
    print("WorkflowConfig Smart Defaults Test Suite")
    print("=" * 70)

    results = []
    results.append(("Smart Defaults", test_smart_defaults()))
    results.append(("Explicit Paths", test_explicit_paths()))
    results.append(("Partial Override", test_partial_override()))

    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("\n🎉 All tests passed!")
        exit(0)
    else:
        print("\n⚠️  Some tests failed!")
        exit(1)
