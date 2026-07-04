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

The current implementation includes:

- A Streamlit app.
- A `BlackOutWorkflow` product seam.
- Typed domain objects for Late-Night Window, Decision, Regret Signal, Evidence Excerpt, and Recall Result.
- Seed Demo Mode that remembers three separable Late-Night Windows from committed Primary Demo Evidence.
- A deterministic fake memory adapter for tests and demos.
- A Recall Result layout with timeline first, pattern insights second, and raw evidence tucked behind an expander.

## Why It Exists

Late-night digital decisions are easy to scatter across apps and hard to inspect later. A person may wake up unsure what they bought, sent, promised, subscribed to, wrote, or changed.

BlackOut is meant to make that review fast and humane. It is not trying to diagnose the user or shame them. It simply helps them inspect decisions, see possible risk, notice repeats, and choose what memory should be improved or forgotten.

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

The current recall tracer bullet returns one deterministic Recall Result:

- A late-night purchase decision.
- A neutral regret signal.
- A prior-pattern insight.
- The raw evidence excerpt used to explain the result.

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
