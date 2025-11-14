# Timing Storage: CSV vs Alternatives

## Current CSV Limitations

### Problems:
1. **Schema evolution is painful** - Adding new timing columns requires manual updates
2. **Hierarchical data is flattened** - Can't represent nested timing naturally
3. **Limited metadata** - Hard to store context (model, constellation, date, etc.)
4. **No querying** - Can't easily filter/aggregate/analyze
5. **Merge conflicts** - Binary format issues with git
6. **Type safety** - Everything is string, need manual parsing

### Example of current CSV pain:
```csv
registration_id,matcher1_critic_time_seconds,phase1_agent_conversation_seconds,phase1_file_write_seconds,phase1_capacity_update_seconds,matcher2_time_seconds,phase2_agent_conversation_seconds,phase2_file_write_seconds
SPUS55557,34.522,33.200,0.500,0.822,15.893,14.900,0.993
```

**Issues:**
- 7+ columns per row (gets worse with more phases)
- Column names are cryptic
- No relationship between related timings
- Hard to add new metrics

---

## Better Alternatives

### Option 1: JSON Lines (JSONL) ⭐ RECOMMENDED
**Best for**: Easy implementation, git-friendly, queryable

```jsonl
{"registration_id": "SPUS55557", "timestamp": "2025-01-14T10:30:00Z", "model": "zai_glm4_5_air", "constellation": "p1m1m2c", "phases": {"phase1": {"total": 34.522, "agent_conversation": 33.200, "file_write": 0.500, "capacity_update": 0.822}, "phase2": {"total": 15.893, "agent_conversation": 14.900, "file_write": 0.993}}}
{"registration_id": "SPUS63654", "timestamp": "2025-01-14T10:31:00Z", "model": "zai_glm4_5_air", "constellation": "p1m1m2c", "phases": {"phase1": {"total": 32.100, "agent_conversation": 31.000, "file_write": 0.600, "capacity_update": 0.500}, "phase2": {"total": 14.200, "agent_conversation": 13.400, "file_write": 0.800}}}
```

**Pros:**
- ✅ Hierarchical data naturally represented
- ✅ Easy to add new fields (backward compatible)
- ✅ Git-friendly (line-based diffs)
- ✅ Can use `jq` for quick queries
- ✅ Type-safe (JSON schema)
- ✅ Easy to load in pandas: `pd.read_json(lines=True)`

**Cons:**
- ❌ Slightly larger file size
- ❌ Need JSON parsing (but Python has it built-in)

**Example queries:**
```bash
# Average phase1 time
cat timings.jsonl | jq -s 'map(.phases.phase1.total) | add/length'

# Filter by model
cat timings.jsonl | jq 'select(.model == "zai_glm4_5_air")'

# Export to CSV for Excel
cat timings.jsonl | jq -r '[.registration_id, .phases.phase1.total] | @csv'
```

---

### Option 2: SQLite Database
**Best for**: Complex queries, aggregations, multi-user

```python
# Schema
CREATE TABLE timings (
    id INTEGER PRIMARY KEY,
    registration_id TEXT,
    timestamp DATETIME,
    model TEXT,
    constellation TEXT,
    total_seconds REAL
);

CREATE TABLE phase_timings (
    id INTEGER PRIMARY KEY,
    timing_id INTEGER REFERENCES timings(id),
    phase_name TEXT,
    total_seconds REAL,
    agent_conversation_seconds REAL,
    file_write_seconds REAL,
    capacity_update_seconds REAL
);
```

**Pros:**
- ✅ Powerful querying (SQL)
- ✅ Proper relationships
- ✅ Aggregations built-in
- ✅ Concurrent access
- ✅ Type safety with schema

**Cons:**
- ❌ More complex setup
- ❌ Binary file (harder git diffs)
- ❌ Overkill for simple use case

---

### Option 3: Parquet Files
**Best for**: Big data, analytics, ML pipelines

```python
import pandas as pd
import pyarrow.parquet as pq

# Write
df.to_parquet('timings.parquet', compression='snappy')

# Read with filters
df = pd.read_parquet('timings.parquet',
                     filters=[('model', '=', 'zai_glm4_5_air')])
```

**Pros:**
- ✅ Extremely fast reads
- ✅ Columnar storage (efficient)
- ✅ Schema evolution support
- ✅ Great for ML/analytics

**Cons:**
- ❌ Binary format
- ❌ Requires `pyarrow` dependency
- ❌ Not human-readable

---

## Recommendation: JSONL

### Why JSONL is best for your use case:

1. **Easy migration from CSV** - Similar append-only pattern
2. **Git-friendly** - Line-based diffs work well
3. **Flexible schema** - Easy to add new timing metrics
4. **Human-readable** - Can inspect with text editor
5. **Tool-friendly** - Works with `jq`, pandas, Python stdlib
6. **Hierarchical** - Natural representation of timing tree
7. **Metadata-rich** - Easy to add context (model, date, git commit, etc.)

### Proposed JSON Structure:

```json
{
  "run_metadata": {
    "registration_id": "SPUS55557",
    "timestamp": "2025-01-14T10:30:00.123Z",
    "model": "zai_glm4_5_air",
    "constellation": "p1m1m2c",
    "git_commit": "c857d44",
    "max_items": 5
  },
  "timings": {
    "total_seconds": 50.415,
    "phases": {
      "phase1": {
        "total_seconds": 34.522,
        "breakdown": {
          "setup_seconds": 0.100,
          "agent_conversation_seconds": 33.200,
          "file_write_seconds": 0.500,
          "capacity_update_seconds": 0.822
        },
        "agents": ["matcher1", "critic"]
      },
      "phase2": {
        "total_seconds": 15.893,
        "breakdown": {
          "setup_seconds": 0.050,
          "agent_conversation_seconds": 14.900,
          "file_write_seconds": 0.993
        },
        "agents": ["matcher2"]
      }
    }
  }
}
```

---

## Implementation Plan

### 1. Create JSONL Writer (30 min)
```python
# igent/utils/jsonl_logger.py
import json
from datetime import datetime
from pathlib import Path

async def log_timing(filepath: str, registration_id: str, timings: dict, metadata: dict):
    """Append timing record to JSONL file."""
    record = {
        "run_metadata": {
            "registration_id": registration_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **metadata
        },
        "timings": timings
    }

    with open(filepath, 'a') as f:
        f.write(json.dumps(record) + '\n')
```

### 2. Update Workflow to Use JSONL (1 hour)
- Keep CSV for backward compatibility
- Add JSONL output in parallel
- Deprecate CSV in future

### 3. Analysis Tools (1 hour)
```python
# scripts/analyze_timings.py
import pandas as pd

# Load JSONL into DataFrame
df = pd.read_json('timings.jsonl', lines=True)

# Flatten nested structure
df = pd.json_normalize(df.to_dict('records'))

# Analyze
print(df['timings.phases.phase1.total_seconds'].describe())
print(df.groupby('run_metadata.model')['timings.total_seconds'].mean())
```

### 4. Keep CSV as Fallback (0 min)
- Still write CSV for Excel users
- JSONL becomes primary source of truth
- CSV has minimal columns (just totals)

---

## Migration Strategy

### Phase 1: Dual Output (Backward Compatible)
```python
# Write both formats
await log_timing_jsonl(jsonl_file, registration_id, timer.get_summary(), metadata)
update_runtime(run_id, filepath=csv_file, **timing_data)  # Keep existing CSV
```

### Phase 2: Deprecation Notice
```python
logger.warning("CSV timing output is deprecated, use JSONL instead")
```

### Phase 3: CSV Optional (Future)
```python
if config.enable_csv_output:  # Default: False
    update_runtime(...)
```

---

## Expected Benefits

### Before (CSV):
- Adding new metric = change code in 3 places
- Analyzing trends = manual Excel work
- Comparing models = error-prone
- Git diffs = unreadable

### After (JSONL):
- Adding new metric = add to dict (1 line)
- Analyzing trends = `jq` or pandas (seconds)
- Comparing models = simple groupby
- Git diffs = clean line changes

---

## Size Comparison

**CSV (current):**
```
180 bytes per row × 100 rows = 18 KB
```

**JSONL:**
```
400 bytes per row × 100 rows = 40 KB
```

**Size increase: 2.2x** - negligible for <1000 registrations

---

## Alternative: Hybrid Approach ⭐

**Best of both worlds:**

1. **JSONL for detailed timings** (primary)
2. **CSV for summary** (Excel-friendly)

```
data/results/
├── timings_detailed.jsonl  # Full hierarchical data
└── timings_summary.csv     # registration_id, total_time, model
```

CSV becomes a simple summary:
```csv
registration_id,total_seconds,model,timestamp
SPUS55557,50.415,zai_glm4_5_air,2025-01-14T10:30:00Z
```

JSONL has all the details for deep analysis.

---

## Recommendation

**Use JSONL + minimal CSV:**

1. ✅ Implement JSONL logging (30 min)
2. ✅ Simplify CSV to summary only (15 min)
3. ✅ Add analysis script (30 min)
4. ✅ Update documentation (15 min)

**Total: ~1.5 hours for much better timing storage**

Want me to implement this?
