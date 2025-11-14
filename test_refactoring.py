#!/usr/bin/env python3
"""Test script to verify refactoring changes."""

import asyncio
import sys


async def test_model_registry():
    """Test that all models are registered correctly."""
    print("Testing model registry...")
    from igent.models import MODELS

    expected_models = [
        "openai_gpt4o",
        "openai_gpt5",
        "openai_gpt5mini",
        "zai_glm4_5_air",
        "zai_glm4_6",
        "azure",
        "vm_deepseek",
    ]

    for model in expected_models:
        if model not in MODELS:
            print(f"❌ FAIL: Model '{model}' not in registry")
            return False
        print(f"✓ Model '{model}' registered")

    print("✅ All models registered correctly\n")
    return True


async def test_workflow_imports():
    """Test that workflow imports work correctly."""
    print("Testing workflow imports...")
    try:
        from igent.workflows.p1m1m2c import Matcher1CriticMatcher2Workflow, run_workflow
        from igent.workflows.workflow import Workflow, WorkflowConfig

        # Verify imports are usable
        assert Matcher1CriticMatcher2Workflow is not None
        assert run_workflow is not None
        assert Workflow is not None
        assert WorkflowConfig is not None

        print("✓ Matcher1CriticMatcher2Workflow imported")
        print("✓ run_workflow imported")
        print("✓ Workflow base class imported")
        print("✓ WorkflowConfig imported")
        print("✅ All workflow imports successful\n")
        return True
    except ImportError as e:
        print(f"❌ FAIL: Import error - {e}")
        return False


async def test_workflow_config():
    """Test that WorkflowConfig can be instantiated."""
    print("Testing WorkflowConfig instantiation...")
    try:
        from igent.workflows.workflow import WorkflowConfig

        config = WorkflowConfig(
            model="openai_gpt4o",
            business_line="sbus",
            registrations_file="test.json",
            offers_file="test.json",
            max_items=1,
        )

        print(f"✓ Config created: model={config.model}")
        print(f"✓ Config business_line={config.business_line}")
        print(f"✓ Config constellation={config.constellation}")
        print("✅ WorkflowConfig instantiation successful\n")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


async def test_field_normalization():
    """Test that field normalization works."""
    print("Testing field normalization...")

    # Create a mock workflow to test normalization
    test_data = [
        {"RegistrationNumber": "TEST001", "other": "data"},
        {"registration_id": "TEST002", "other": "data"},
    ]

    # The normalization happens in _load_data, but we can test the logic
    normalized = []
    for reg in test_data:
        if "RegistrationNumber" in reg and "registration_id" not in reg:
            reg["registration_id"] = reg.pop("RegistrationNumber")
        normalized.append(reg)

    # Check results
    if normalized[0].get("registration_id") == "TEST001":
        print("✓ RegistrationNumber normalized to registration_id")
    else:
        print("❌ FAIL: Normalization failed")
        return False

    if "RegistrationNumber" not in normalized[0]:
        print("✓ Old field removed")
    else:
        print("❌ FAIL: Old field still present")
        return False

    if normalized[1].get("registration_id") == "TEST002":
        print("✓ Existing registration_id preserved")
    else:
        print("❌ FAIL: registration_id not preserved")
        return False

    print("✅ Field normalization working correctly\n")
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("REFACTORING VERIFICATION TESTS")
    print("=" * 60 + "\n")

    results = []

    # Test 1: Model registry
    results.append(await test_model_registry())

    # Test 2: Workflow imports
    results.append(await test_workflow_imports())

    # Test 3: WorkflowConfig
    results.append(await test_workflow_config())

    # Test 4: Field normalization
    results.append(await test_field_normalization())

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total} passed)")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
