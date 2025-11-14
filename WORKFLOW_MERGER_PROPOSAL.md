# Workflow Configuration Analysis & Merger Recommendation

## Executive Summary

**Problem:** 4 separate workflow implementations with ~400 lines of duplicated code

**Solution:** Single `ConfigurableWorkflow` class with YAML-based constellation configs

**Benefits:** 50% code reduction, easier maintenance, trivial to add new constellations

---

## Current Workflow Implementations

### 1. **p1m1m2c** - One Critic, Two Phases
**File:** `p1m1m2c.py`
**Structure:**
- Phase 1: Matcher1 + Critic (2 agents)
- Capacity Update
- Phase 2: Matcher2 (1 agent, no critic)

**Prompts:** `variant="one_critic"`
**Timing:** `matcher1_critic_time`, `matcher2_time`

### 2. **p1m1c1m2c2** - Single Group, All Agents
**File:** `p1m1c1m2c2.py`
**Structure:**
- Single group: Matcher1 + Critic1 + Matcher2 + Critic2 (4 agents)
- Capacity updated after group completes

**Prompts:** `variant=None` (default)
**Timing:** `group_time` (total)

### 3. **p1m1_p2m2** - No Critics, Two Phases
**File:** `p1m1_p2m2.py`
**Structure:**
- Phase 1: Matcher1 (1 agent)
- Capacity Update
- Phase 2: Matcher2 (1 agent)

**Prompts:** `variant="no_critic"`
**Timing:** `matcher1_time`, `matcher2_time`

### 4. **p1m1c1_p2m2c2** - Two Critics, Two Phases
**File:** `p1m1c1_p2m2c2.py`
**Structure:**
- Phase 1: Matcher1 + Critic1 (2 agents)
- Capacity Update
- Phase 2: Matcher2 + Critic2 (2 agents)

**Prompts:** `variant=None` (default)
**Timing:** `pair1_time`, `pair2_time`

---

## Configuration Comparison Matrix

| Constellation | Phase 1 Agents | Phase 2 Agents | Capacity Update | Prompts | Timing Columns |
|---------------|---------------|----------------|-----------------|---------|----------------|
| p1m1m2c | Matcher1+Critic | Matcher2 | Between phases | one_critic | m1c_time, m2_time |
| p1m1c1m2c2 | All 4 in one group | N/A | After group | default | group_time |
| p1m1_p2m2 | Matcher1 | Matcher2 | Between phases | no_critic | m1_time, m2_time |
| p1m1c1_p2m2c2 | Matcher1+Critic1 | Matcher2+Critic2 | Between phases | default | pair1_time, pair2_time |

---

## Code Duplication Analysis

### Duplicated Patterns:

1. **Workflow initialization** (~40 lines each) - CSV initialization, prompt loading, file paths, data loading
2. **Capacity update logic** (~10 lines each) - Update supplier capacity, reload offers, error handling
3. **Agent creation** (~5 lines per phase) - get_agents() calls with prompts dict
4. **Message construction** (~15 lines per phase) - Registration/offers data formatting, incentives, role instructions
5. **Timing & logging** (~10 lines per phase) - start_time, execution time calculation, logger calls

### Total Duplication: ~400 lines across 4 files

---

## Recommended Solution: Configuration-Driven Workflow

### Example YAML Configuration

```yaml
# config/constellations/p1m1m2c.yaml
name: "p1m1m2c"
description: "Matcher1 with Critic, then Matcher2 solo"

phases:
  - name: "phase1"
    agents:
      - role: "matcher1"
        prompt_key: "a_matcher"
      - role: "critic"
        prompt_key: "critic"
    capacity_update: false

  - name: "phase2"
    agents:
      - role: "matcher2"
        prompt_key: "b_matcher"
    capacity_update: true  # Update capacity BEFORE this phase

prompts:
  variant: "one_critic"

timing:
  columns:
    - "matcher1_critic_time_seconds"
    - "matcher2_time_seconds"
```

---

## Migration Benefits

### ✅ Advantages:

1. **Single Implementation** - One workflow class instead of 4
2. **Easy to Add Constellations** - Just add YAML config
3. **Reduced Duplication** - ~400 lines → ~200 lines total
4. **Better Maintainability** - Fix bugs once, applies everywhere
5. **Clearer Configuration** - YAML is self-documenting
6. **Consistent Behavior** - Same code path for all configs
7. **Easier Testing** - Test one implementation thoroughly

### ⚠️ Considerations:

1. **Initial Migration Effort** - Need to refactor existing code
2. **YAML Validation** - Need schema validation for configs
3. **Backward Compatibility** - Old function signatures still work
4. **Testing Coverage** - Need to test all 4 constellations

---

## Migration Strategy

### Phase 1: Create Infrastructure
1. Create `config/constellations/` directory
2. Write YAML config for each constellation
3. Implement `ConfigurableWorkflow` class
4. Add YAML schema validation

### Phase 2: Create Compatibility Layer
1. Keep old workflow files but mark as deprecated
2. Add wrapper functions that call `ConfigurableWorkflow`
3. Update documentation

### Phase 3: Migrate Tests
1. Create comprehensive test suite for `ConfigurableWorkflow`
2. Test all 4 constellations
3. Compare outputs with old implementations

### Phase 4: Deprecate Old Files
1. Add deprecation warnings to old workflows
2. Update all examples to use new API
3. After grace period, remove old files

---

## Recommended File Structure

```
igent/
├── workflows/
│   ├── configurable_workflow.py    # New unified implementation
│   ├── workflow.py                  # Base class (unchanged)
│   ├── p1m1m2c.py                  # Deprecated wrapper
│   ├── p1m1c1m2c2.py              # Deprecated wrapper
│   ├── p1m1_p2m2.py               # Deprecated wrapper
│   └── p1m1c1_p2m2c2.py           # Deprecated wrapper
config/
├── constellations/
│   ├── p1m1m2c.yaml
│   ├── p1m1c1m2c2.yaml
│   ├── p1m1_p2m2.yaml
│   └── p1m1c1_p2m2c2.yaml
└── schema/
    └── constellation.schema.json
```

---

## Example Usage After Migration

```python
# New API (recommended)
from igent.workflows.configurable_workflow import run_workflow

await run_workflow(
    constellation="p1m1m2c",
    model="zai_glm4_5_air",
    registrations_file="data/sbus/registrations/full_dataset.json",
    offers_file="data/sbus/offers/base_offers.json",
    max_items=10
)

# Old API (still works via compatibility wrapper)
from igent.workflows.p1m1m2c import run_workflow

await run_workflow(
    model="zai_glm4_5_air",
    # ... same parameters
)
```

---

## Conclusion

**Recommendation:** Implement the unified `ConfigurableWorkflow` class with YAML-based constellation configs.

This will:
- Reduce code duplication by ~50%
- Make adding new constellations trivial
- Improve maintainability significantly
- Keep backward compatibility during migration

The investment in refactoring will pay off quickly as the codebase becomes easier to understand, test, and extend.
