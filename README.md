# BlackOut

BlackOut helps you answer a very specific morning-after question:

> What did I do last night?

It is a small Streamlit app that reconstructs late-night digital decisions from messy evidence such as pasted receipts, messages, notes, commits, and other text traces.

The app turns that evidence into a timeline of decisions, highlights neutral regret signals, shows repeat patterns from prior late-night windows, and gives the user controls to improve or forget memory.

## What It Does

BlackOut focuses on three jobs:

1. Reconstruct what happened in the most recent late-night window.
2. Recognize patterns from previous late-night windows.
3. Repair memory with feedback or forgetting.

The main product action is Morning-After Recall, shown in the app as:

```text
What did I do last night?
```

The app also has Seed Demo Mode. It loads three prepared Late-Night Windows so the demo can show a full memory flow without relying on live personal data:

- The most recent completed midnight-through-5:00am window.
- A prior impulse-purchase pattern window.
- A prior emotional-message pattern window.

Today, the app can:

- Load Seed Demo Mode with three prepared Late-Night Windows.
- Remember pasted Evidence without connecting any personal accounts.
- Reconstruct the most recent Late-Night Window into a Decision timeline.
- Show each Decision with a timestamp, category, source type, people or vendors, amount, neutral regret signals, and an Evidence Excerpt when those details are available.
- Keep raw Evidence behind a collapsible provenance section instead of making it the main result.
- Run deterministically with a fake memory adapter for tests and demos.

## Why It Exists

Late-night digital decisions are easy to scatter across apps and hard to inspect later. A person may wake up unsure what they bought, sent, promised, subscribed to, wrote, or changed.

BlackOut is meant to make that review fast and humane. It is not trying to diagnose the user or shame them. It simply helps them inspect decisions, see possible risk, notice repeats, and choose what memory should be improved or forgotten.

The main idea is simple: show actions and commitments first, not a pile of raw text. A user should be able to scan the timeline and quickly understand what happened.

The MVP uses Streamlit, Python, and Cognee so the demo can make the memory lifecycle visible:

- Remember evidence.
- Recall decisions and answers.
- Improve memory from feedback.
- Forget a late-night window.

## How It Works

Streamlit does not own the product behavior directly. It calls `BlackOutWorkflow`, which is the main interface for product actions.

The workflow talks to a memory adapter. Today the repo includes a fake adapter so the first slices are deterministic and testable. A real Cognee adapter is planned as the next memory implementation behind the same seam.

When the user clicks Seed Demo Mode, the workflow:

1. Finds the most recent completed Late-Night Window using the user's local time.
2. Builds three dated Late-Night Windows from the seed dataset.
3. Sends each window to the memory adapter as its own remembered unit.
4. Confirms that all three windows were loaded.

Each window is remembered as a separable unit so a later Forget Scope action can remove one complete Late-Night Window.

Users can also paste Evidence directly. The workflow stores that text as the most recent completed Late-Night Window, using the same memory adapter seam as Seed Demo Mode.

Morning-After Recall reconstructs remembered Evidence into a deterministic Decision timeline for the most recent Late-Night Window:

- Timestamped decisions.
- MVP Decision Categories: purchase, message, note, commit, plan, subscription, or other.
- People or vendors, amounts, neutral regret signals, and Evidence Excerpts when available.
- Raw Evidence shown only behind the collapsible provenance section.

The current extraction is intentionally narrow and demo-friendly. It reads timestamped text lines such as receipts, messages, notes, tasks, calendar entries, and commits, then turns them into the MVP Decision shape. The real Cognee adapter will later sit behind the same workflow and memory adapter seam.

## Local Development

Install the app and development dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

Run the Streamlit app:

```bash
python3 -m streamlit run app.py
```

Run tests:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest
```

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` keeps unrelated globally installed pytest plugins from affecting this project test run.
