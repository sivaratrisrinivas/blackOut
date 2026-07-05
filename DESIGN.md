# BlackOut — DESIGN.md

The visual system for BlackOut's morning-after recall surface. Captured after the UI redesign so future variants stay on-brand. Read alongside [PRODUCT.md](./PRODUCT.md) — PRODUCT wins on strategic/voice decisions, DESIGN wins on visual ones.

## Register

Product. Design serves the morning-after recall workflow. Earned familiarity, not strangeness: the tool should disappear into the task.

## Concept

The side rail is the **night** — a warm-tinted near-black where the decisions were made. The workspace is the **morning** — clean paper-white where you review them. The copper-amber accent is the lamplight connecting the two. This is a meaningful metaphor, not decoration: the user literally moves from night (rail) into morning light (workspace) to review last night.

## Color strategy

Restrained. Tinted neutrals carry the surface; the copper accent appears on primary actions, the active step, and category/feedback chips only (well under 10% of any screen). The body background is a true paper-white (OKLCH L 0.985), not cream — warmth is carried by accent, typography, and the dark rail, never by a warm-tinted body.

All color is OKLCH. Light is primary (morning daylight); a dark theme is offered for late-night review with the same contrast guarantees in reverse.

### Light theme tokens

| Role | Token | Value |
|---|---|---|
| Body | `--bg` | `oklch(0.985 0.004 75)` |
| Surface (cards) | `--surface` | `oklch(1 0 0)` |
| Sunken (code/excerpts) | `--surface-2` | `oklch(0.972 0.005 250)` (cool) |
| Night rail | `--rail` | `oklch(0.255 0.012 70)` |
| Ink (body text) | `--ink` | `oklch(0.27 0.012 70)` |
| Muted text | `--muted` | `oklch(0.48 0.014 70)` |
| Hairline | `--line` | `oklch(0.905 0.008 75)` |
| Strong line | `--line-strong` | `oklch(0.78 0.012 75)` |
| Accent | `--accent` | `oklch(0.57 0.12 65)` |
| Accent strong (text/buttons) | `--accent-strong` | `oklch(0.45 0.11 60)` |
| Accent soft (tints) | `--accent-soft` | `oklch(0.965 0.025 75)` |

### Dark theme

The whole surface becomes night: `--bg` `oklch(0.21 0.012 70)`, `--surface` `oklch(0.245 0.013 70)`, `--rail` deepens to `oklch(0.175 0.012 70)`, ink lightens to `oklch(0.93 0.008 75)`, accent brightens to `oklch(0.72 0.12 65)`. Chip pairs invert to dark tinted backgrounds with light foregrounds. Full token set lives in `globals.css`.

### Semantic pairs (light)

Every chip uses a paired tint (`-bg`) plus a darker same-hue text (`-fg`) so contrast clears 4.5:1 by construction.

- **Categories** (icon + label, never color alone): purchase (amber 60), message (blue 250), note (green 130), commit (violet 295), plan (teal 200), subscription (magenta 340), other (neutral).
- **Feedback**: Regret (clay 28 — restrained, not alarm-red), Fine (slate 225), Funny (plum 315), Worth it (forest 160).
- **Risk**: possible-risk uses the accent; confirmed-regret uses the restrained clay (never fire-engine red).

## Typography

Two faces, paired on a contrast axis (serif display + neo-grotesque UI). Both self-hosted via `next/font/google` (no runtime network dependency).

- **Fraunces** (`--font-display`): serif. Used **only** for human-facing section voice — the welcome hero, screen h2 titles, the finish card title. Never for buttons, labels, chips, data, or decision summaries (product register ban on display fonts in UI/data).
- **Inter** (`--font-ui`): neo-grotesque sans. Carries everything functional — body, summaries, timestamps, buttons, chips, evidence excerpts, answers.
- **Mono** (`--font-mono`): `ui-monospace` stack. Timestamps, amounts, raw evidence, evidence excerpts.

Fixed rem scale (not fluid — product UI, consistent DPI), ratio ~1.2. Scale tokens `--step-1` (0.75rem) through `--step-9` (2.75rem). Hero ceiling 2.75rem (calm, not shouting). Display letter-spacing floor -0.02em (well inside the -0.04em floor). `text-wrap: balance` on headings, `pretty` on prose. Body line length capped ~64ch on prose; data runs denser.

## Layout

- `.app`: 248px night rail + flexible workspace, edge-to-edge, min-height 100vh. No outer glass frame, no ambient blobs.
- Workspace content max-width 880px (640px for narrow/form screens), centered with generous padding.
- Flexbox for 1D (button rows, chips), Grid for 2D (welcome split, feedback grid, prompts).
- Responsive grids use `minmax(0, 1fr)` columns; no breakpoints for fluid type — breakpoints step the fixed scale down on mobile only.
- z-index scale: rail sticky = 20; status/modal layers above as needed. No arbitrary 999.

## Components

Every interactive component ships all states: default, hover, focus-visible (3:1 amber ring via `box-shadow: 0 0 0 3px var(--ring)`), active (translateY 0.5px), disabled (opacity 0.55), loading (`aria-busy` + CSS spinner via `::after`).

- **Buttons** (`.btn`): radius 10px, min-height 44px. `.btn-primary` (copper, white text in light; amber, dark text in dark), `.btn-secondary` (surface + strong line), `.btn-danger` (transparent + clay, restrained), `.btn-ghost`. One consistent shape across the surface.
- **Cards** (`.decision-card`, `.insight-card`, `.answer-card`): radius 12px, 1px line + soft low-blur shadow (≤8px). No border+wide-shadow combo.
- **Chips** (`.chip`): pill 999px, small icon + label. Category and feedback variants via `--c-bg`/`--c-fg` pairs.
- **Inputs** (`.textarea`, `.input`): radius 10px, strong line, amber focus ring. Textarea is mono.
- **Decision card**: timestamp + category chip (icon+label+color) + source + amount, then summary (sans, 600), neutral regret-signal chips (clay dot + text), evidence excerpt (mono, sunken, left rule).
- **Raw evidence**: collapsible `<details>` provenance section, never the main result.
- **Stepper** (`.steps`): `<ol>`, numbered; active = amber fill, done = check, `aria-current="step"`.
- **Theme toggle**: CSS-only knob reflecting `[data-theme]`; click flips `data-theme` on `<html>` and persists to `localStorage`.
- **Empty states** teach (title + hint), never "nothing here."
- **Loading**: button `aria-busy` spinner + status line with `role="status"` / `aria-live="polite"`. No mid-content spinners.

## Motion

180ms, `cubic-bezier(0.22, 1, 0.36, 1)` (ease-out-quint). Screen entry is a 6px rise + fade conveying state change. Status spinner + skeleton shimmer for async. `prefers-reduced-motion: reduce` collapses every animation to ~instant (opacity-only / none). No decorative motion, no orchestrated load sequences, no bounce/elastic.

## Accessibility

WCAG 2.2 AA: 4.5:1 body / 3:1 large-text + UI components. Full keyboard nav with visible focus rings. Semantic landmarks (`main`, `aside`, `nav`, `header`). `aria-current` on the active step, `aria-pressed` on feedback buttons, `aria-busy` on loading buttons, `role="status"` + `aria-live` on status. Category encoding is color-blind-safe (icon + text label, color is reinforcement only). Two-step inline confirm for the destructive Forget action.

## What was removed (vs. the prior design)

Cream/sand body background, glassmorphism frame (`backdrop-filter: blur`), ambient blurred color blobs, the 8px-everything radius, the warm-cream code blocks, gradient text, and `clamp()`-fluid headings. Replaced with a grounded night-rail / paper-morning surface, restrained copper accent, serif section voice, fixed rem scale, and full component states.