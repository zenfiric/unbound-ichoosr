# Capacity Tracking Architecture

## Overview

Supplier capacity tracking has been separated from offer files to maintain data immutability and clarity. This separation ensures that:

1. **Offers files remain immutable** - They contain only supplier offer details (rates, terms, service areas)
2. **Capacity is tracked separately** - A dedicated capacity file tracks usage and availability
3. **Cleaner architecture** - Clear separation of concerns between static offer data and dynamic capacity state

## File Structure

### Before (Coupled)
```
data/sbus/offers/
└── base_offers.json          # Contains both offer details AND capacity tracking
    {
      "SupplierOffers": [
        {
          "SupplierID": "All Energy Solar",
          "Capacity": 70,
          "Used": 5,              ❌ Mixed with offer data
          "UsedPct": 0.07,        ❌ Mixed with offer data
          "InterestRate": 7.73,
          "ServiceAreas": [...]
        }
      ]
    }
```

### After (Separated)
```
data/sbus/
├── offers/
│   └── base_offers.json      # Immutable offer details only
│       {
│         "SupplierOffers": [
│           {
│             "SupplierID": "All Energy Solar",
│             "Capacity": 70,
│             "InterestRate": 7.73,
│             "ServiceAreas": [...]
│             // No Used/UsedPct fields
│           }
│         ]
│       }
│
└── capacity/
    └── overlap_only.json     # Dynamic capacity tracking
        {
          "All Energy Solar": {
            "SupplierID": "All Energy Solar",
            "Capacity": 70,
            "Used": 5,            ✅ Tracked separately
            "UsedPct": 0.07       ✅ Tracked separately
          }
        }
```

## Benefits

1. **Immutable Offers** - Offer files never change during workflow execution
2. **Scenario-Specific Capacity** - Each scenario can have its own capacity tracking
3. **Easier Testing** - Reset capacity without touching offer data
4. **Clearer Intent** - Separation of static configuration from runtime state
5. **Better Git Diffs** - Only capacity files change during experiments

## Usage

### Workflow Configuration

The workflow automatically uses capacity files via smart defaults:

```python
from igent.workflows import run_workflow

await run_workflow(
    constellation="p1m1m2c",
    model="zai_glm4_5_air",
    business_line="sbus",
    data_dir="../data/sbus",
    scenario="overlap_only",  # Automatically uses capacity/overlap_only.json
    max_items=5
)
```

The `capacity_file` is automatically set to `{data_dir}/capacity/{scenario}.json`.

### Manual Configuration

You can also specify the capacity file explicitly:

```python
await run_workflow(
    constellation="p1m1m2c",
    model="zai_glm4_5_air",
    business_line="sbus",
    registrations_file="data/sbus/registrations/overlap_only.json",
    offers_file="data/sbus/offers/base_offers.json",
    capacity_file="data/sbus/capacity/overlap_only.json",  # Explicit
    max_items=5
)
```

## API Reference

### `capacity_tracker.py` Module

#### `initialize_capacity_file(offers_file, capacity_file)`
Creates a capacity file from an offers file if it doesn't exist.

```python
from igent.tools.capacity_tracker import initialize_capacity_file

# Automatically called by update_supplier_capacity
capacity_data = await initialize_capacity_file(
    offers_file="data/sbus/offers/base_offers.json",
    capacity_file="data/sbus/capacity/overlap_only.json"
)
```

#### `update_supplier_capacity(match_data, offers_file, capacity_file)`
Updates capacity tracking for a supplier based on match data.

```python
from igent.tools.capacity_tracker import update_supplier_capacity

# Update capacity after a match
result = await update_supplier_capacity(
    match_data={"supplier_id": "All Energy Solar", ...},
    offers_file="data/sbus/offers/base_offers.json",
    capacity_file="data/sbus/capacity/overlap_only.json"
)
```

**Note**: This function updates the capacity file, NOT the offers file.

#### `get_available_capacity(capacity_file)`
Retrieves current capacity data for all suppliers.

```python
from igent.tools.capacity_tracker import get_available_capacity

capacity_data = await get_available_capacity(
    capacity_file="data/sbus/capacity/overlap_only.json"
)

# Returns:
# {
#   "All Energy Solar": {"SupplierID": "...", "Capacity": 70, "Used": 5, "UsedPct": 0.07},
#   "iSoalr": {"SupplierID": "...", "Capacity": 50, "Used": 0, "UsedPct": 0.0},
#   ...
# }
```

#### `reset_capacity(capacity_file)`
Resets all supplier capacity to 0.

```python
from igent.tools.capacity_tracker import reset_capacity

result = await reset_capacity(
    capacity_file="data/sbus/capacity/overlap_only.json"
)
```

## Scripts

### Migration Script

Use this **once** to migrate existing offers files to the new structure:

```bash
# Migrate all offers files
python scripts/migrate_capacity_tracking.py --all

# Migrate specific file
python scripts/migrate_capacity_tracking.py data/sbus/offers/base_offers.json
```

This script:
1. Extracts `Used` and `UsedPct` from offers files
2. Creates capacity tracking files in `data/sbus/capacity/`
3. Removes `Used` and `UsedPct` from offers files

**Warning**: This modifies offers files. Commit your changes first!

### Reset Script

Reset capacity tracking before running workflows:

```bash
# Reset all capacity files
python scripts/reset_capacity.py --all

# Reset specific file
python scripts/reset_capacity.py data/sbus/capacity/overlap_only.json
```

**Note**: This only resets capacity files, not offers files.

## Migration Guide

### Step 1: Backup Your Data
```bash
git add -A
git commit -m "Backup before capacity tracking migration"
```

### Step 2: Run Migration
```bash
python scripts/migrate_capacity_tracking.py --all
```

### Step 3: Verify Changes
```bash
# Check offers files no longer contain Used/UsedPct
cat data/sbus/offers/base_offers.json | grep "Used"
# Should return nothing

# Check capacity files exist
ls data/sbus/capacity/
# Should show: capacity.json, capacity_no_aes_battery.json
```

### Step 4: Update Workflows
The workflows automatically use the new capacity tracking if you're using the unified API. No code changes needed!

### Step 5: Commit Changes
```bash
git add -A
git commit -m "Migrate to separate capacity tracking"
```

## Capacity File Format

### Structure
```json
{
  "SupplierID": {
    "SupplierID": "string",
    "Capacity": "number (max registrations)",
    "Used": "number (current usage)",
    "UsedPct": "number (0.0 to 1.0)"
  }
}
```

### Example
```json
{
  "All Energy Solar": {
    "SupplierID": "All Energy Solar",
    "Capacity": 70,
    "Used": 5,
    "UsedPct": 0.07
  },
  "iSoalr": {
    "SupplierID": "iSoalr",
    "Capacity": 50,
    "Used": 0,
    "UsedPct": 0.0
  },
  "TruNorthSolar": {
    "SupplierID": "TruNorthSolar",
    "Capacity": 80,
    "Used": 15,
    "UsedPct": 0.19
  }
}
```

## Workflow Integration

The capacity tracking integrates seamlessly with the workflow:

```python
# In workflow._update_capacity()
async def _update_capacity(self, matches: list[dict], run_id: str) -> list[dict] | None:
    """Update supplier capacity and reload offers."""
    try:
        # Updates capacity file, not offers file
        result = await update_supplier_capacity(
            matches,
            self.config.offers_file,      # Used for initialization only
            self.config.capacity_file      # Updated with new capacity
        )
        logger.info("Capacity update: %s", result)

        # Offers are reloaded but remain unchanged
        offers = await read_json(self.config.offers_file)
        return offers
    except ValueError as e:
        logger.error("Error updating capacity: %s", e)
        return None
```

## Smart Defaults

Capacity files follow the smart defaults pattern:

| Input | Capacity File Path |
|-------|-------------------|
| `data_dir="data/sbus"`, `scenario="overlap_only"` | `data/sbus/capacity/overlap_only.json` |
| `data_dir="data/sbus"`, `scenario="full_dataset"` | `data/sbus/capacity/full_dataset.json` |
| `data_dir="data/sbus"`, `scenario="no_battery"` | `data/sbus/capacity/no_battery.json` |

## Troubleshooting

### Capacity File Not Found
If you get "Capacity file not found", it will be automatically created from the offers file on first use.

### Capacity Exceeded Error
```
ValueError: Supplier All Energy Solar capacity exceeded: 71 > 70
```

This means the supplier has reached their capacity limit. Reset capacity or increase the limit in the capacity file.

### Offers File Modified During Workflow
If your offers file is being modified during workflow runs, you may still be using the old `update_supplier_capacity` from `igent/tools/update_supplier_capacity.py`. Make sure you're importing from `igent.tools.capacity_tracker` instead.

## Related Documentation

- [SMART_DEFAULTS.md](./SMART_DEFAULTS.md) - Smart defaults configuration
- [WORKFLOW_MERGER_PROPOSAL.md](./WORKFLOW_MERGER_PROPOSAL.md) - Unified workflow architecture
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Overall system architecture
