# Product

## Register

product

## Users

A person who wakes up unsure what they bought, sent, promised, subscribed to, wrote, or changed during the previous Late-Night Window (midnight through 5:00am). They open their laptop in morning daylight or soft indoor light, in a calm, private, slightly vulnerable mood, and want to reconstruct what happened — fast, without judgment, and without being buried in raw copied text.

Their context: alone, on a personal device, reviewing evidence they pasted themselves (receipts, chat exports, notes, commits, calendar text). No live accounts, no OAuth, no phone integrations. The job is a private morning-after review, not a data dashboard and not a chat session.

## Product Purpose

BlackOut makes the review of late-night digital decisions fast and humane. It reconstructs the most recent Late-Night Window into a Decision timeline, recognizes repeat patterns from prior windows, and lets the user repair memory with feedback (Regret, Fine, Funny, Worth it) or forgetting.

Success looks like: the user scans the timeline, notices whether anything resembles a prior late-night pattern, applies a plain-word judgment, and walks away understanding what happened — without being shamed, diagnosed, or handed a pile of raw text they have to re-read.

The memory lifecycle (remember, recall, improve, forget) is the product spine, made visible through Cognee. The demo runs entirely on pasted text evidence and a seeded dataset; no personal accounts are required.

## Brand Personality

Calm. Clear. Non-judgmental.

A trusted friend helping you reconstruct the morning after — not a doctor diagnosing you, not a wellness coach tracking your streaks, not a chatbot pretending to be an assistant. The voice is quiet, plain, and honest. Regret signals are neutral indicators ("this resembles something you marked before"), never moral verdicts. The interface treats the user as an adult reviewing their own choices in a safe, private space.

## Anti-references

- **NOT SaaS-cream / glassmorphism / ambient blobs.** No warm-tinted near-white backgrounds, no translucent blurred panels, no decorative blurred color circles. The current cream-brown glassmorphism look is the failure mode being replaced.
- **NOT gamified wellness.** No streaks, rewards, badges, or "morning routine" framing. Late-night decisions are not a game.
- **NOT moralizing or alarm-red.** Regret signals never shout, never diagnose, never use fire-engine red to scare. They are neutral, readable indicators.
- **NOT a centered chatbot UI as the primary surface.** The Decision timeline is the hero; Ask Your Memory is a secondary follow-up, not the main interface. No message bubbles as the primary affordance.
- **NOT novelty or emoji-heavy "late night vibes."** The product is serious about privacy and treats the user as an adult. No cutesy theming.

## Design Principles

1. **Show actions and commitments first, not raw text.** The Decision timeline is the hero of Morning-After Recall. Raw Evidence stays behind a collapsible provenance section, never the main result. A user should scan actions, not re-read receipts.
2. **Never moralize.** Regret signals are neutral indicators of possible risk, not judgments of the user's character. The interface informs, it doesn't diagnose, shame, or alarm.
3. **Make the memory lifecycle visible and controllable.** Remember, recall, improve, and forget are exposed as first-class actions, not hidden behind a chat. Forgetting a complete Late-Night Window is a privacy control on the same surface as the review — never buried in settings.
4. **Calm over loud.** A private morning-after surface, not a dashboard or a streak tracker. Quiet typography, restrained color, and motion that earns its place. The tool should disappear into the task.
5. **Ground everything in evidence.** Every Decision and every Ask Your Memory answer links back to an Evidence Excerpt the user can verify. The product never invents a timestamp, a fact, or an answer it cannot ground.

## Accessibility & Inclusion

WCAG 2.2 AA is the floor: 4.5:1 body text contrast and 3:1 large-text plus UI-component contrast against their backgrounds. Full keyboard navigation with visible focus, semantic landmarks, and correct heading order. `prefers-reduced-motion` is honored on every animation with a crossfade or instant fallback. Category encoding is color-blind-safe: every Decision category is identified by an icon plus a text label, never by color alone.

Light theme is primary (morning daylight, soft indoor light). A dark theme is offered for late-night review sessions, with the same contrast guarantees in reverse.