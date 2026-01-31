# Update from the AI & Data Squad: POM AI PoC Performance Benchmark Results

Hey team!:wave: I'm revisiting the POM AI PoC project for iChoosr (from April 2025), and I ran some follow-up benchmarks on the original agentic workflow.

## Context

Back in April, we concluded the 3-agent system was accurate but too slow (>12s median, far from the 5s target). Since then, new models dropped, so I wanted to test the performance.

## What We Tested

We benchmarked the agentic workflow for **auction result matching** - the process of matching customer registrations with supplier offers after an auction completes. This is a critical business process for iChoosr where:

- Customers register for products (solar panels, heat pumps)
- Suppliers participate in auctions with their offers
- The system must match customers to the best supplier based on their needs and available offers

## How We Tested

We ran test cases across all models (10-14 test cases per model), measuring the total processing time for both agents in the workflow:

1. **Matcher1/Critic Agent**: Analyzes customer requirements and supplier offers
2. **Matcher2 Agent**: Performs the final matching based on the critic's analysis

For each model, we calculated the median total processing time across all test cases.

## The Question

Can newer LLMs finally push us under the speed threshold?

Spoiler: Still no. But the gap is closing.

## Models Tested (Oct 2025)

- `gpt-4o` (original baseline)
- `gpt-5` (flagship, Aug 2025)
- `gpt-5-mini` (lightweight)
- `glm-4.6` (Zhipu AI, Sept 2025)
- `glm-4.5-air` (speed-optimized)

## Key Results (Median Speed & Accuracy)

| Model         | Median Speed | Accuracy (Price/Subsidy Match) | Notes                                                 |
| ------------- | ------------ | ------------------------------ | ----------------------------------------------------- |
| `gpt-4o`      | **10.3s**    | 100%                           | Original benchmark - consistent performance           |
| `gpt-5`       | **149.2s**   | 100%                           | *Most accurate*, but slowest (deep reasoning)         |
| `gpt-5-mini`  | **96.4s**    | 93.3%                          | Faster than full GPT-5, some accuracy trade-offs         |
| `glm-4.6`     | **17.2s**    | 83.3%                          | Faster than GPT-4o, but notable accuracy drop          |
| `glm-4.5-air` | **65.1s**    | 80.0%                          | Speed-optimized, significant accuracy compromises        |

All still >10s median — confirms agentic handoffs + complex logic are the real bottleneck, not just model speed.

## Business Impact & Next Steps

From a business perspective, we're still not meeting the 5-second target needed for a seamless customer experience. The results show a clear speed-accuracy tradeoff:

- **GPT-4o and GPT-5** maintain 100% accuracy but can't meet speed targets
- **GLM models** achieve faster speeds but with 15-20% accuracy drops, which may not be acceptable for production

Our research goals moving forward:

1. **Reduce processing time** to meet the 5-second target without sacrificing accuracy
2. **Evaluate architectural changes** to minimize agent handoffs
3. **Explore industry applications** beyond iChoosr, particularly in other matching-heavy industries

We plan to present these findings back to iChoosr to discuss next steps for their platform re-platforming project. The insights from this research could also apply to other clients in retail, financial services, and healthcare where complex matching is required.

## Technical Next Steps

While we explore architectural improvements, we're focusing on two key areas:

1. **Standardize offer JSON format** - This could provide the biggest speed win by reducing parsing complexity
2. **Switch to MCP server instead of file I/O** - Current file operations add 2-4s latency per agent call. MCP's in-memory context + parallel tool calls could potentially cut total time significantly

## Deep Dive Resources

For those interested in the full project details:

- [POM Final Playback](https://docs.google.com/presentation/d/1nIc-Bm6ZBCt0bEZb3X_lZRa927N0B12JW2WvXCGUZgg/edit)
- [POM Demo](https://docs.google.com/presentation/d/1aZgJ-AVSfDejT2CUp7LxmOXu1zsVWZ3bObc1llZrMpc/edit)

## Research Documentation

I'm currently writing up a longer research report, which will be available in Google Docs in our shared squad folder (not Confluence as previously mentioned). I'll share the link once it's ready.

Original conclusion stands: Not a question of yes or no, but when.
