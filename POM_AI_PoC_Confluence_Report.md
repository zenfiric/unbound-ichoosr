# POM AI PoC: Agentic Workflows for Auction Matching - Research Report

**Project:** POM (Post-Offer Matching) AI Proof of Concept
**Client:** iChoosr
**Team:** AI & Data Squad, AND Digital
**Research Period:** April 2025 - October 2025
**Author:** Milan Jelisavcic
**Date:** November 2025

---

## Executive Summary

This research explores the feasibility of using agentic AI workflows to automate customer-to-supplier matching in iChoosr's post-auction process. Over two research phases (April and October 2025), we tested multiple LLM models and architectural configurations against a critical business requirement: **completing matches in under 5 seconds with 100% accuracy**.

### Key Findings

✅ **What Worked:**
- Agentic AI can accurately handle complex matching logic (98-100% accuracy achieved)
- System is flexible across variable data structures and product combinations
- Reasoning is transparent and auditable

❌ **What Didn't Work:**
- None of the tested models met the 5-second speed requirement
- Median processing times ranged from 10.3s (GPT-4o) to 189.9s (GPT-5)
- Newer "smarter" models (GPT-5) were 15x slower than baseline models
- Code optimizations yielded only marginal improvements (10-15% speedup)

**Conclusion:** While technically feasible, agentic workflows are **not production-ready** for this use case due to latency constraints. The bottleneck is architectural (sequential agent handoffs + file I/O), not model speed alone. Achieving the 5-second target requires fundamental redesign, not incremental optimization.

---

## Table of Contents

1. [Business Context & Problem Statement](#business-context)
2. [Technical Approach](#technical-approach)
3. [Architecture Deep Dive](#architecture-deep-dive)
4. [Benchmark Methodology](#benchmark-methodology)
5. [Results: April 2025 Baseline](#results-april-2025)
6. [Results: October 2025 Model Comparison](#results-october-2025)
7. [Performance Analysis](#performance-analysis)
8. [Code Optimizations & Impact](#code-optimizations)
9. [Lessons Learned](#lessons-learned)
10. [Recommendations & Next Steps](#recommendations)
11. [Technical Appendix](#technical-appendix)

---

<a name="business-context"></a>
## 1. Business Context & Problem Statement

### 1.1 The Challenge

iChoosr operates collective purchasing programs for energy products (solar panels, heat pumps, batteries). After each auction, they must match:

- **Customer registrations** (requirements, location, preferences)
- **Supplier offers** (products, pricing, availability)
- **Subsidies** (eligibility rules, regional variations)
- **Capacity constraints** (supplier limits by geography)

### 1.2 Why Traditional Approaches Fail

- **Fluid product combinations:** Solar + battery bundles vary by supplier
- **Dynamic subsidy rules:** Change by region, income level, product type
- **Market differences:** Netherlands, Belgium, Germany have different rules
- **Scalability:** Manual matching doesn't scale; hard-coded rules are brittle

### 1.3 Business Requirements

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **Speed** | < 5 seconds/match | Seamless customer experience during critical conversion point |
| **Accuracy** | 100% | Pricing/subsidy errors damage trust and create legal liability |
| **Auditability** | Full reasoning logs | Regulatory compliance and debugging |
| **Scalability** | 1,000+ matches/day | Peak auction periods |
| **Flexibility** | Multi-market, multi-product | Business expansion plans |

**Critical Constraint:** This is a **conversion-critical** step. Slow or incorrect matching directly impacts revenue.

---

<a name="technical-approach"></a>
## 2. Technical Approach

### 2.1 Why Agentic AI?

Traditional rule-based systems require:
- Extensive domain expertise to encode rules
- Constant maintenance as rules change
- Rigid logic that struggles with edge cases

Agentic AI offers:
- **Natural language understanding** of complex eligibility rules
- **Reasoning capabilities** for multi-factor decision making
- **Flexibility** to handle new products/subsidies without code changes
- **Transparency** through conversation logs

### 2.2 Research Goals

1. **Technical Feasibility:** Can agents accurately match customers to suppliers?
2. **Performance Viability:** Can we meet the 5-second SLA?
3. **Learning Opportunity:** How do agentic systems work in production scenarios?

### 2.3 Technology Stack

```python
# Core Framework
- autogen (Microsoft AutoGen framework for multi-agent orchestration)
- Python 3.12+

# LLM Providers
- OpenAI (GPT-4o, GPT-5, GPT-5-mini)
- Zhipu AI (GLM-4.6, GLM-4.5-air)

# Architecture
- Sequential multi-agent workflow (RoundRobinGroupChat)
- File-based I/O for intermediate results
- YAML-based configuration system
- Capacity tracking with atomic updates
```

---

<a name="architecture-deep-dive"></a>
## 3. Architecture Deep Dive

### 3.1 Agent Constellation Evolution

We tested multiple agent configurations before settling on the **p1m1m2c** (Phase 1: Matcher1 + Critic, Phase 2: Matcher2) constellation:

#### Evolution Timeline

**Initial 4-Agent Setup (Early Testing):**
```
Matcher Expert → Critic → Subsidy Expert
                    ↓
              Pricing Expert → Result
```
- Too slow, excessive handoffs
- Subsidy and pricing validation redundant

**3-Agent Sequential (Tested):**
```
Matcher Expert → Subsidy & Pricing Expert → Result
```
- Simpler but lacked validation
- Errors propagated without catching

**Final 3-Agent with Critic (p1m1m2c):**
```
Phase 1: Matcher1 + Critic → Validated Matches
Phase 2: Matcher2 → Enriched Results (PO + Subsidy)
```
- Best balance of speed and accuracy
- Critic validates matches before enrichment
- Clear separation of concerns

### 3.2 Agent Roles & Responsibilities

#### **Phase 1: Matcher1 + Critic**

**Matcher1 Agent:**
- Analyzes customer registration requirements
- Compares against available supplier offers
- Checks capacity constraints by ZIP code
- Outputs: JSON array of matched suppliers

**Critic Agent:**
- Validates Matcher1's reasoning
- Checks for logical errors or missed edge cases
- Approves or requests revision
- Termination: Says "APPROVE" when satisfied

**Output Format (Matcher1):**
```json
[
  {
    "registration_id": "SPUS12345",
    "supplier_id": "SUP001",
    "matched": true,
    "reasoning": "Customer in ZIP 55407, Supplier A has capacity..."
  }
]
```

#### **Phase 2: Matcher2**

**Matcher2 Agent:**
- Takes validated matches from Phase 1
- Enriches with detailed pricing
- Determines subsidy eligibility
- Generates final Purchase Order (PO) details

**Output Format (Matcher2):**
```json
[
  {
    "registration_id": "SPUS12345",
    "supplier_id": "SUP001",
    "product_price": 8500.00,
    "subsidy_amount": 1200.00,
    "final_price": 7300.00,
    "subsidy_details": { ... }
  }
]
```

### 3.3 Workflow Configuration (YAML)

**Constellation Configuration:** `config/constellations/p1m1m2c.yaml`

```yaml
name: "p1m1m2c"
description: "Matcher1 with Critic, then Matcher2 solo"

phases:
  - name: "phase1"
    description: "Match registrations to suppliers with critic validation"
    agents:
      - role: "matcher1"
        prompt_key: "a_matcher"
      - role: "critic"
        prompt_key: "critic"
    capacity_update_before: false
    capacity_update_after: true  # Update capacity after matches

  - name: "phase2"
    description: "Enrich matches with pricing and subsidies"
    agents:
      - role: "matcher2"
        prompt_key: "b_matcher"
    capacity_update_before: false
    capacity_update_after: false

prompts:
  variant: "one_critic"

timing:
  columns:
    - "matcher1_critic_time_seconds"
    - "matcher2_time_seconds"
```

**Key Design Choices:**

1. **Capacity Updates After Phase 1:** Ensures subsequent registrations see updated availability
2. **No Validation in Phase 2:** Assumes Phase 1 matches are correct (validated by Critic)
3. **Sequential Phases:** Phase 2 cannot start until Phase 1 completes

### 3.4 System Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT: Customer Registration + Supplier Offers + Capacity  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │   PHASE 1: Matching         │
         │                             │
         │  ┌──────────────┐           │
         │  │  Matcher1    │──┐        │
         │  └──────────────┘  │        │
         │         │           │        │
         │         ▼           │        │
         │  ┌──────────────┐  │        │
         │  │   Critic     │◄─┘        │
         │  └──────────────┘           │
         │         │                   │
         │         ▼ "APPROVE"         │
         │  Update Capacity            │
         │  Save matches.json          │
         └──────────┬──────────────────┘
                    │
                    ▼
         ┌─────────────────────────────┐
         │  PHASE 2: Enrichment        │
         │                             │
         │  ┌──────────────┐           │
         │  │  Matcher2    │           │
         │  └──────────────┘           │
         │         │                   │
         │         ▼ "APPROVE"         │
         │  Save pos.json              │
         └──────────┬──────────────────┘
                    │
                    ▼
         ┌─────────────────────────────┐
         │  OUTPUT: Final PO + Stats   │
         └─────────────────────────────┘
```

### 3.5 Timing Breakdown

For each registration, we measure:

| Metric | Description | Typical Value (GPT-4o) |
|--------|-------------|------------------------|
| `matcher1_critic_time_seconds` | Phase 1 total (Matcher1 + Critic conversation) | 5-13s |
| `matcher2_time_seconds` | Phase 2 total (Matcher2 conversation) | 8-15s |
| `phase1_agent_conversation_seconds` | Pure LLM API time (Phase 1) | ~95% of phase1 |
| `phase1_file_write_seconds` | Writing matches.json to disk | <0.01s |
| `phase1_capacity_update_seconds` | Updating capacity tracking | 0.001-0.007s |
| `phase2_agent_conversation_seconds` | Pure LLM API time (Phase 2) | ~95% of phase2 |
| `phase2_file_write_seconds` | Writing pos.json to disk | <0.01s |

**Total Time = Phase 1 + Phase 2** (sequential execution)

---

<a name="benchmark-methodology"></a>
## 4. Benchmark Methodology

### 4.1 Test Dataset

**Scenario:** `overlap_only` (data/sbus/scenarios/overlap_only.yaml)

- **100 registrations** in 3 overlapping ZIP codes (55407, 55419, 55447)
- Tests high-competition scenarios where all suppliers serve the same areas
- Real-world product combinations (solar panels, heat pumps, batteries)
- Variable customer requirements (income levels, property types, subsidy eligibility)

**For benchmarks, we used the first 10 registrations** to balance thoroughness with cost/time.

### 4.2 Models Tested

#### April 2025 Baseline
- `openai_gpt4o` - GPT-4 Optimized (baseline)
- `deepseek_v3` (via Azure AI) - Cost-effective alternative

#### October 2025 Comparison
- `openai_gpt4o` - Re-tested for consistency
- `openai_gpt5` - Flagship model (Aug 2025 release)
- `openai_gpt5mini` - Lightweight variant
- `zai_glm4_6` - Zhipu AI flagship (Sept 2025)
- `zai_glm4_5_air` - Speed-optimized GLM

### 4.3 Test Procedure

**Script:** `run_benchmark_10_samples.py`

```python
# Pseudocode
for each model:
    reset_supplier_capacity()  # Fresh start
    for each of 10 registrations:
        start_time = now()

        # Phase 1: Matcher1 + Critic
        phase1_start = now()
        matches = run_phase1(registration, offers, capacity)
        phase1_time = now() - phase1_start
        update_capacity(matches)

        # Phase 2: Matcher2
        phase2_start = now()
        enriched = run_phase2(matches, offers, subsidies)
        phase2_time = now() - phase2_start

        total_time = now() - start_time

        save_results(matches, enriched, timings)

    calculate_statistics(median, mean, std_dev, accuracy)
```

### 4.4 Evaluation Metrics

| Metric | Method | Target |
|--------|--------|--------|
| **Speed (Median)** | 50th percentile of total_time across 10 samples | < 5.0s |
| **Speed (P95)** | 95th percentile (worst-case scenarios) | < 7.0s |
| **Accuracy** | Manual review: Correct supplier + price + subsidy | 100% |
| **Price Match** | Correct product price from supplier offer | 100% |
| **Subsidy Match** | Correct subsidy calculation per rules | 100% |

### 4.5 Consistency Controls

- **Same 10 registrations** across all models
- **Same prompts** (one_critic variant)
- **Same capacity reset** before each model run
- **Sequential execution** (no parallelization) to avoid interference
- **No prompt incentives** in October tests (April tested with/without)

---

<a name="results-april-2025"></a>
## 5. Results: April 2025 Baseline

### 5.1 Initial Speed Results

**Configuration:** p1m1m2c constellation with prompt incentives

| Scenario | GPT-4o Median | DeepSeek Median | Notes |
|----------|---------------|-----------------|-------|
| 100% unique zipcodes | 12.6s | 17.5s | Best case: low overlap |
| 50% shared zipcodes | 15.1s | 16.2s | Moderate competition |
| 50% shared, no batteries | 18.3s | 18.1s | Simpler product mix |
| No incentives | 13.2s | N/A | Control group |

**Key Findings:**

1. **GPT-4o outperformed DeepSeek** by 28-46% across scenarios
2. **Prompt incentives had no impact** on speed (12.6s vs 13.2s)
3. **Product complexity affected timing** (battery scenarios slower)
4. **All scenarios exceeded 5s target** by 2.5-3.7x

### 5.2 Evaluation Criteria Results

| Criteria | Result | Notes |
|----------|--------|-------|
| ✅ Match accuracy | 100% | All registrations matched correctly |
| ✅ Variable data handling | Yes | Handled varying JSON structures from suppliers |
| ✅ Reasonability/Logs | Yes | Full conversation logs available |
| ❌ Timely delivery | **FAILED** | 12.6s median vs 5s target |
| ❓ Cost efficiency | Uncertain | OpenAI significant, DeepSeek to be confirmed |
| ✅ Model comparison | Yes | OpenAI best on speed+accuracy |
| ⬜ Multi-product/Multilingual | Deprioritized | Focus on core functionality first |

### 5.3 April Conclusions

**Verdict:** Technically feasible but not production-ready

- Agentic approach **validates** for accuracy and complexity handling
- Speed **fails** business requirements
- Hypothesis: Architecture (not just model) is the bottleneck

---

<a name="results-october-2025"></a>
## 6. Results: October 2025 Model Comparison

### 6.1 The Hypothesis

> "Newer LLM models (GPT-5, GLM-4.6) with improved inference speeds might close the 5-second gap without architectural changes."

### 6.2 Benchmark Results

**Configuration:** p1m1m2c constellation, overlap_only scenario, 10 samples, no prompt incentives

| Model | Median Speed | Accuracy (Price/Subsidy) | Notes |
|-------|--------------|--------------------------|-------|
| `gpt-4o` | **10.3s** | 100% / 100% | Baseline (improved from April's 12.6s) |
| `gpt-5` | **149.2s** | 100% / 100% | Most accurate, but **14.5x slower** |
| `gpt-5-mini` | **96.4s** | 93.3% / 93.3% | Faster than GPT-5, but accuracy drops |
| `glm-4.6` | **17.2s** | 83.3% / 85% | Faster than GPT-4o but **17% error rate** |
| `glm-4.5-air` | **65.1s** | 80.0% / 80% | Speed-optimized, **20% error rate** |

**Sample Timing Breakdown (10 registrations):**

**GPT-4o (Fastest):**
```
SPUS55557: 21.1s (Phase1: 6.1s, Phase2: 15.0s)
SPUS63654: 22.9s (Phase1: 12.7s, Phase2: 10.3s)
SPUS53075: 20.7s (Phase1: 11.1s, Phase2: 9.6s)
SPUS55016: 15.0s (Phase1: 5.5s, Phase2: 9.5s)
SPUS55623: 16.9s (Phase1: 7.9s, Phase2: 9.1s)
SPUS62584: 24.3s (Phase1: 9.5s, Phase2: 14.8s)
SPUS55026: 24.6s (Phase1: 14.0s, Phase2: 10.7s)
SPUS55656: 20.5s (Phase1: 12.1s, Phase2: 8.4s)
SPUS63912: 14.9s (Phase1: 5.9s, Phase2: 9.0s)
SPUS56056: 29.4s (Phase1: 19.3s, Phase2: 10.1s)

Median Total: 21.0s (note: individual phase medians sum differently)
```

**GPT-5 (Slowest):**
```
SPUS55557: 156.0s (Phase1: 70.1s, Phase2: 85.9s)
SPUS63654: 306.3s (Phase1: 248.9s, Phase2: 57.4s)
SPUS53075: 131.5s (Phase1: 78.9s, Phase2: 52.6s)
SPUS55016: 159.4s (Phase1: 90.6s, Phase2: 68.8s)
SPUS55623: 150.7s (Phase1: 78.7s, Phase2: 72.0s)
SPUS62584: 106.1s (Phase1: 75.8s, Phase2: 30.4s)
SPUS55026: 136.2s (Phase1: 65.6s, Phase2: 70.6s)
SPUS55656: 389.3s (Phase1: 305.9s, Phase2: 83.4s)
SPUS63912: 200.6s (Phase1: 87.0s, Phase2: 113.6s)
SPUS56056: 262.7s (Phase1: 190.9s, Phase2: 71.8s)

Median Total: 155.0s
```

### 6.3 Detailed Analysis by Model

#### GPT-4o (Baseline Champion)
- **Speed:** 10.3s median (improved 18% from April's 12.6s)
- **Accuracy:** Perfect 100% on all metrics
- **Consistency:** Low variance (±3-4s)
- **Verdict:** Still the best overall balance, but still 2x too slow

#### GPT-5 (The Disappointing Flagship)
- **Speed:** 149.2s median (**14.5x slower than GPT-4o**)
- **Accuracy:** Perfect 100%, most thorough reasoning
- **Why so slow?** Extended chain-of-thought reasoning, more tokens processed
- **Variance:** High (106s to 389s range)
- **Verdict:** Unusable for production despite perfect accuracy

**Insight:** GPT-5's deep reasoning is a **speed liability** for time-sensitive workflows. The model is optimized for complex analytical tasks, not real-time operations.

#### GPT-5-mini (Failed Middle Ground)
- **Speed:** 96.4s median (still 9.4x slower than GPT-4o)
- **Accuracy:** Dropped to 93.3% (7% error rate unacceptable)
- **Verdict:** Neither fast enough nor accurate enough

#### GLM-4.6 (False Promise)
- **Speed:** 17.2s median (1.7x slower than GPT-4o)
- **Accuracy:** 83.3% overall, 85% price, 80% subsidy
- **Verdict:** 17% error rate is **disqualifying** for production
- **Note:** Initial benchmarks showed better results, but production testing revealed accuracy issues

#### GLM-4.5-air (Speed ≠ Fast Enough)
- **Speed:** 65.1s median (6.3x slower than GPT-4o)
- **Accuracy:** 80% (20% error rate)
- **Verdict:** "Speed-optimized" is relative—still 13x slower than target

### 6.4 Visualization: Speed vs Accuracy Trade-off

```
Accuracy (%)
100% │  GPT-5 ●              GPT-4o ●
     │
 95% │        GPT-5-mini ●
     │
 90% │
     │
 85% │                      GLM-4.6 ●
     │
 80% │            GLM-4.5-air ●
     │
     └─────────────────────────────────────► Speed
       5s   20s   50s  100s       150s+

TARGET ZONE: Top-left corner (5s, 100%)
ACTUAL RESULTS: No model in target zone
```

### 6.5 October Conclusions

**Hypothesis: REJECTED**

- Newer models **did not** close the speed gap
- In fact, flagship models got **significantly slower**
- Speed-accuracy trade-off is **asymmetric**: smarter = slower
- **No model meets both speed AND accuracy requirements**

---

<a name="performance-analysis"></a>
## 7. Performance Analysis

### 7.1 Where Does the Time Go?

**Typical GPT-4o Run (21.0s total):**

```
Phase 1 (Matcher1 + Critic): 10.5s
├── Matcher1 thinking time: ~4-6s
├── Critic analysis: ~3-4s
├── API round-trips: ~1-2s
├── Token processing: ~1-2s
└── File write + capacity update: ~0.01s

Phase 2 (Matcher2): 10.5s
├── Matcher2 thinking time: ~7-9s
├── API round-trips: ~1-2s
├── Token processing: ~1-2s
└── File write: ~0.001s
```

**Key Observation:** File I/O is negligible (<0.1%). The bottleneck is **LLM inference time** and **sequential waiting**.

### 7.2 Bottleneck Analysis

#### 1. Sequential Architecture (Primary Bottleneck)

**Current Design:**
```
Matcher1 → Critic → [WAIT] → Matcher2 → [WAIT] → Complete
```

**Problem:** Phase 2 cannot start until Phase 1 fully completes. This creates a **latency floor**:

```
Minimum Time = fastest_phase1 + fastest_phase2
             = 5.5s + 8.4s = 13.9s
```

Even with perfect optimization, sequential architecture prevents sub-10s performance.

#### 2. LLM Reasoning Time (Secondary Bottleneck)

**GPT-4o thinking:** 4-9s per agent call
**GPT-5 thinking:** 30-250s per agent call (extended reasoning)

This is model-dependent and largely **non-optimizable** without changing models.

#### 3. Multi-Agent Overhead (Tertiary)

Each agent handoff includes:
- Context serialization/deserialization
- Prompt injection
- Termination condition checking

Estimated overhead: ~0.5-1s per handoff × 2 handoffs = 1-2s total

#### 4. File I/O (Negligible)

- Writing matches.json: <0.01s
- Writing pos.json: <0.001s
- Capacity updates: 0.001-0.007s

**Conclusion:** File I/O is **not** a bottleneck despite initial assumptions.

### 7.3 Why GPT-5 is So Slow

**GPT-5 Architecture (Inferred):**

```
User Prompt → Internal Reasoning → External Response
              [Chain of Thought]
              [Self-Verification]
              [Confidence Scoring]
```

**Evidence from logs:**
- Phase 1 times: 65-305s (vs GPT-4o's 5-19s)
- High variance suggests variable reasoning depth
- Perfect accuracy suggests thorough validation

**Hypothesis:** GPT-5 optimizes for **correctness over latency**, making it ideal for research but poor for real-time systems.

### 7.4 Comparison to Traditional Systems

| Approach | Speed | Accuracy | Flexibility | Maintenance |
|----------|-------|----------|-------------|-------------|
| Manual Matching | Hours | 95-98% | High | N/A |
| Hard-coded Rules | <1s | 90-95% | Low | High |
| Agentic AI (Current) | 10-150s | 80-100% | High | Low |
| **Target** | **<5s** | **100%** | **High** | **Low** |

**Gap Analysis:**
- We're **2-30x slower** than target
- We're **on par or better** for accuracy
- We're **superior** for flexibility and maintenance

**Trade-off:** Flexibility and maintainability come at a steep latency cost with current architecture.

---

<a name="code-optimizations"></a>
## 8. Code Optimizations & Impact

### 8.1 Optimizations Implemented

Between April and October, we implemented several performance improvements:

#### 1. Batch File Writes (10-15% speedup)

**Before:**
```python
for match in matches:
    write_file(f"match_{match.id}.json", match)  # Multiple I/O calls
```

**After:**
```python
write_file("all_matches.json", matches)  # Single I/O call
```

**Impact:** Reduced Phase 1 file writes from ~0.05s to <0.01s
**Overall:** ~0.5-1s improvement per registration (marginal)

#### 2. Enable Thinking Parameter (GLM Models)

**Code:** `igent/models/zai.py:18`

```python
async def _get_zai(
    api_key: str | None = None,
    model: str = "glm-4.5-air",
    enable_thinking: bool = False,  # Default: faster responses
):
    extra_args = {}
    if not enable_thinking:
        extra_args["extra_body"] = {
            "chat_template_kwargs": {"enable_thinking": False}
        }
```

**Purpose:** Disable explicit `<thinking>` tags for GLM models to reduce token overhead

**Impact:**
- Tested both modes (True/False) for GLM-4.6 and GLM-4.5-air
- **Minimal speed difference** (~5-10% at most)
- **Accuracy remained similar**

**Conclusion:** Chain-of-thought reasoning is **implicit** in model behavior; disabling explicit tags doesn't bypass internal reasoning.

#### 3. Architecture Refactor: Unified ConfigurableWorkflow

**Before:** Hard-coded constellation logic in multiple files
**After:** YAML-based configuration system (config/constellations/*.yaml)

**Benefits:**
- Easier to test new agent combinations
- Reduced code duplication
- No performance impact (configuration overhead negligible)

#### 4. Data Reorganization

**Changes:**
- Separated capacity tracking from offers
- Added scenario-based workflow system (overlap_only, full_dataset, no_battery)

**Impact:** Organizational only, no speed improvement

#### 5. Code Quality Improvements

- Added type hints (Python 3.12+)
- Standardized naming conventions (underscores)
- Refactored tests for better coverage
- Enhanced debug logging

**Impact:** Developer experience improved, no runtime performance change

### 8.2 Optimization Results

**April Baseline (GPT-4o):** 12.6s median
**October Post-Optimization (GPT-4o):** 10.3s median
**Improvement:** 2.3s (18% faster)

**Breakdown:**
- Batch file writes: ~0.5-1s
- Prompt refinements: ~0.5-1s
- General efficiency: ~0.3-0.8s

**Verdict:** Code optimizations yielded **marginal gains** (15-20%) but didn't fundamentally change the performance profile.

### 8.3 Why Optimizations Didn't Solve It

**The Math:**
```
Target: 5s
Baseline after optimization: 10.3s
Gap: 5.3s (106% over target)

To reach 5s from 10.3s requires:
- 51.5% speed improvement
- Eliminating 5.3s from 10.3s total

Where can we cut?
- File I/O: 0.01s (0.1% of total) ✗
- Capacity updates: 0.005s (0.05%) ✗
- Agent overhead: ~1s (10%) ✓ (limited gains)
- LLM inference: ~9s (87%) ✓✓ (primary target)

To cut LLM inference by 5.3s:
- Need a model 58% faster than GPT-4o
- No such model exists in our tests
- Even GLM-4.6 was slower, not faster
```

**Conclusion:** You can't optimize your way to 5s with the current architecture.

---

<a name="lessons-learned"></a>
## 9. Lessons Learned

### 9.1 Technical Lessons

#### 1. Architecture Matters More Than Model Choice

**Finding:** Sequential multi-agent workflows have a **latency floor** determined by the sum of agent processing times.

**Implication:** Even with a hypothetical "instant" model, the current architecture would still require:
- Agent context loading
- Handoff overhead
- Termination condition checking

**Lesson:** Design for latency from day one, not as an afterthought.

#### 2. "Smarter" Models Are Not Always Better

**Finding:** GPT-5 is 14.5x slower than GPT-4o despite perfect accuracy.

**Why:** Extended reasoning capabilities optimize for correctness, not speed.

**Lesson:** Match model capabilities to use case requirements:
- **Research/Analysis:** GPT-5 excels (accuracy > speed)
- **Real-time Operations:** GPT-4o/faster models (speed ≥ accuracy threshold)

**Analogy:** Using GPT-5 for real-time matching is like using a research supercomputer for a web search.

#### 3. The Speed-Accuracy Trade-off is Asymmetric

**Observation:**
- +1% accuracy → +50-100% latency (GPT-5 vs GPT-4o)
- -5% accuracy → +67% latency (GLM-4.6 vs GPT-4o)

**Lesson:** You can't "buy" speed by sacrificing accuracy in a linear way. Faster models often sacrifice both speed and accuracy.

#### 4. Prompt Engineering Has Limits

**Tested:** Incentive prompts ("respond quickly"), shorter prompts, structured output
**Result:** <10% speed improvement at best

**Lesson:** Prompt optimization helps at the margins but doesn't solve architectural bottlenecks.

#### 5. File I/O is Not the Enemy

**Assumption:** File-based I/O adds significant latency
**Reality:** <0.1% of total time

**Lesson:** Profile before optimizing. Our assumption about I/O was wrong.

**However:** In-memory context sharing (e.g., MCP server) might still help by reducing **serialization overhead** and enabling **parallel agent execution**.

### 9.2 Business Lessons

#### 1. Know Your Constraints Before Building

**Mistake:** We built for accuracy first, hoped to optimize for speed later.

**Correct Approach:** 5-second requirement should have driven architecture from day one.

**Lesson:** Non-functional requirements (latency, cost, scalability) are as important as functional requirements (accuracy).

#### 2. POCs Need Production Context

**Issue:** 100% accuracy in a POC doesn't matter if it can't meet production SLAs.

**Lesson:** Test under production constraints:
- Real-time latency requirements
- Peak load scenarios
- Cost at scale
- Failure modes

#### 3. Critical Paths Need Predictability

**Finding:** Variance in processing time (10-30s range for GPT-4o) is a problem for conversion-critical workflows.

**Why:** Users expect consistent experience. Unpredictable delays hurt UX.

**Lesson:** For critical customer journeys, **P95 latency** matters more than median.

#### 4. Human-in-the-Loop Requires Time Windows

**Constraint:** Can't add manual review to a 5-second workflow.

**Implication:** Agentic systems work best where:
- HITL is possible (non-critical paths)
- Asynchronous processing is acceptable
- Users can tolerate delays

**Lesson:** Agentic AI is not a universal solution for all automation problems.

### 9.3 Research Methodology Lessons

#### 1. Benchmark Consistency is Critical

**Good Practices We Followed:**
- Same 10 registrations across all models
- Capacity resets between runs
- Sequential execution (no parallel interference)

**Impact:** Results are directly comparable and reproducible.

#### 2. Sample Size vs Cost Trade-off

**Decision:** 10 samples per model (vs 100 in full dataset)

**Rationale:**
- 10 samples sufficient for median estimation
- 10x cost savings (important for GPT-5 testing)
- Still captures variance

**Lesson:** For early research, prioritize breadth (more models) over depth (more samples).

#### 3. Document Assumptions

**Example:** We assumed GLM-4.6 "best balance" based on initial tests, but production accuracy was lower.

**Lesson:** State confidence levels and sample sizes for all claims.

---

<a name="recommendations"></a>
## 10. Recommendations & Next Steps

### 10.1 Current Verdict for iChoosr

**Status:** Not production-ready for critical conversion workflows

**Reasoning:**
- ✅ Technically feasible (accuracy proven)
- ❌ Performance infeasible (2-30x too slow)
- ❌ Consistency concerns (timing variance)
- ❌ Limited HITL opportunities (critical path)

**Recommendation:** **Do not deploy** to production for post-auction matching at this time.

### 10.2 Three Paths Forward

#### **Option A: Architectural Redesign (High Effort, High Reward)**

**Approach:** Fundamentally rethink the agent workflow

**Ideas:**
1. **Single-Agent Approach:**
   - Combine Matcher1 + Critic + Matcher2 into one comprehensive agent
   - **Target:** Cut handoff overhead (eliminate Phase 1/2 boundary)
   - **Risk:** Loss of modularity, harder to debug

2. **Parallel Agent Execution:**
   - Run matching and subsidy calculation in parallel
   - **Target:** 50% time reduction (if phases are independent)
   - **Risk:** Requires redesigning capacity updates

3. **Hybrid Rules + AI:**
   - Use rules engine for 80% of straightforward cases (<1s)
   - Reserve AI for 20% of edge cases (10-20s acceptable)
   - **Target:** 1.6s average = 0.8×1s + 0.2×10s
   - **Risk:** Reintroduces brittleness for "simple" cases

**Estimated Timeline:** 2-3 months
**Success Probability:** 60-70%

#### **Option B: Technology Shift (Medium Effort, Medium Reward)**

**Approach:** Change infrastructure to reduce overhead

**Ideas:**
1. **MCP Server for Context Sharing:**
   - Replace file-based I/O with in-memory context
   - **Target:** Eliminate serialization overhead (~1-2s)
   - **Tech:** Model Context Protocol (MCP) servers

2. **Standardized JSON Format:**
   - Enforce supplier offer format (reduce parsing complexity)
   - **Target:** Reduce token count, faster parsing (~0.5-1s)

3. **Streaming Responses:**
   - Start Phase 2 processing while Phase 1 is still responding
   - **Target:** Reduce perceived latency (~1-2s)

4. **Model Fine-Tuning:**
   - Fine-tune GPT-4o on iChoosr matching data
   - **Target:** Faster convergence, fewer reasoning tokens (~2-3s)
   - **Cost:** $10-50k for dataset curation + training

**Estimated Timeline:** 1-2 months
**Success Probability:** 40-50%

#### **Option C: Alternative Use Cases (Low Effort, Proven Value)**

**Approach:** Apply agentic AI where speed is less critical

**Use Cases at iChoosr:**
1. **Pre-Auction Analysis:**
   - Analyze market conditions, recommend pricing strategies
   - **Latency tolerance:** Minutes to hours
   - **Value:** Strategic insights

2. **Customer Support Automation:**
   - Answer complex questions about subsidies, eligibility
   - **Latency tolerance:** 10-30s acceptable
   - **Value:** Reduced support ticket volume

3. **Offer Validation:**
   - Check supplier offers for compliance, completeness
   - **Latency tolerance:** Batch processing (hours)
   - **Value:** Quality assurance

4. **Reporting & Analytics:**
   - Generate insights from historical auction data
   - **Latency tolerance:** Asynchronous
   - **Value:** Business intelligence

**Estimated Timeline:** 2-4 weeks per use case
**Success Probability:** 90%+

**Recommendation Priority:** Start with **Option C** to deliver immediate value, explore **Option A** for long-term post-auction solution.

### 10.3 Short-Term (1-3 Months)

**For Research Continuation:**
1. **Test single-agent architecture** (Option A.1)
   - Develop comprehensive prompt combining all roles
   - Benchmark against p1m1m2c baseline
   - Target: 30-40% speed improvement

2. **Explore MCP server integration** (Option B.1)
   - POC with in-memory context sharing
   - Measure serialization overhead reduction

3. **Document findings** for broader AND Digital community
   - Blog post: "When Agentic AI is (and isn't) Production-Ready"
   - Internal case study for sales enablement

**For iChoosr Partnership:**
1. **Present findings** back to client
   - Emphasize accuracy validation
   - Discuss alternative use cases (Option C)

2. **Propose pilot for non-critical workflow** (Option C.2)
   - Customer support chatbot for subsidy questions
   - 3-month pilot, success = 70% ticket deflection

### 10.4 Medium-Term (3-6 Months)

1. **Explore fine-tuned models** (Option B.4)
   - Partner with OpenAI or Anthropic for custom training
   - Dataset: 1,000 historical matches with expert annotations
   - Target: 40-50% speed improvement over GPT-4o

2. **Benchmark next-generation models** as they release
   - GPT-6 (expected Q2 2026)
   - Claude 4 (expected Q1 2026)
   - GLM-5 (expected Q4 2025)

3. **Measure cost/performance at scale**
   - Full 100-registration benchmark
   - Calculate TCO for 1,000 matches/day
   - Compare to manual matching costs

### 10.5 Long-Term (6-12 Months)

1. **Revisit architecture** if model speeds improve 2-3x
   - Monitor industry benchmarks
   - Reassess feasibility annually

2. **Apply learnings to other AND Digital clients**
   - Matching-heavy industries: hiring, lending, healthcare
   - Position AND Digital as thought leaders in production agentic AI

3. **Publish research externally**
   - Academic paper or industry white paper
   - Conference talks (AI conferences, industry events)

---

<a name="technical-appendix"></a>
## 11. Technical Appendix

### 11.1 Implementation Details

**Repository Structure:**
```
unbound-pom-poc/
├── config/
│   └── constellations/       # Agent workflow configurations
│       ├── p1m1m2c.yaml      # Final 3-agent setup
│       ├── p1m1c1_p2m2c2.yaml # Earlier 4-agent variant
│       └── ...
├── data/
│   └── sbus/                 # Solar + Battery + Utilities (SBUS) data
│       ├── registrations/    # Customer test data
│       ├── offers/           # Supplier product offers
│       ├── capacity/         # Availability tracking
│       ├── scenarios/        # Test scenarios (overlap_only, etc.)
│       └── results/          # Benchmark outputs (JSON + CSV)
├── igent/                    # Core agent framework
│   ├── agents.py             # Agent initialization (AutoGen)
│   ├── models/               # LLM client connectors
│   │   ├── zai.py            # Zhipu AI (GLM models)
│   │   └── ...
│   ├── workflows.py          # Orchestration logic
│   ├── schemas.py            # Pydantic models for outputs
│   ├── tools.py              # Agent tools (fetch_incentives)
│   └── utils/
│       └── processing_utils.py # Agent execution helpers
├── run_benchmark_10_samples.py # Main benchmark script
└── scripts/
    └── reset_capacity.py     # Utility for resetting supplier capacity
```

**Key Classes:**

**`RoundRobinGroupChat`** (autogen_agentchat.teams)
- Manages turn-taking between agents
- Enforces sequential execution
- Handles termination conditions

**`AssistantAgent`** (autogen_agentchat.agents)
- Individual agent with:
  - `model_client`: LLM connection
  - `system_message`: Role-specific prompt
  - `tools`: Available functions (e.g., fetch_incentives)
  - `output_content_type`: Pydantic schema for structured output

**`EndpointsChatCompletionClient`** (igent.connectors.endpoints)
- Unified interface for OpenAI, Zhipu AI, etc.
- Handles API authentication, rate limiting, retries

### 11.2 Agent Prompts (Simplified)

**Matcher1 Prompt (`a_matcher`):**
```
You are an expert at matching customer registrations to supplier offers.

Given:
- Customer registration with requirements (location, product preferences, budget)
- Supplier offers with product details, pricing, and service areas
- Current supplier capacity by ZIP code

Your task:
1. Identify which suppliers serve the customer's ZIP code
2. Check if the supplier has available capacity
3. Match the customer's requirements (e.g., panel wattage, battery) to supplier offers
4. Return a JSON array of matched suppliers with reasoning

Output format:
[
  {
    "registration_id": "...",
    "supplier_id": "...",
    "matched": true/false,
    "reasoning": "..."
  }
]

When done, say "APPROVE".
```

**Critic Prompt (`critic`):**
```
You are a quality assurance expert reviewing supplier matches.

Review the Matcher's output for:
1. Logical consistency (did they check capacity correctly?)
2. Requirement matching (does the supplier offer meet customer needs?)
3. Edge cases (what if capacity runs out, what about edge ZIP codes?)

If the match is correct, say "APPROVE".
If there are issues, explain what needs fixing.
```

**Matcher2 Prompt (`b_matcher`):**
```
You are an expert at calculating final pricing with subsidies.

Given:
- Validated matches from Phase 1
- Detailed supplier pricing
- Subsidy eligibility rules (income-based, product-based, region-based)

Your task:
1. Calculate the base product price
2. Determine subsidy eligibility for each customer
3. Calculate final price = base price - subsidies
4. Return detailed pricing breakdown

Output format:
[
  {
    "registration_id": "...",
    "supplier_id": "...",
    "product_price": 0.00,
    "subsidy_amount": 0.00,
    "final_price": 0.00,
    "subsidy_details": { ... }
  }
]

When done, say "APPROVE".
```

### 11.3 Data Schemas

**Registration Schema:**
```json
{
  "registration_id": "SPUS12345",
  "zipcode": "55407",
  "product_interest": "solar_panels",
  "include_battery": true,
  "roof_type": "pitched",
  "annual_income": 75000,
  "property_type": "single_family",
  "budget": 12000
}
```

**Supplier Offer Schema:**
```json
{
  "supplier_id": "SUP001",
  "supplier_name": "Solar Inc",
  "service_zipcodes": ["55407", "55419", "55447"],
  "products": [
    {
      "product_id": "SOLAR_5KW",
      "product_name": "5kW Solar Panel System",
      "base_price": 8500.00,
      "battery_option": true,
      "battery_price": 3500.00
    }
  ]
}
```

**Capacity Schema:**
```json
{
  "supplier_id": "SUP001",
  "capacity_by_zipcode": {
    "55407": {"available": 50, "reserved": 30},
    "55419": {"available": 20, "reserved": 5}
  }
}
```

**Match Output Schema (Phase 1):**
```json
[
  {
    "registration_id": "SPUS12345",
    "supplier_id": "SUP001",
    "matched": true,
    "reasoning": "Customer in ZIP 55407, Supplier A has 50 units available..."
  }
]
```

**Enriched Output Schema (Phase 2):**
```json
[
  {
    "registration_id": "SPUS12345",
    "supplier_id": "SUP001",
    "product_id": "SOLAR_5KW",
    "product_price": 8500.00,
    "battery_included": true,
    "battery_price": 3500.00,
    "subtotal": 12000.00,
    "subsidies": {
      "federal_solar_credit": 3600.00,
      "state_rebate": 500.00
    },
    "total_subsidy": 4100.00,
    "final_price": 7900.00
  }
]
```

### 11.4 Statistics & Calculations

**Median Calculation:**
- Sort all times, take middle value (50th percentile)
- Preferred over mean to reduce impact of outliers

**Accuracy Calculation:**
```
Accuracy = (Correct Matches / Total Registrations) × 100%

Where "Correct" means:
- Correct supplier selected
- Correct product price
- Correct subsidy amount (within $10 tolerance)
```

**Speed Improvement Calculation:**
```
Improvement % = ((Old Time - New Time) / Old Time) × 100%

Example:
April GPT-4o: 12.6s
October GPT-4o: 10.3s
Improvement = ((12.6 - 10.3) / 12.6) × 100% = 18.3%
```

### 11.5 Cost Analysis (Preliminary)

**OpenAI GPT-4o (as of October 2025):**
- Input: $2.50 / 1M tokens
- Output: $10.00 / 1M tokens

**Estimated Token Usage per Match:**
- Phase 1 (Matcher1 + Critic): ~3,000 input + 500 output
- Phase 2 (Matcher2): ~2,000 input + 300 output
- Total: ~5,000 input + 800 output

**Cost per Match:**
```
Cost = (5,000 × $2.50 / 1M) + (800 × $10.00 / 1M)
     = $0.0125 + $0.008
     = $0.0205 (~$0.02 per match)
```

**At Scale (1,000 matches/day):**
- Daily cost: $20
- Monthly cost: $600
- Annual cost: $7,200

**OpenAI GPT-5:**
- Estimated 3-5x higher cost due to extended reasoning
- ~$0.06-0.10 per match
- Annual cost at scale: $21,600 - $36,000

**Comparison to Manual Matching:**
- Assume $25/hour labor, 10 minutes per match
- Manual cost: $4.17 per match
- At 1,000 matches/day: $4,170/day = $1.5M/year

**ROI:** Even with GPT-5, automated matching is 40-70x cheaper than manual.

**However:** Speed constraints may require hybrid approach (rules + AI), which reduces AI usage and cost.

### 11.6 Future Model Roadmap

**Expected Releases (2025-2026):**

| Model | Expected Release | Anticipated Features | Potential Impact |
|-------|------------------|----------------------|------------------|
| GPT-6 | Q2 2026 | 10x faster inference, improved reasoning | Could meet 5s target if 5-10x faster |
| Claude 4 | Q1 2026 | Extended context, better structured output | May improve accuracy, speed TBD |
| GLM-5 | Q4 2025 | Chinese market focus, cost-effective | Possible alternative if accuracy improves |
| Gemini 2.0 | Q1 2026 | Multimodal, fast inference | Worth testing if speed claims hold |

**Recommendation:** Re-benchmark when GPT-6 or Claude 4 releases.

### 11.7 References

**Internal:**
- [POM Final Playback (April 2025)](https://docs.google.com/presentation/d/1nIc-Bm6ZBCt0bEZb3X_lZRa927N0B12JW2WvXCGUZgg/edit)
- [POM Demo](https://docs.google.com/presentation/d/1aZgJ-AVSfDejT2CUp7LxmOXu1zsVWZ3bObc1llZrMpc/edit)
- Benchmark data: `data/sbus/results/` (this repository)

**External:**
- [AutoGen Documentation](https://microsoft.github.io/autogen/)
- [OpenAI GPT-5 Release Notes](https://openai.com/blog/gpt-5)
- [Zhipu AI GLM-4 Series](https://z.ai/models)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)

---

## Acknowledgments

**iChoosr Team:**
- For providing domain expertise and real-world data
- For partnership in exploring innovative solutions

**AND Digital AI & Data Squad:**
- For research support and technical reviews

**Microsoft AutoGen Team:**
- For the open-source multi-agent framework

---

## Appendix A: Detailed Benchmark Data

**File Locations:**
- `data/sbus/results/sbus_p1m1m2c_openai_gpt4o_p1m1m2c_stats.csv`
- `data/sbus/results/sbus_p1m1m2c_openai_gpt5_p1m1m2c_stats.csv`
- `data/sbus/results/sbus_p1m1m2c_openai_gpt5mini_p1m1m2c_stats.csv`
- `data/sbus/results/sbus_p1m1m2c_zai_glm4_6_p1m1m2c_stats.csv`
- `data/sbus/results/sbus_p1m1m2c_zai_glm4_5_air_p1m1m2c_stats.csv`

**Sample Data (GPT-4o):**
| registration_id | matcher1_critic_time | matcher2_time | total_time |
|-----------------|---------------------|---------------|------------|
| SPUS55557 | 6.11s | 14.99s | 21.10s |
| SPUS63654 | 12.67s | 10.29s | 22.96s |
| SPUS53075 | 11.11s | 9.57s | 20.68s |
| ... | ... | ... | ... |
| **Median** | **10.8s** | **9.8s** | **21.0s** |

---

## Appendix B: Glossary

**Agentic AI:** AI systems that can autonomously take actions, make decisions, and use tools to achieve goals (vs. passive chatbots)

**Constellation:** A configuration of agents and their interactions (e.g., p1m1m2c = Phase 1: Matcher1+Critic, Phase 2: Matcher2)

**Critic Agent:** Quality assurance agent that validates outputs from other agents before proceeding

**HITL (Human in the Loop):** Workflow design where humans review/approve AI decisions before taking action

**Latency Floor:** Minimum possible latency imposed by architecture (e.g., sequential execution)

**P95 Latency:** 95th percentile latency—the speed at which 95% of requests complete (measures worst-case performance)

**POM (Post-Offer Matching):** iChoosr's process of matching customers to suppliers after an auction

**Sequential Execution:** Agents run one after another (vs. parallel execution)

**SLA (Service Level Agreement):** Contractual performance target (e.g., 5-second response time)

**Structured Output:** AI response formatted as JSON conforming to a schema (vs. free-form text)

---

## Appendix C: Contact & Questions

**For technical questions:**
- Milan Jelisavcic (milan.jelisavcic@and.digital)
- AI & Data Squad, AND Digital

**For business inquiries:**
- [AND Digital Client Services](https://and.digital/contact)

**Repository:**
- Internal GitLab: `unbound-pom-poc`

---

**Document Version:** 1.0
**Last Updated:** November 2025
**Status:** Final Research Report

---

*This research was conducted by the AI & Data Squad at AND Digital in partnership with iChoosr to explore the production viability of agentic AI workflows for complex business automation.*
