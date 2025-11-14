# Deep Dive: p1m1m2c Agentic Architecture Analysis

## Executive Summary

**The `p1m1m2c` workflow does NOT use a single group chat with 2 matchers and 1 critic.**

Instead, it uses **TWO SEPARATE group chats executed sequentially**:

1. **Phase 1:** Matcher1 + Critic (group chat)
2. **Phase 2:** Matcher2 (solo agent)

## Detailed Architecture Breakdown

### Phase 1: Matcher1-Critic Group Chat

**File:** `igent/workflows/p1m1m2c.py:36-43`

```python
group1 = await get_agents(
    model=self.config.model,
    stream=self.config.stream,
    prompts={
        "matcher1": self.prompts["a_matcher"],
        "critic": self.prompts["critic"],
    },
)
```

**Participants:** 2 agents

- `matcher1` - Uses `a_matcher` prompt
- `critic` - Uses shared `critic` prompt (from `sbus_a_and_b_critic.txt`)

**Task:** Match registrations to suppliers based on:

- Registration requirements (ZIP, panels, product type)
- Supplier capacity and service areas
- Business rules (lowest usedPct)

**Termination Condition:**

```python
# From agents.py:72-78
critic_source = next(
    (name for name in prompts if "critic" in name.lower()), None
)
terminations = TextMentionTermination(
    "APPROVE", sources=[critic_source]
) | MaxMessageTermination(max_messages=10)
```

The conversation continues until:

- The critic says "APPROVE" (validates Matcher1's output), OR
- 10 messages are exchanged (timeout)

**Output:** Match JSON with supplier assignment

---

### Interlude: Capacity Update

**File:** `igent/workflows/p1m1m2c.py:67-71`

Between Phase 1 and Phase 2, the system:

1. Saves Matcher1's output to `matches.json`
2. Updates supplier capacity (decrements available slots)
3. Reloads updated offers for Phase 2

This ensures Matcher2 works with current capacity state.

---

### Phase 2: Matcher2 Solo Agent

**File:** `igent/workflows/p1m1m2c.py:74-78`

```python
group2 = await get_agents(
    model=self.config.model,
    stream=self.config.stream,
    prompts={"matcher2": self.prompts["b_matcher"]},
)
```

**Participants:** 1 agent
- `matcher2` - Uses `b_matcher` prompt

**Task:** Enrich matches with:
- Detailed pricing information
- Applicable subsidies/incentives (via `fetch_incentives_tool`)
- Final purchase order (PO) data

**Termination Condition:**
```python
# From agents.py:88-90
terminations = TextMentionTermination(
    "APPROVE", sources=matcher_sources
) | MaxMessageTermination(max_messages=10)
```

Since there's only one matcher and no critic:

- Matcher2 says "APPROVE" when done, OR
- 10 messages timeout

**Output:** Enriched PO JSON with pricing and subsidies

---

## Why Two Separate Group Chats?

Looking at the code structure, there are several reasons:

### 1. **Sequential Dependencies**

- Phase 2 requires Phase 1's output (the match)
- Capacity must be updated between phases
- Different input data for each phase

### 2. **Different Agent Compositions**

- Phase 1: Matcher + Critic (validation needed)
- Phase 2: Matcher only (enrichment task)

### 3. **Separate Concerns**

- Phase 1: Business logic matching (complex, needs validation)
- Phase 2: Data enrichment (straightforward, no validation)

### 4. **Timing Separation**

```python
# From p1m1m2c.py:58,106
t_matcher1_critic = time.time() - start_time  # Phase 1 timing
t_matcher2 = time.time() - start_time          # Phase 2 timing
```

The workflow tracks execution time separately for:

- Matcher1-Critic operations
- Matcher2 operations

This allows performance analysis of each phase independently.

---

## Prompt Loading Logic

**File:** `igent/workflows/workflow.py:76-81`

```python
variant = (
    "one_critic"
    if self.config.constellation == "p1m1m2c"
    else "no_critic" if self.config.constellation == "p1m1_p2m2" else None
)
self.prompts = await load_prompts(self.config.business_line, variant=variant)
```

For `p1m1m2c` constellation:
- Uses `variant="one_critic"`
- Loads prompts from `igent/prompts/sbus/one_critic/`:
  - `sbus_a_matcher.txt` → `prompts["a_matcher"]`
  - `sbus_b_matcher.txt` → `prompts["b_matcher"]`
  - `sbus_a_and_b_critic.txt` → `prompts["critic"]`

The critic prompt is **shared** between both phases (though only used in Phase 1).

---

## Agent Creation Details

**File:** `igent/agents.py:14-97`

### Key Features:

1. **Dynamic Agent Creation** (lines 28-50)
   - Creates agents based on `prompts` dict keys
   - Each agent gets:
     - System message from prompt file
     - Access to `fetch_incentives_tool`
     - Instruction to say "APPROVE" when done

2. **Tool Reflection** (line 44)
   ```python
   reflect_on_tool_use=True
   ```
   - Enables agents to validate tool usage
   - Passes `tool_choice` parameter to model
   - This is why we needed the **kwargs fix in EndpointsChatCompletionClient

3. **RoundRobinGroupChat** (lines 92-95)
   - Agents take turns speaking
   - Not a free-for-all discussion
   - Ordered conversation flow

4. **Termination Logic** (lines 56-90)
   - Detects critic presence dynamically
   - Adjusts termination conditions based on agent composition
   - Supports multiple configurations (one_critic, two_critics, no_critics)

---

## Workflow Constellations Supported

**File:** `igent/workflows/workflow.py:27`

```python
constellation: Literal["p1m1m2c", "p1m1c1m2c2", "p1m1c1_p2m2c2", "p1m1_p2m2"]
```

Different experiment configurations:

1. **p1m1m2c** (current)
   - Phase 1: Matcher1 + Critic
   - Phase 2: Matcher2 (no critic)
   - Variant: `one_critic`

2. **p1m1c1m2c2**
   - Phase 1: Matcher1 + Critic1
   - Phase 2: Matcher2 + Critic2
   - Variant: default (two critics)

3. **p1m1c1_p2m2c2**
   - Phase 1: Matcher1 + Critic1
   - Phase 2: Matcher2 + Critic2
   - Different prompt set

4. **p1m1_p2m2**
   - Phase 1: Matcher1 only
   - Phase 2: Matcher2 only
   - Variant: `no_critic`

---

## Message Flow Example

### Phase 1: Matcher1-Critic

**User message to group:**
```
Matcher1: Match based on instructions in system prompt.
REGISTRATION: ```[{...registration data...}]```
OFFERS: ```{...supplier offers...}```
Critic: Review Matcher1's output and say 'APPROVE' if acceptable.
```

**Conversation:**

1. Matcher1 analyzes data, outputs JSON match
2. Critic reviews Matcher1's output
3. If issues found, Critic provides feedback
4. Matcher1 revises based on feedback
5. Repeat until Critic says "APPROVE"

### Phase 2: Matcher2

**User message:**
```
Matcher2: Enrich matches with pricing and subsidies:
MATCHES: ```[{...match from Phase 1...}]```
OFFERS: ```{...updated offers...}```
INCENTIVES: Use fetch_incentives_tool to fetch incentives based on zip code.
```

**Conversation:**

1. Matcher2 receives match from Phase 1
2. Calls `fetch_incentives_tool` if needed
3. Enriches with pricing and subsidy data
4. Outputs enriched PO JSON
5. Says "APPROVE"

---

## Critical Observations

### ✓ Strengths

1. **Clear Separation of Concerns**
   - Matching logic isolated from enrichment
   - Easy to debug each phase independently

2. **Flexible Architecture**
   - Easy to add/remove critics
   - Supports multiple constellation patterns

3. **Performance Tracking**
   - Separate timing for each phase
   - Enables bottleneck identification

4. **Tool Usage**
   - Matcher2 can fetch incentives dynamically
   - `reflect_on_tool_use` ensures correct tool usage

### ⚠️ Potential Issues

1. **No Inter-Phase Validation**
   - Matcher2 has no critic to validate enrichment
   - Pricing/subsidy errors might go undetected

2. **Capacity Update Timing**
   - Capacity updated between phases
   - If Phase 2 fails, capacity is already decremented
   - Could lead to "lost" capacity slots

3. **Magic Strings**
   - "APPROVE" hardcoded in multiple places
   - Agent names ("matcher1", "critic", etc.) hardcoded
   - Prompt key names inconsistent

4. **Prompt Loading Complexity**
   - Complex conditional logic in `load_prompts()`
   - Different file names for different variants
   - Hard to discover what prompts exist

---

## Recommendations

### Priority 1: Fix Magic Strings

Extract constants:

```python
# constants.py
TERMINATION_KEYWORD = "APPROVE"
AGENT_NAMES = {
    "MATCHER1": "matcher1",
    "MATCHER2": "matcher2",
    "CRITIC": "critic",
}
PROMPT_KEYS = {
    "A_MATCHER": "a_matcher",
    "B_MATCHER": "b_matcher",
    "CRITIC": "critic",
}
```

### Priority 2: Simplify Prompt Loading

Use configuration-driven approach:

```python
# prompt_config.yaml
constellations:
  p1m1m2c:
    variant: one_critic
    prompts:
      - key: a_matcher
        file: sbus_a_matcher.txt
      - key: b_matcher
        file: sbus_b_matcher.txt
      - key: critic
        file: sbus_a_and_b_critic.txt
```

### Priority 3: Add Phase 2 Validation

Consider adding a critic to Phase 2 for pricing validation.

### Priority 4: Improve Error Handling

Add rollback mechanism for capacity updates if Phase 2 fails.

---

## Conclusion

The `p1m1m2c` workflow uses a **two-phase sequential architecture**:

- **Phase 1:** Matcher1 + Critic (group chat) → produces match
- **Phase 2:** Matcher2 (solo) → enriches match

This is NOT a single group chat with 2 matchers and 1 critic, but rather two separate agent groups executing in sequence with a capacity update in between.

The architecture is flexible and well-separated, but has opportunities for improvement in validation, error handling, and configuration management.
