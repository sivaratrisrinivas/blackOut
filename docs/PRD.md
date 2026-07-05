# BlackOut MVP PRD

## Problem Statement

People often wake up after a late-night window with fragmented memory of what they bought, sent, promised, subscribed to, wrote, or changed. The evidence is scattered across messages, receipts, notes, screenshots, and other digital traces, so reconstructing the night requires awkward manual scrolling and still does not reveal repeat patterns.

BlackOut addresses the specific pain of late-night digital amnesia: the user wants to know what actually happened, which decisions may deserve attention, what they have regretted doing at similar hours before, and how to remove sensitive memory when they no longer want it stored.

## Solution

BlackOut is a focused Next.js and Python app that turns messy late-night evidence into remembered decisions using Cognee. The user can load a deterministic seed demo dataset or paste their own evidence, run Morning-After Recall for the most recent late-night window, inspect a Recall Result, apply Feedback Labels, query remembered context through Ask Your Memory, and forget an entire late-night window.

The MVP centers on three submission beats:

1. Reconstruct what happened in the most recent late-night window.
2. Recognize patterns from previous late-night windows.
3. Repair memory with feedback or forgetting.

## User Stories

1. As a hackathon judge, I want to press one obvious Morning-After Recall button, so that I can understand BlackOut's core value within seconds.
2. As a user, I want BlackOut to ingest pasted evidence, so that I can reconstruct late-night decisions without connecting personal accounts.
3. As a demo presenter, I want a Seed Demo Mode, so that the presentation is deterministic and does not depend on live personal data.
4. As a demo presenter, I want the Seed Demo Dataset to include three late-night windows, so that BlackOut can show both last night's decisions and prior patterns.
5. As a user, I want each late-night window to be separable, so that I can forget one night without deleting everything.
6. As a user, I want the default late-night window to span midnight through 5:00am, so that BlackOut captures the main period where impulsive decisions are likely to occur.
7. As a user, I want BlackOut to extract decisions from evidence, so that I can see actions and commitments instead of raw text dumps.
8. As a user, I want each decision to include a timestamp when available, so that I can understand the sequence of the night.
9. As a user, I want each decision to include a Decision Category, so that purchases, messages, notes, commits, plans, subscriptions, and other decisions are easy to scan.
10. As a user, I want each decision to include people or vendors when available, so that I can recognize who or what was involved.
11. As a user, I want each decision to include an amount when available, so that spending decisions stand out.
12. As a user, I want each decision to include Regret Signals, so that risky or repeat behavior is surfaced without moral judgment.
13. As a user, I want each decision to include an Evidence Excerpt, so that I can verify where BlackOut found it.
14. As a user, I want the Recall Result to show a timeline first, so that I can quickly reconstruct what happened.
15. As a user, I want the Recall Result to show pattern insights second, so that I can see whether similar decisions happened before.
16. As a user, I want raw evidence to be collapsible, so that I can inspect provenance without cluttering the main result.
17. As a user, I want BlackOut to show similar prior decisions, so that I can understand repeat late-night patterns.
18. As a user, I want BlackOut to distinguish possible risk from confirmed regret, so that the app does not overstate what it knows.
19. As a user, I want to mark a decision as Regret, so that future recall can highlight similar decisions.
20. As a user, I want to mark a decision as Fine, so that BlackOut learns not every late-night decision is a problem.
21. As a user, I want to mark a decision as Funny, so that the app preserves the humor of harmless odd choices.
22. As a user, I want to mark a decision as Worth it, so that unusual decisions can be remembered positively.
23. As a user, I want feedback to improve the memory layer, so that future pattern insights reflect my actual judgment.
24. As a user, I want to ask freeform questions through Ask Your Memory, so that I can query the memory beyond the default summary.
25. As a user, I want suggested prompts, so that I can quickly ask useful questions without inventing them.
26. As a user, I want to ask what I bought after midnight, so that spending decisions are easy to find.
27. As a user, I want to ask whether I messaged anyone emotionally risky, so that sensitive communication is surfaced.
28. As a user, I want to ask what I should cancel today, so that subscriptions or purchases can become actionable.
29. As a user, I want to forget an entire late-night window, so that sensitive evidence and decisions can be removed naturally.
30. As a user, I want the app to confirm when forgetting succeeds, so that I trust the privacy control.
31. As a hackathon judge, I want to see visible use of Cognee's memory lifecycle, so that I can evaluate the project against the Best Use of Cognee criterion.
32. As a developer, I want the app to call Cognee for remembering evidence, so that ingestion is not a fake demo path.
33. As a developer, I want the app to call Cognee for recalling decisions and answers, so that retrieval demonstrates persistent memory.
34. As a developer, I want the app to call Cognee improve or memify after feedback, so that feedback visibly affects the memory story.
35. As a developer, I want the app to call Cognee forget for late-night window deletion, so that privacy is backed by the memory layer.
36. As a developer, I want Cognee credentials to come from environment variables, so that secrets stay out of the repository.
37. As a developer, I want a fake Cognee adapter for tests, so that BlackOut behavior can be tested deterministically.
38. As a developer, I want an optional real Cognee smoke path, so that configured environments can verify the live integration.
39. As a developer, I want the Next.js UI to depend on a product workflow seam, so that UI code does not own domain behavior.
40. As a maintainer, I want the README to explain Reconstruct, Recognize, Repair, so that the submission narrative is clear.
41. As a maintainer, I want out-of-scope integrations clearly excluded, so that the MVP does not drift into phone, email, or shopping platform OAuth.
42. As a user, I want BlackOut to avoid psychological diagnosis, so that the product remains tasteful and focused on decisions.
43. As a user, I want the tone to be witty but not shaming, so that I can use it without feeling judged.
44. As a demo presenter, I want the app to work even when screenshot OCR is not used, so that the core demo remains reliable.
45. As a future user, I want screenshot upload to remain possible as a secondary evidence path, so that the product direction still includes visual evidence.

## Implementation Decisions

- BlackOut will use a Next.js frontend, a Python workflow/API layer, and Cognee for memory, as recorded in the current architecture decisions.
- The primary implementation seam will be a product workflow service named conceptually as `BlackOutWorkflow`.
- The frontend will call the workflow service through API endpoints for all product actions instead of directly owning Cognee calls or decision extraction behavior.
- The workflow service will expose actions for loading the Seed Demo Dataset, remembering evidence, running Morning-After Recall, asking memory, applying feedback, improving memory, and forgetting a late-night window.
- Cognee access will sit behind an adapter interface so tests can use a deterministic fake adapter while the app uses the real Cognee Python SDK.
- The real adapter will use configured environment variables for Cognee and LLM credentials. Secrets may exist in the user's shell configuration, but the application must only read environment variables and must not copy secret values into tracked files.
- The Seed Demo Dataset will contain three late-night windows: the most recent window for the main reveal and two prior windows that establish repeat decision patterns.
- The primary evidence path is pasted text and committed seed evidence. Screenshot upload is a secondary evidence path and is not required for the core demo.
- A late-night window is the default forget scope and should be mapped to a separable Cognee dataset or dataset-like unit.
- Morning-After Recall uses the most recent completed midnight through 5:00am late-night window in the user's local time.
- A decision is the central extracted object. Evidence, categories, people, vendors, amounts, regret signals, feedback, and evidence excerpts attach to decisions.
- The MVP extraction schema is intentionally narrow: timestamp, decision summary, decision category, source type, people or vendors, amount, regret signals, and evidence excerpt.
- Decision categories are limited to purchase, message, note, commit, plan, subscription, and other.
- Feedback labels are limited to Regret, Fine, Funny, and Worth it.
- Regret Signals are neutral indicators, not moral judgments or psychological explanations.
- The Recall Result is presented as a timeline first, pattern insights second, and collapsible raw evidence third.
- Ask Your Memory is secondary to Morning-After Recall and should include suggested prompts.
- The app should visibly map product actions onto Cognee's memory lifecycle: remember evidence, recall decisions and answers, improve from feedback, and forget a late-night window.
- Public API integrations are not part of the MVP. Public API lists may inform future enrichment, but the MVP should not depend on external public APIs beyond Cognee and configured model providers.

## Testing Decisions

- Good tests should verify externally visible BlackOut behavior and avoid testing Cognee internals, frontend framework internals, or private helper implementation details.
- The highest-value test seam is the workflow service. Tests should ask product-level questions such as whether seeded evidence can produce a Recall Result with timeline decisions, pattern insights, evidence excerpts, feedback behavior, and forget behavior.
- Most automated tests should run against a fake Cognee adapter that records calls and returns deterministic recall data.
- The fake adapter should verify that the workflow makes the expected memory lifecycle calls for remember, recall, improve, and forget.
- Extraction behavior should be tested through expected decision outputs from representative evidence, not by asserting on prompt wording.
- Seed Demo Dataset behavior should be tested by loading all three windows and confirming that the workflow can identify the most recent late-night window and prior pattern-building windows.
- Feedback behavior should be tested by applying each Feedback Label and confirming that the workflow records the label and triggers memory improvement.
- Forget behavior should be tested by forgetting a late-night window and confirming the workflow no longer presents that window in product-level results.
- Ask Your Memory should be tested by sending a freeform question through the workflow and confirming the adapter receives a recall query and returns a user-facing answer.
- One optional smoke test may run against real Cognee when credentials are configured, but it should be skipped by default when the environment is missing required values.
- There is no existing prior test suite in this repository, so the first implementation should establish the workflow test pattern.

## Out of Scope

- Full phone integration.
- Gmail, Amazon, Telegram, Slack, or social account OAuth.
- User accounts, authentication, and multi-user permissions.
- A polished native mobile app.
- Replacing the Python workflow with a JavaScript-only domain layer.
- Public API integrations from curated API lists.
- Production-grade screenshot OCR as a required path.
- Complex agent frameworks.
- Social sharing features.
- Deep psychological inference, diagnosis, or cause attribution.
- Automatic cancellation of purchases or subscriptions.
- Real payment, shopping, messaging, or email actions.
- Fine-grained deletion of individual lines or messages.
- Long-term analytics dashboards beyond the Recall Result and pattern insight needed for the demo.

## Further Notes

- The hackathon theme and judging criteria strongly favor a demo where the memory lifecycle is visible. BlackOut should make Cognee feel necessary, not incidental.
- The MVP should optimize for the 5 to 10 second demo moment: the user opens the app, clicks Morning-After Recall, and immediately sees last night's decisions plus a prior regret pattern.
- The product tone should be witty, specific, and humane. It should help the user inspect decisions without shaming them.
- The application should disclose AI assistant usage in the final hackathon submission, because the hackathon rules require disclosure.
- Real Cognee credentials are expected to be configured in the user's shell environment. Implementation should document required environment variable names without exposing secret values.
