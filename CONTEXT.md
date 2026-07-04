# BlackOut

BlackOut helps a person reconstruct and understand regrettable or impulsive late-night digital decisions from messy personal evidence.

## Language

**Evidence**:
Raw user-provided material that may contain one or more late-night decisions, such as pasted messages, order confirmations, notes, receipts, screenshots, or exported chat text.
_Avoid_: Data dump, upload, source

**Primary Demo Evidence**:
Seeded pasteable text evidence used to make the hackathon demo deterministic and fast.
_Avoid_: Live integration, OCR-first demo

**Secondary Evidence Path**:
An optional ingestion route for screenshots or images that supports the product story but is not required for the core demo to succeed.
_Avoid_: Main upload flow, required screenshot path

**Decision**:
An extracted late-night action or commitment that BlackOut can remember, explain, compare, and ask for feedback on.
_Avoid_: Event, item, message, transaction

**Regret Signal**:
A neutral indicator that a decision may be risky, unwanted, expensive, emotionally loaded, or similar to something the user previously marked negatively.
_Avoid_: Bad decision, mistake, moral judgment

**Morning-After Recall**:
The primary first-screen action that reconstructs decisions from the previous late-night window and surfaces their timeline, regret signals, related past decisions, feedback controls, and forgetting controls.
_Avoid_: Generic chat, dashboard landing page

**Late-Night Window**:
The default overnight period BlackOut treats as likely impaired or impulsive, spanning midnight through 5:00am in the user's local time.
_Avoid_: Night, session, day

**Memory Lifecycle**:
The visible product flow that maps BlackOut actions onto Cognee operations: remember evidence, recall decisions, improve memory from feedback, and forget selected data.
_Avoid_: Backend storage, database flow

**Seed Demo Mode**:
A deterministic demo path that loads curated late-night evidence so judges can see the full memory lifecycle without relying on live personal data or unpredictable extraction.
_Avoid_: Mock app, fake integration

**Seed Demo Dataset**:
Curated evidence spanning three late-night windows: the most recent night for the morning-after reveal and two prior nights that establish repeatable decision patterns.
_Avoid_: Single sample, one-off demo data

**Feedback Label**:
A user-applied judgment on a decision, limited in the MVP to Regret, Fine, Funny, or Worth it.
_Avoid_: Rating, score, reaction

**Forget Scope**:
The unit of memory deletion in the MVP, set to an entire late-night window so the user can remove a complete night of evidence and decisions.
_Avoid_: Line deletion, partial cleanup, message removal

**Recall Result**:
The output of morning-after recall, presented as a decision timeline first, pattern insights second, and collapsible raw evidence third.
_Avoid_: Chat answer, report, dashboard

**Ask Your Memory**:
A secondary freeform recall interface for querying remembered evidence and decisions after the primary morning-after recall flow.
_Avoid_: Chatbot, assistant, main interface

**Decision Category**:
The coarse type assigned to an extracted decision, limited in the MVP to purchase, message, note, commit, plan, subscription, or other.
_Avoid_: Intent, diagnosis, personality trait

**Evidence Excerpt**:
A short source snippet shown with a decision so the user can verify where BlackOut found it.
_Avoid_: Full transcript, hidden provenance
