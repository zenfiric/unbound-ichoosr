# Smart Defaults for Workflow Configuration

## Overview

The `WorkflowConfig` class now supports **smart defaults** that automatically construct file paths based on a conventional directory structure. This eliminates repetitive parameter passing and makes the API much more concise.

## Usage

### Before (Verbose API)

```python
from igent.workflows import run_workflow

await run_workflow(
    constellation="p1m1m2c",
    model="zai_glm4_5_air",
    business_line="sbus",
    registrations_file="../data/sbus/registrations/overlap_only.json",
    offers_file="../data/sbus/offers/base_offers.json",
    matches_file="../data/sbus/results/p1m1m2c_matches.json",
    pos_file="../data/sbus/results/p1m1m2c_pos.json",
    stats_file="../data/sbus/results/p1m1m2c_stats.csv",
    max_items=5
)
```

### After (Concise API with Smart Defaults)

```python
from igent.workflows import run_workflow

await run_workflow(
    constellation="p1m1m2c",
    model="zai_glm4_5_air",
    business_line="sbus",
    data_dir="../data/sbus",
    scenario="overlap_only",
    max_items=5
)
```

## How It Works

When you provide `data_dir` and `scenario` parameters, `WorkflowConfig` automatically constructs paths using this convention:

```
{data_dir}/
├── registrations/
│   └── {scenario}.json          → registrations_file
├── offers/
│   └── base_offers.json         → offers_file
└── results/
    ├── {constellation}_matches.json  → matches_file
    ├── {constellation}_pos.json      → pos_file
    └── {constellation}_stats.csv     → stats_file
```

### Example Path Construction

Given:
- `data_dir = "data/sbus"`
- `scenario = "overlap_only"`
- `constellation = "p1m1m2c"`

The following paths are automatically generated:

| Parameter | Generated Path |
|-----------|---------------|
| `registrations_file` | `data/sbus/registrations/overlap_only.json` |
| `offers_file` | `data/sbus/offers/base_offers.json` |
| `matches_file` | `data/sbus/results/p1m1m2c_matches.json` |
| `pos_file` | `data/sbus/results/p1m1m2c_pos.json` |
| `stats_file` | `data/sbus/results/p1m1m2c_stats.csv` |

## Backward Compatibility

The smart defaults feature is **fully backward compatible**. You can still use explicit file paths if needed:

```python
# Explicit paths still work
await run_workflow(
    constellation="p1m1m2c",
    model="zai_glm4_5_air",
    business_line="sbus",
    registrations_file="custom/path/registrations.json",
    offers_file="custom/path/offers.json",
    matches_file="custom/path/matches.json",
    pos_file="custom/path/pos.json",
    stats_file="custom/path/stats.csv",
    max_items=5
)
```

## Partial Overrides

You can mix smart defaults with explicit paths. Smart defaults are only applied to parameters that are `None`:

```python
# Use smart defaults for most files, but override offers_file
await run_workflow(
    constellation="p1m1m2c",
    model="zai_glm4_5_air",
    business_line="sbus",
    data_dir="../data/sbus",
    scenario="overlap_only",
    offers_file="custom/special_offers.json",  # Override this one
    max_items=5
)
```

In this example:
- `registrations_file`, `matches_file`, `pos_file`, and `stats_file` use smart defaults
- `offers_file` uses the explicit path provided

## Implementation Details

The smart defaults are implemented in `WorkflowConfig.__post_init__()`:

```python
@dataclass
class WorkflowConfig:
    model: str
    constellation: Literal["p1m1m2c", "p1m1c1m2c2", "p1m1c1_p2m2c2", "p1m1_p2m2"] = "p1m1m2c"
    business_line: str = "sbus"

    # Smart defaults option 1: Use data_dir + scenario
    data_dir: str | None = None  # e.g., "data/sbus"
    scenario: str | None = None  # e.g., "overlap_only"

    # Smart defaults option 2: Explicit paths (backward compatibility)
    registrations_file: str | None = None
    offers_file: str | None = None
    # ... other file parameters

    def __post_init__(self):
        """Apply smart defaults for file paths if data_dir and scenario are provided."""
        if self.data_dir and self.scenario:
            base = Path(self.data_dir)

            if self.registrations_file is None:
                self.registrations_file = str(base / "registrations" / f"{self.scenario}.json")

            if self.offers_file is None:
                self.offers_file = str(base / "offers" / "base_offers.json")

            # ... apply other defaults
```

## Testing

A comprehensive test suite is available in `test_smart_defaults.py`:

```bash
python test_smart_defaults.py
```

The test suite verifies:
1. ✅ Smart defaults generate correct paths
2. ✅ Explicit paths still work (backward compatibility)
3. ✅ Partial overrides work correctly (smart defaults + explicit paths)

## Benefits

1. **Reduced Boilerplate**: 5 file path parameters → 2 directory parameters
2. **Less Error-Prone**: Conventional structure reduces typos and path mistakes
3. **Easier to Understand**: Clear data organization pattern
4. **Backward Compatible**: Existing code continues to work without changes
5. **Flexible**: Can still override individual paths when needed

## Migration Guide

### For New Code

Use the simplified API with `data_dir` and `scenario`:

```python
await run_workflow(
    constellation="p1m1m2c",
    model="zai_glm4_5_air",
    business_line="sbus",
    data_dir="../data/sbus",
    scenario="overlap_only",
    max_items=5
)
```

### For Existing Code

No changes required! Existing code using explicit file paths will continue to work:

```python
# This still works exactly as before
await run_workflow(
    model="zai_glm4_5_air",
    business_line="sbus",
    registrations_file="../data/sbus/registrations/overlap_only.json",
    offers_file="../data/sbus/offers/base_offers.json",
    matches_file="../data/sbus/results/matches.json",
    pos_file="../data/sbus/results/pos.json",
    stats_file="../data/sbus/results/stats.csv",
    max_items=5
)
```

### Gradual Migration

You can migrate one workflow at a time by switching to the smart defaults API when convenient.

## Related Features

This smart defaults feature complements the other recent improvements:

1. **YAML-based Constellations** (see `config/constellations/`) - Define agent patterns declaratively
2. **Unified ConfigurableWorkflow** (see `WORKFLOW_MERGER_PROPOSAL.md`) - Single workflow implementation for all patterns
3. **Scenario-based Configuration** (see `data/sbus/scenarios/`) - Organize test data by scenario

Together, these features provide a clean, flexible, and maintainable workflow API.
