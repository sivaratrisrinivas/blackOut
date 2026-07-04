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
- Compare the most recent Late-Night Window with prior remembered windows and show similar prior Decisions as Pattern insights.
- Label Pattern insights as possible risk until the user marks a related Decision as Regret.
- Let the user apply one of four Feedback Labels to a Decision: Regret, Fine, Funny, or Worth it.
- Improve remembered Decisions from feedback so future recall can show the user's actual judgment.
- Let the user ask a freeform Ask Your Memory question after Morning-After Recall.
- Offer suggested Ask Your Memory prompts for purchases after midnight, emotionally risky messages, and things to cancel today.
- Answer Ask Your Memory questions with plain-English answers grounded in remembered Decisions and Evidence Excerpts.
- Forget an entire Late-Night Window after confirmation, removing that window from future recall.
- Keep forgotten Late-Night Windows out of both Morning-After Recall and Ask Your Memory answers.
- Keep raw Evidence behind a collapsible provenance section instead of making it the main result.
- Run deterministically with a fake memory adapter for tests and demos.

## Why It Exists

Late-night digital decisions are easy to scatter across apps and hard to inspect later. A person may wake up unsure what they bought, sent, promised, subscribed to, wrote, or changed.

BlackOut is meant to make that review fast and humane. It is not trying to diagnose the user or shame them. It simply helps them inspect decisions, see possible risk, notice repeats, and choose what memory should be improved or forgotten.

The main idea is simple: show actions and commitments first, not a pile of raw text. A user should be able to scan the timeline, notice whether anything resembles a prior late-night pattern, and quickly understand what happened.

Pattern insights matter because repeat behavior is often the useful part of memory. A single late-night purchase might be fine. Seeing that it looks like a previous late-night purchase gives the user better context without calling it a mistake.

Feedback Labels matter because BlackOut should not pretend every late-night Decision is a problem. Regret teaches the memory layer to treat similar future Decisions more seriously. Fine, Funny, and Worth it let the user say, in plain terms, that a strange-looking Decision was harmless, amusing, or actually a good call.

Ask Your Memory matters because the default timeline cannot predict every question a user wakes up with. The timeline stays first, but the user can ask a targeted follow-up such as what they bought after midnight, whether an emotionally loaded message showed up, or what they should cancel today. The answer stays grounded in remembered Decisions and Evidence instead of becoming a generic chatbot response.

Forgetting matters because some remembered evidence is sensitive. The MVP keeps the privacy control simple: the user forgets one whole Late-Night Window, not individual lines, so the app can remove that night cleanly and confirm what happened.

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

After the timeline, Morning-After Recall compares current Decisions with prior remembered Decisions. When it finds a similar category with the same person or vendor, it returns a Pattern insight with:

- A possible-risk status.
- A short plain-English summary.
- The current Decision that triggered the insight.
- Compact related prior Decisions, such as timestamp, summary, vendor or person, and amount when available.

The app shows those Pattern insights before raw Evidence. This gives the user enough context to recognize the pattern without exposing full prior transcripts by default.

Ask Your Memory appears after the Recall Result, so it stays secondary to the main Morning-After Recall action. The workflow exposes three suggested prompts:

- What did I buy after midnight?
- Did I message anyone emotionally risky?
- What should I cancel today?

The user can also type a freeform question. Streamlit sends both suggested prompts and typed questions through `BlackOutWorkflow`, and the workflow asks the memory adapter for an answer. The fake adapter records the question for tests, finds matching remembered Decisions in the active Late-Night Window, and returns:

- The original question.
- A short user-facing answer.
- The Evidence Excerpts that ground the answer.

If a Late-Night Window has been forgotten, Ask Your Memory uses the same forgotten-window state as Morning-After Recall, so deleted Evidence is not shown again in an answer.

Each recalled Decision now includes Feedback Label actions. When the user marks a Decision as Regret, Fine, Funny, or Worth it, Streamlit sends that choice back through `BlackOutWorkflow`. The workflow records the label through the memory adapter and returns an updated Recall Result, so the page can keep the timeline, Pattern insights, and raw Evidence in place.

The fake memory adapter records every improve-memory call for tests. It also attaches the latest Feedback Label to matching recalled Decisions. If a current Pattern insight is related to a Decision marked Regret, the insight changes from possible risk to confirmed regret. Other labels are still remembered, but they do not turn a pattern into confirmed regret.

The Recall Result also exposes the MVP Forget Scope: one complete Late-Night Window. After the user confirms the action, Streamlit routes the forget request through `BlackOutWorkflow`, the memory adapter forgets that window as a separable remembered unit, and the next Morning-After Recall excludes its Evidence and Decisions.

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
