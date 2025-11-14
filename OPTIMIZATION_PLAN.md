# Performance Optimization Plan

## Current Performance
- **Per registration**: ~50 seconds (phase1: 34s, phase2: 16s)
- **For 5 registrations**: ~4 minutes total
- **Bottleneck**: 95% of time is in AI API calls (not our code)

## Optimization Opportunities

### 1. ✅ **High Impact: Cache Capacity Data** (EASY - 5-10% speedup)
**Current**: Load capacity file from disk on every update
**Optimized**: Cache in memory, only load once per workflow run

```python
# Before: Load from disk every time (5 registrations × 2 = 10 file reads)
async def update_supplier_capacity(...):
    capacity_data = await initialize_capacity_file(...)  # Disk I/O every time

# After: Load once, keep in memory
class Workflow:
    def __init__(self):
        self._capacity_cache = None

    async def _get_capacity_data(self):
        if self._capacity_cache is None:
            self._capacity_cache = await load_capacity_file(...)
        return self._capacity_cache
```

**Savings**: ~0.1s × 10 calls = 1 second per 5 registrations

---

### 2. ✅ **High Impact: Batch File Writes** (MEDIUM - 10-15% speedup)
**Current**: Write matches/pos/capacity files after EACH registration
**Optimized**: Batch writes, flush at intervals or end

```python
# Before: 5 registrations × 3 files × 2 phases = 30 file writes
update_json_list(matches_file, data)  # Immediate write
update_json_list(pos_file, data)      # Immediate write

# After: Accumulate in memory, write in batches
self._pending_writes = []
self._pending_writes.append((matches_file, data))
if len(self._pending_writes) >= 5 or is_last_registration:
    await flush_pending_writes()
```

**Savings**: Reduce 30 file writes to 6-10 writes = 2-3 seconds

---

### 3. ✅ **Medium Impact: Parallel Offer Loading** (EASY - 5% speedup)
**Current**: Load offers, incentives, registrations sequentially
**Optimized**: Load all files in parallel

```python
# Before: Sequential (3 file reads)
registrations = await read_json(registrations_file)  # Wait
offers = await read_json(offers_file)                # Wait
incentives = await read_json(incentives_file)        # Wait

# After: Parallel (3 files at once)
registrations, offers, incentives = await asyncio.gather(
    read_json(registrations_file),
    read_json(offers_file),
    read_json(incentives_file)
)
```

**Savings**: ~0.5 seconds (one-time at start)

---

### 4. ⚠️ **Low Impact: Optimize JSON Parsing** (HARD - 2% speedup)
**Current**: Parse entire offers file multiple times
**Optimized**: Keep parsed offers in memory

**Not recommended**: Complexity vs. minimal gain

---

### 5. 🚀 **HIGHEST IMPACT: Reduce AI Round-Trips** (HARD - 20-40% speedup)
**Current**: Critic always reviews, causing extra AI turns
**Optimized**: Skip critic if matcher output is valid JSON

```python
# Before: Always run critic
matcher -> critic -> approve (multiple API calls)

# After: Validate before critic
matcher_output = await run_matcher()
if is_valid_json(matcher_output) and has_required_fields(matcher_output):
    return matcher_output  # Skip critic!
else:
    return await run_critic(matcher_output)  # Only if needed
```

**Savings**: Skip 1-2 AI calls per phase = 5-10 seconds per registration

---

### 6. 🚀 **HIGHEST IMPACT: Streaming with Early Termination** (MEDIUM - 10-20% speedup)
**Current**: Wait for "APPROVE" keyword from critic
**Optimized**: Extract JSON as soon as it's complete in stream

```python
# Before: Wait for full response + "APPROVE"
async for msg in stream:
    accumulate_response()
    if "APPROVE" in response:  # Wait for this
        break

# After: Extract JSON early
async for msg in stream:
    accumulated += msg
    if json_is_complete(accumulated):  # Parse as we go
        return extract_json(accumulated)  # Don't wait for APPROVE
```

**Savings**: 2-5 seconds per phase (skip waiting for "APPROVE" text)

---

### 7. 🎯 **Alternative: Use Faster Constellation** (EASY - 30-50% speedup)
**Current**: `p1m1m2c` (2 phases with critic)
**Optimized**: `p1m1_p2m2` (2 phases, no critic)

```python
# Before: Matcher1 + Critic (~34s)
await run_workflow(constellation="p1m1m2c")

# After: Just Matcher1 (~20s)
await run_workflow(constellation="p1m1_p2m2")
```

**Savings**: ~14 seconds per registration (remove critic overhead)

---

## Timing Measurement Improvements

### Current System Issues:
1. ❌ Only measures total phase time
2. ❌ Doesn't separate AI time vs. I/O time
3. ❌ No breakdown within phases
4. ❌ Hard to identify specific bottlenecks

### Proposed Improvements:

```python
# Add detailed timing breakdown
{
    "registration_id": "SPUS55557",
    "phase1_total_seconds": 34.522,
    "phase1_agent_conversation_seconds": 33.2,    # NEW: AI time
    "phase1_capacity_update_seconds": 0.8,        # NEW: I/O time
    "phase1_file_write_seconds": 0.5,             # NEW: File writes
    "phase2_total_seconds": 15.893,
    "phase2_agent_conversation_seconds": 14.9,    # NEW: AI time
    "phase2_file_write_seconds": 0.9,             # NEW: File writes
    "total_seconds": 50.415
}
```

### Implementation:

```python
class TimingContext:
    """Context manager for detailed timing."""
    def __init__(self, name: str, parent_timer=None):
        self.name = name
        self.start = None
        self.timings = {}
        self.parent = parent_timer

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        elapsed = time.time() - self.start
        self.timings[self.name] = elapsed
        if self.parent:
            self.parent.timings[self.name] = elapsed

# Usage:
with TimingContext("phase1") as phase_timer:
    with TimingContext("agent_conversation", phase_timer):
        result = await process_pair(...)
    with TimingContext("capacity_update", phase_timer):
        await update_capacity(...)
```

---

## Recommended Implementation Order

### Quick Wins (1-2 hours):
1. ✅ Cache capacity data in workflow
2. ✅ Parallel file loading
3. ✅ Enhanced timing measurements

**Expected speedup**: 10-15% (5 seconds per 5 registrations)

### Medium Effort (2-4 hours):
4. ✅ Batch file writes
5. 🚀 Early JSON extraction from stream

**Expected speedup**: 20-30% (15-20 seconds per 5 registrations)

### Advanced (4-8 hours):
6. 🚀 Smart critic skipping
7. 🎯 Constellation-level optimizations

**Expected speedup**: 30-50% (30-40 seconds per 5 registrations)

---

## Non-Code Optimizations

### Infrastructure:
- **Use regional API endpoint** (if available) - reduces latency
- **Increase API rate limits** - fewer throttling delays
- **Use faster model tier** - some models are faster but less accurate

### Configuration:
- **Reduce max_items during development** - test with 2 instead of 5
- **Use mock mode for testing** - instant responses
- **Enable aggressive caching** - cache API responses for same inputs

---

## Measurement Strategy

### Before Optimization:
```bash
# Baseline measurements (3 runs)
time python -m igent.workflows p1m1m2c --max-items 5
# Average: 4m 15s
```

### After Each Optimization:
```bash
# Measure improvement
time python -m igent.workflows p1m1m2c --max-items 5
# Target: 3m 30s (15% improvement)
```

### Detailed Profiling:
```python
import cProfile
cProfile.run('asyncio.run(run_workflow(...))', 'stats.prof')

# Analyze with snakeviz
snakeviz stats.prof
```

---

## Expected Results

| Optimization | Difficulty | Time to Implement | Speedup | Risk |
|-------------|-----------|-------------------|---------|------|
| Cache capacity | Easy | 30 min | 2-3% | Low |
| Parallel file loading | Easy | 20 min | 1-2% | Low |
| Enhanced timing | Easy | 1 hour | 0% (measurement only) | None |
| Batch writes | Medium | 2 hours | 5-10% | Medium |
| Early JSON extraction | Medium | 2 hours | 5-15% | Medium |
| Smart critic skip | Hard | 4 hours | 15-25% | High |
| No-critic constellation | Easy | 0 min | 30-40% | Low |

**Best ROI**: Use `p1m1_p2m2` constellation (instant 30-40% speedup, zero code changes)
**Best code improvement**: Cache + Parallel loading + Batch writes (15-20% speedup, 3 hours work)
