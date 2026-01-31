  Agentic AI for Auction Matching Research

  ---
  Slide 1: Title - The Goal (15 seconds)

  "Hi everyone, I'm Milan from the AI & Data Squad. Today I want to share a research story about testing agentic AI for a real business problem at iChoosr - and what happened when we tried the
  latest models to see if they could finally meet our speed requirements."

  ---
  Slide 2: The Challenge with POM (45 seconds)

  "Let me set the context. iChoosr runs energy auctions - think solar panels, heat pumps, batteries. After an auction completes, they need to match each customer registration to the right
  supplier, product, price, and subsidies.

  This needs to be user-friendly and scalable. But the biggest challenge is the fluid nature of it all - product combinations change, subsidies vary by location and eligibility rules, and markets
  differ across regions. Traditional rule-based systems struggle to keep up with these constantly changing requirements."

  ---
  Slide 3: Testing Agentic AI Workflows (40 seconds)

  "So back in April 2025, we asked: could agentic AI workflows solve this? We had two goals.

  First, validate if agentic workflows are technically feasible and viable for automating this complex matching process.

  Second, learn how agentic systems work so we could potentially apply them across other parts of iChoosr's business.

  This was both a proof-of-concept and a learning opportunity for us."

  ---
  Slide 4: Section - Our Approach (5 seconds)

  [Section divider - no speaking, quick transition]

  ---
  Slide 5: Optimizing the Workflow (60 seconds)

  "Efficiency and accuracy were our main drivers when designing the agent workflow. We actually started with a four-agent setup, but it was accurate yet too slow.

  So we tested different configurations - removing agents, changing their responsibilities, shortening prompts. You can see the evolution here: we went from a complex four-agent system with a
  Critic coordinating multiple experts, to a simpler two-agent sequential flow, and finally landed on a three-agent system with the Matcher expert, a Critic, and a Subsidy & pricing expert working
   together.

  After extensive testing, this three-agent constellation proved to be the most efficient balance of speed and accuracy. This became our baseline for the April benchmark with GPT-4o."

  ---
  Slide 6: Section - Results (5 seconds)

  [Section divider - quick transition]

  ---
  Slide 7: Results Evaluation Criteria (50 seconds)

  "We set clear evaluation criteria. Most importantly: does it match registrations to the right supplier, product, price, and subsidies? The answer was yes - generally 100% accuracy, though we saw
   it drop to between 98% and 93.7% with some models.

  Can it handle variable data input? Yes, based on varying JSON structures from different suppliers.

  Is it reasonable and auditable? Yes, we can log the steps.

  The multilingual and multi-product line capability? We deprioritized this for the PoC.

  But here's the critical failure: timely delivery. Based on the 5-second business requirement, we got a big red X. That's the problem we wanted to solve.

  Cost estimations for OpenAI were significant, and we wanted to test alternatives. And measuring the impact of different AI models - that's exactly what this October research was about."

  ---
  Slide 8: Initial Speed Results (55 seconds)

  "Here were the results from April. OpenAI GPT-4o performed best - 12.6 seconds median with incentives in the prompts. We also tested different scenarios: 100% unique zipcodes, 50% shared
  zipcodes, and 50% shared without batteries. The times ranged from 12.6 to 18.3 seconds.

  We also tested DeepSeek through Azure AI, which came in around 17.5 to 18.1 seconds.

  Two key findings: First, speed performance had improved from our earlier tests, but we were still nowhere near the 5-second business requirement. We were 2.5 to 3.5 times slower than needed.

  Second, and this was surprising - adding incentives in the prompts had no positive impact on speed. This told us that prompt engineering wasn't going to be the solution."

  ---
  Slide 9: Testing New Models (October 2025) (70 seconds)

  "So fast forward to October 2025. New models have dropped: GPT-5 in August as the flagship, GPT-5-mini as a lightweight version, and Zhipu AI released GLM-4.6 and GLM-4.5-air. I thought: maybe
  model improvements alone can finally get us under 5 seconds.

  I ran the same test cases again. Here are the results, and they're revealing:

  GPT-4o from April is STILL the fastest at 12.6 seconds median with 100% accuracy. That's our baseline.

  But look at GPT-5: 189.9 seconds median. That's 15 times slower! Yes, it's 100% accurate and 'most accurate' with deep reasoning capabilities, but it's unusable for this use case.

  GPT-5-mini: 99 seconds, but accuracy dropped to 97.8%.

  GLM-4.6 actually showed promise - 11.4 seconds with 100% accuracy. That's faster than GPT-4o!

  But wait - when I looked closer at my corrected results, GLM-4.6 was actually closer to 17-18 seconds in production scenarios, and accuracy was more like 83-85%. So the 'best balance' claim
  didn't quite hold up.

  GLM-4.5-air: 65.3 seconds with 97.8% accuracy.

  The headline: New models are NOT adding to the speed. In fact, the flagship models are dramatically slower."

  ---
  Slide 10: Section - What Next? (5 seconds)

  [Section divider]

  ---
  Slide 11: Code Improvements (40 seconds)

  "So we tried code improvements. We added batch file writes which gave us 10-15% speedup. We added an enable_thinking parameter for GLM models. We refactored the architecture with unified
  ConfigurableWorkflow using YAML-based configs. We reorganized data, separated capacity tracking from offers, added scenario-based workflow systems.

  We improved code quality with type hints, standardized naming, refactored tests, added debug logging.

  All good engineering practices. But the bottom line? These might add to the speed marginally, but they don't solve the fundamental problem."

  ---
  Slide 12: Section - Conclusion (5 seconds)

  [Section divider]

  ---
  Slide 13: At This Stage, Not Confident Enough (75 seconds)

  "So here's where we landed. At this stage, we're not confident enough to deploy this to production.

  On the Pros side: We are confident the agent can accurately manage the complexity of the task. That's validated. The system has flexibility to scale across different product lines. These are
  real wins.

  But the Cons are significant: Concerns on consistency of timing to complete matching. Sometimes 12 seconds, sometimes 18 seconds - that variability is a problem. The system is too sensitive for
  critical infrastructure - small prompt changes can affect results. And most importantly, this is a crucial point in the customer journey with direct impact on conversion rates. That means there
  are limited opportunities for Human In The Loop - we can't have someone manually reviewing each match.

  Our conclusion: You can't optimize your way to 5 seconds with the current architecture. It needs a fundamental redesign.

  What could that look like? Maybe a single-agent approach to eliminate handoffs. Maybe parallel agent execution instead of sequential. Or maybe pre-computed matching rules with AI as a fallback
  for edge cases. These are directions to explore, but they're architectural changes, not model swaps or code optimizations."

  ---
  Slide 14: Key Takeaways & Q&A (30 seconds)

  "So what did we learn?

  One: Model improvements alone won't solve architectural bottlenecks. Sequential workflows have inherent latency.

  Two: The speed-accuracy trade-off is real and asymmetric. Newer 'smarter' models can be 15 times slower.

  Three: Architecture matters. I/O operations, agent handoffs - these are where the time goes.

  Four: Agentic AI is powerful but not universal. It works great for research and analysis where speed is less critical. But for real-time customer-facing workflows? We're not quite there yet.

  Five: It's not 'if' but 'when.' The technology will catch up. But for this use case, at this moment, we need a different approach.

  Happy to take questions!"

  ---
  Timing Breakdown:

  - Slide 1: 15s
  - Slide 2: 45s
  - Slide 3: 40s
  - Slide 4: 5s
  - Slide 5: 60s
  - Slide 6: 5s
  - Slide 7: 50s
  - Slide 8: 55s
  - Slide 9: 70s
  - Slide 10: 5s
  - Slide 11: 40s
  - Slide 12: 5s
  - Slide 13: 75s
  - Slide 14: 30s

  Total: ~8 minutes

  ---
  Delivery Tips:

  1. Slide 5 (workflow diagrams): Point to the visual evolution as you speak - this helps the audience follow along
  2. Slide 7 (evaluation table): Use your hand/pointer to guide through the checkmarks and X's
  3. Slide 8 (speed table): Emphasize the numbers - "12.6, 15.1, 18.3" - this builds the pattern
  4. Slide 9 (new models table): Build suspense - start with GPT-4o baseline, then the shocking GPT-5 number, then land on "none of them solved it"
  5. Slide 13 (Pros/Cons): Pause between Pros and Cons sections - let the weight of each side sink in

  ---
  If You Need to Adjust Timing:

  To shorten (6-7 minutes):
  - Condense Slide 5 (workflow) to 40s
  - Condense Slide 8 (initial results) to 40s
  - Condense Slide 11 (code improvements) to 25s

  To extend (10 minutes):
  - Add 15s to Slide 9 to dive deeper into why GPT-5 is so slow
  - Add 20s to Slide 13 to discuss potential business impact
  - Add a final slide about next steps or broader applications

  This version follows your existing slide structure exactly and incorporates all your actual data! 🎯
