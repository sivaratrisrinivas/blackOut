"use client";

import {
  ArrowLeft,
  ArrowRight,
  Brain,
  CalendarClock,
  Check,
  ChevronDown,
  Circle,
  CircleAlert,
  Clock3,
  Eye,
  GitCommit,
  MessageCircleQuestion,
  MessageSquare,
  Moon,
  NotebookText,
  RefreshCw,
  RotateCcw,
  ShoppingCart,
  Sparkles,
  StickyNote,
  Trash2
} from "lucide-react";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";

type Decision = {
  timestamp: string;
  summary: string;
  category: string;
  source_type: string;
  people_or_vendors: string[];
  amount: string | null;
  regret_signals: string[];
  evidence_excerpt: string;
  feedback_label: string | null;
};

type PatternInsight = {
  status: string;
  summary: string;
  current_decision_excerpt: string;
  related_prior_decisions: Array<{
    timestamp: string;
    summary: string;
    amount: string | null;
    people_or_vendors: string[];
    feedback_label: string | null;
  }>;
};

type Recall = {
  window: {
    label: string;
    starts_at: string;
    ends_at: string;
    memory_key: string;
  };
  timeline: Decision[];
  pattern_insights: PatternInsight[];
  raw_evidence: string[];
};

type ApiResult<T> = T & {
  success: boolean;
  error?: string;
};

type Step =
  | "welcome"
  | "evidence"
  | "recall"
  | "feedback"
  | "insights"
  | "ask"
  | "finish";

const stepLabels: Record<Step, string> = {
  welcome: "Start",
  evidence: "Evidence",
  recall: "Recall",
  feedback: "Feedback",
  insights: "Patterns",
  ask: "Ask",
  finish: "Done"
};

const steps: Step[] = ["welcome", "evidence", "recall", "feedback", "insights", "ask", "finish"];
const visibleSteps: Step[] = ["evidence", "recall", "feedback", "insights", "ask", "finish"];
const feedbackLabels = ["Regret", "Fine", "Funny", "Worth it"];
const apiBaseUrl = process.env.NEXT_PUBLIC_BLACKOUT_API_BASE_URL || "http://127.0.0.1:5000";

const categoryIcon: Record<string, ReactNode> = {
  purchase: <ShoppingCart size={13} />,
  message: <MessageSquare size={13} />,
  note: <StickyNote size={13} />,
  commit: <GitCommit size={13} />,
  plan: <CalendarClock size={13} />,
  subscription: <RefreshCw size={13} />,
  other: <Circle size={13} />
};

function feedbackSuffix(label: string) {
  return label.replace(/\s+/g, "");
}

function apiUrl(path: string) {
  if (/^https?:\/\//.test(path)) {
    return path;
  }
  return `${apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

async function postApi<T>(path: string, body?: unknown): Promise<ApiResult<T>> {
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const responseText = await response.text();
  let result: Record<string, unknown> = {};
  if (responseText) {
    try {
      const parsed: unknown = JSON.parse(responseText);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        result = parsed as Record<string, unknown>;
      }
    } catch {
      result = {};
    }
  }
  if (!response.ok) {
    const error =
      "error" in result && typeof result.error === "string"
        ? result.error
        : `BlackOut API returned ${response.status}.`;
    return { success: false, ...result, error } as ApiResult<T>;
  }
  return result as ApiResult<T>;
}

export default function Home() {
  const [step, setStep] = useState<Step>("welcome");
  const [recall, setRecall] = useState<Recall | null>(null);
  const [prompts, setPrompts] = useState<string[]>([]);
  const [evidence, setEvidence] = useState("");
  const [feedbackIndex, setFeedbackIndex] = useState(0);
  const [question, setQuestion] = useState("What did I buy after midnight?");
  const [answer, setAnswer] = useState<{ answer: string; evidence: string[] } | null>(null);
  const [status, setStatus] = useState("");
  const [statusTone, setStatusTone] = useState<"info" | "error">("info");
  const [busy, setBusy] = useState(false);
  const [forgetConfirmed, setForgetConfirmed] = useState(false);
  const [forgetArmed, setForgetArmed] = useState(false);

  const currentDecision = recall?.timeline[feedbackIndex] ?? null;
  const hasInsights = Boolean(recall?.pattern_insights.length);
  const progressIndex = steps.indexOf(step);

  const visibleProgress = useMemo(
    () =>
      visibleSteps.map((item) => {
        const itemIndex = steps.indexOf(item);
        return {
          item,
          state: step === item ? "active" : progressIndex > itemIndex ? "done" : "todo"
        };
      }),
    [step, progressIndex]
  );

  async function runAction<T>(label: string, action: () => Promise<ApiResult<T>>) {
    setBusy(true);
    setStatusTone("info");
    setStatus(label);
    try {
      const result = await action();
      if (!result.success) {
        setStatusTone("error");
        setStatus(result.error || "Something did not work.");
        return null;
      }
      setStatus("");
      return result;
    } catch {
      setStatusTone("error");
      setStatus("Could not reach the BlackOut API. Start `python3 server.py` first.");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function loadDemo() {
    const result = await runAction<{ recall: Recall; prompts: string[] }>(
      "Loading the prepared Late-Night Windows...",
      () => postApi("/api/load-demo")
    );
    if (!result) return;
    setRecall(result.recall);
    setPrompts(result.prompts || []);
    setFeedbackIndex(0);
    setStep("recall");
  }

  async function rememberEvidence() {
    if (!evidence.trim()) {
      setStatusTone("error");
      setStatus("Paste some Evidence first.");
      return;
    }
    const result = await runAction<{ recall: Recall; prompts: string[] }>(
      "Remembering Evidence...",
      () => postApi("/api/remember", { evidence })
    );
    if (!result) return;
    setRecall(result.recall);
    setPrompts(result.prompts || []);
    setFeedbackIndex(0);
    setStep("recall");
  }

  async function applyFeedback(label: string) {
    if (!currentDecision || !recall) return;
    const decision = currentDecision;
    const window = recall.window;
    updateDecisionFeedback(decision.evidence_excerpt, decision.summary, label);
    setStatusTone("info");
    setStatus(`Saving ${label} feedback...`);
    try {
      const result = await postApi<{ decision: Decision }>("/api/feedback", {
        window,
        decision,
        label
      });
      if (!result.success) {
        setStatusTone("error");
        setStatus(result.error || "Feedback was not saved.");
        return;
      }
      setStatus("");
    } catch {
      setStatusTone("error");
      setStatus("Feedback is shown locally, but the API save did not finish.");
    }
  }

  function updateDecisionFeedback(evidenceExcerpt: string, summary: string, label: string) {
    setRecall((current) => {
      if (!current) return current;
      return {
        ...current,
        timeline: current.timeline.map((decision) =>
          decision.evidence_excerpt === evidenceExcerpt
            ? { ...decision, feedback_label: label }
            : decision
        ),
        pattern_insights: current.pattern_insights.map((insight) => ({
          ...insight,
          status:
            insight.current_decision_excerpt === evidenceExcerpt && label === "Regret"
              ? "confirmed regret"
              : insight.status,
          related_prior_decisions: insight.related_prior_decisions.map((decision) =>
            decision.summary === summary
              ? { ...decision, feedback_label: label }
              : decision
          )
        }))
      };
    });
  }

  function nextFeedback() {
    if (!recall) return;
    const next = feedbackIndex + 1;
    if (next < recall.timeline.length) {
      setFeedbackIndex(next);
      return;
    }
    setStep(hasInsights ? "insights" : "ask");
  }

  async function askMemory(prompt?: string) {
    const text = (prompt || question).trim();
    if (!text) {
      setStatusTone("error");
      setStatus("Ask a question first.");
      return;
    }
    setQuestion(text);
    const result = await runAction<{ answer: string; evidence: string[] }>(
      "Asking remembered Evidence...",
      () => postApi("/api/ask", { question: text })
    );
    if (!result) return;
    setAnswer({ answer: result.answer, evidence: result.evidence || [] });
  }

  async function forgetWindow() {
    if (!recall) return;
    const result = await runAction<{ recall: Recall; forgotten: boolean }>(
      "Forgetting this Late-Night Window...",
      () => postApi("/api/forget", { memory_key: recall.window.memory_key })
    );
    if (!result) return;
    setRecall(result.recall);
    setForgetConfirmed(true);
    setForgetArmed(false);
  }

  async function resetApp() {
    await runAction("Resetting memory...", () => postApi("/api/reset"));
    setStep("welcome");
    setRecall(null);
    setPrompts([]);
    setEvidence("");
    setFeedbackIndex(0);
    setQuestion("What did I buy after midnight?");
    setAnswer(null);
    setForgetConfirmed(false);
    setForgetArmed(false);
  }

  return (
    <main className="app">
      <aside className="rail" aria-label="BlackOut navigation">
        <div className="rail-top">
          <span className="brand">
            <span className="brand-mark" aria-hidden="true">
              <Moon size={17} />
            </span>
            BlackOut
          </span>
          <p className="rail-tag">morning-after recall</p>
          <ThemeToggle />
        </div>
        <ol className="steps" aria-label="Progress">
          {visibleProgress.map(({ item, state }) => (
            <li className="step" key={item} data-state={state} aria-current={state === "active" ? "step" : undefined}>
              <span className="step__num" aria-hidden="true">
                {state === "done" ? <Check size={13} /> : steps.indexOf(item)}
              </span>
              <span className="step__label">{stepLabels[item]}</span>
            </li>
          ))}
        </ol>
      </aside>

      <section className="workspace">
        <div className="workspace__inner">
          {status ? (
            <div className="status" role="status" aria-live="polite" data-tone={statusTone}>
              {busy ? <span className="status__spinner" aria-hidden="true" /> : null}
              <span>{status}</span>
            </div>
          ) : null}

          {step === "welcome" ? (
            <WelcomeScreen busy={busy} onLoadDemo={loadDemo} onPaste={() => setStep("evidence")} />
          ) : null}

          {step === "evidence" ? (
            <EvidenceScreen
              busy={busy}
              evidence={evidence}
              onBack={() => setStep("welcome")}
              onChange={setEvidence}
              onRemember={rememberEvidence}
            />
          ) : null}

          {step === "recall" && recall ? (
            <RecallScreen
              recall={recall}
              onBack={() => setStep("evidence")}
              onContinue={() =>
                setStep(recall.timeline.length ? "feedback" : hasInsights ? "insights" : "ask")
              }
            />
          ) : null}

          {step === "feedback" && recall && currentDecision ? (
            <FeedbackScreen
              busy={busy}
              decision={currentDecision}
              index={feedbackIndex}
              total={recall.timeline.length}
              onApply={applyFeedback}
              onNext={nextFeedback}
            />
          ) : null}

          {step === "insights" && recall ? (
            <InsightsScreen
              insights={recall.pattern_insights}
              onBack={() => setStep("feedback")}
              onContinue={() => setStep("ask")}
            />
          ) : null}

          {step === "ask" ? (
            <AskScreen
              answer={answer}
              busy={busy}
              prompts={prompts}
              question={question}
              onAsk={askMemory}
              onBack={() => setStep(hasInsights ? "insights" : "feedback")}
              onChange={setQuestion}
              onContinue={() => setStep("finish")}
            />
          ) : null}

          {step === "finish" && recall ? (
            <FinishScreen
              busy={busy}
              armed={forgetArmed}
              forgotten={forgetConfirmed}
              onArm={() => setForgetArmed(true)}
              onCancelArm={() => setForgetArmed(false)}
              onConfirmForget={forgetWindow}
              onReset={resetApp}
            />
          ) : null}
        </div>
      </section>
    </main>
  );
}

function ThemeToggle() {
  const toggle = () => {
    if (typeof document === "undefined") return;
    const root = document.documentElement;
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try {
      localStorage.setItem("blackout-theme", next);
    } catch {
      /* ignore */
    }
  };
  return (
    <button type="button" className="theme-toggle" onClick={toggle} aria-label="Switch color theme">
      <span className="theme-toggle__track" aria-hidden="true">
        <span className="theme-toggle__knob" />
      </span>
      <span className="theme-toggle__label">Theme</span>
    </button>
  );
}

function WelcomeScreen({
  busy,
  onLoadDemo,
  onPaste
}: {
  busy: boolean;
  onLoadDemo: () => void;
  onPaste: () => void;
}) {
  return (
    <div className="screen welcome">
      <div className="intro">
        <span className="intro__eyebrow">Morning-after recall</span>
        <h1 className="hero-title">Late-night decisions, morning clarity.</h1>
        <p className="lead">
          Reconstruct the previous Late-Night Window, recognize repeat patterns, and repair
          memory with feedback or forgetting. No accounts, no judgments &mdash; just your own
          evidence, on your own screen.
        </p>
        <div className="hero-actions">
          <button className="btn btn-primary" aria-busy={busy} disabled={busy} onClick={onLoadDemo}>
            <Sparkles size={17} />
            {busy ? "Loading" : "Load demo"}
          </button>
          <button className="btn btn-secondary" onClick={onPaste}>
            <NotebookText size={17} />
            Paste Evidence
          </button>
        </div>
      </div>
      <aside className="preview-card" aria-label="What a Late-Night Window looks like">
        <div className="preview-card__head">
          <Clock3 size={15} />
          00:00 &mdash; 05:00
        </div>
        <div className="preview-item">
          <span className="preview-item__dot" />
          <div className="preview-item__body">
            <span className="preview-item__title">Bought an espresso machine</span>
            <span className="preview-item__meta">purchase &middot; $249</span>
          </div>
        </div>
        <div className="preview-item">
          <span className="preview-item__dot" />
          <div className="preview-item__body">
            <span className="preview-item__title">Promised slides by breakfast</span>
            <span className="preview-item__meta">message &middot; emotionally loaded</span>
          </div>
        </div>
        <div className="preview-item">
          <span className="preview-item__dot" />
          <div className="preview-item__body">
            <span className="preview-item__title">Started a new branch</span>
            <span className="preview-item__meta">commit &middot; repeat pattern</span>
          </div>
        </div>
      </aside>
    </div>
  );
}

function EvidenceScreen({
  busy,
  evidence,
  onBack,
  onChange,
  onRemember
}: {
  busy: boolean;
  evidence: string;
  onBack: () => void;
  onChange: (value: string) => void;
  onRemember: () => void;
}) {
  return (
    <div className="screen narrow">
      <ScreenHeader
        icon={<NotebookText size={18} />}
        title="Add Evidence"
        description="Paste copied receipts, chats, notes, calendar text, commits, book notes, or OCR text from the previous Late-Night Window."
      />
      <div className="field">
        <textarea
          className="textarea"
          value={evidence}
          onChange={(event) => onChange(event.target.value)}
          aria-label="Evidence text"
          placeholder={"Late-Night Window: Last night\nOrder placed: 2:13 AM\nMerchant: ShopSwift\nItem: novelty keyboard\nTotal: $129\n\nPriya, 1:05 AM\nI can totally redesign the slides by breakfast.\n\nStarts 4:00 AM\nTitle: Review launch deck"}
        />
        <p className="hint">
          Each excerpt needs a recognizable time (like <code>2:13 AM</code> or <code>03:12</code>) to
          become a Decision. Unrecognized text returns an empty timeline instead of an invented one.
        </p>
      </div>
      <div className="btn-row">
        <button className="btn btn-secondary" onClick={onBack}>
          <ArrowLeft size={17} />
          Back
        </button>
        <button className="btn btn-primary" aria-busy={busy} disabled={busy} onClick={onRemember}>
          <Brain size={17} />
          Remember
        </button>
      </div>
    </div>
  );
}

function RecallScreen({
  recall,
  onBack,
  onContinue
}: {
  recall: Recall;
  onBack: () => void;
  onContinue: () => void;
}) {
  return (
    <div className="screen">
      <ScreenHeader
        icon={<Eye size={18} />}
        title="Your Night"
        description={`${recall.window.starts_at} to ${recall.window.ends_at}`}
        meta={recall.window.label}
      />
      <div className="timeline">
        {recall.timeline.length ? (
          recall.timeline.map((decision) => (
            <DecisionCard decision={decision} key={decision.evidence_excerpt} />
          ))
        ) : (
          <EmptyState
            title="No Decisions found in this Late-Night Window."
            hint="Try pasting evidence that includes a recognizable time, like a receipt timestamp or a chat export."
          />
        )}
      </div>
      {recall.raw_evidence.length ? (
        <details className="raw-evidence">
          <summary>
            <ChevronDown size={16} />
            <span className="raw-evidence__hint">{recall.raw_evidence.length} excerpt(s)</span>
          </summary>
          <div className="raw-evidence__body">
            {recall.raw_evidence.map((line, index) => (
              <p className="evidence-excerpt" key={index}>
                {line}
              </p>
            ))}
          </div>
        </details>
      ) : null}
      <div className="btn-row">
        <button className="btn btn-secondary" onClick={onBack}>
          <ArrowLeft size={17} />
          Back
        </button>
        <button className="btn btn-primary" onClick={onContinue}>
          Continue
          <ArrowRight size={17} />
        </button>
      </div>
    </div>
  );
}

function FeedbackScreen({
  busy,
  decision,
  index,
  total,
  onApply,
  onNext
}: {
  busy: boolean;
  decision: Decision;
  index: number;
  total: number;
  onApply: (label: string) => void;
  onNext: () => void;
}) {
  const progress = Math.min(100, Math.round(((index + 1) / total) * 100));
  return (
    <div className="screen narrow">
      <ScreenHeader
        icon={<CircleAlert size={18} />}
        title="How does this one land?"
        description="Mark each Decision in your own words. Regret teaches memory to treat similar choices more seriously; the rest say a strange-looking Decision was harmless, amusing, or actually a good call."
      />
      <DecisionCard decision={decision} featured />
      <div className="feedback-progress" aria-label={`Decision ${index + 1} of ${total}`}>
        <span>
          Decision {index + 1} of {total}
        </span>
        <span className="feedback-progress__bar">
          <span className="feedback-progress__fill" style={{ width: `${progress}%` }} />
        </span>
      </div>
      <div className="feedback-grid" role="group" aria-label="Feedback labels">
        {feedbackLabels.map((label) => {
          const applied = decision.feedback_label === label;
          return (
            <button
              className={`btn feedback-btn feedback-btn--${feedbackSuffix(label)}`}
              data-applied={applied || undefined}
              disabled={busy}
              key={label}
              onClick={() => onApply(label)}
              aria-pressed={applied}
            >
              <span className="feedback-btn__dot" aria-hidden="true" />
              {label}
            </button>
          );
        })}
      </div>
      <button className="btn btn-primary btn-full" onClick={onNext} style={{ marginTop: 16 }}>
        {decision.feedback_label ? "Next Decision" : "Skip"}
        <ArrowRight size={17} />
      </button>
    </div>
  );
}

function InsightsScreen({
  insights,
  onBack,
  onContinue
}: {
  insights: PatternInsight[];
  onBack: () => void;
  onContinue: () => void;
}) {
  return (
    <div className="screen">
      <ScreenHeader
        icon={<Sparkles size={18} />}
        title="Patterns"
        description="Decisions that resemble previous Late-Night Windows. These are neutral signals, not judgments &mdash; repeat behavior is often the useful part of memory."
      />
      <div className="insight-list">
        {insights.length ? (
          insights.map((insight) => (
            <article className="insight-card" key={insight.current_decision_excerpt}>
              <div className="insight-card__head">
                <span className={`chip ${insight.status === "confirmed regret" ? "risk risk--confirmed" : "risk"}`}>
                  {insight.status}
                </span>
              </div>
              <h3 className="insight-card__title">{insight.summary}</h3>
              <ol className="prior-list">
                {insight.related_prior_decisions.map((decision) => (
                  <li className="prior-item" key={`${decision.timestamp}-${decision.summary}`}>
                    <span className="prior-item__time">{decision.timestamp}</span>
                    <span>{decision.summary}</span>
                    {decision.amount ? <span className="prior-item__amount">{decision.amount}</span> : null}
                  </li>
                ))}
              </ol>
            </article>
          ))
        ) : (
          <EmptyState
            title="No repeat patterns found yet."
            hint="Patterns appear when a current Decision resembles one from a prior Late-Night Window &mdash; same category, same person or vendor."
          />
        )}
      </div>
      <div className="btn-row">
        <button className="btn btn-secondary" onClick={onBack}>
          <ArrowLeft size={17} />
          Back
        </button>
        <button className="btn btn-primary" onClick={onContinue}>
          Ask Memory
          <ArrowRight size={17} />
        </button>
      </div>
    </div>
  );
}

function AskScreen({
  answer,
  busy,
  prompts,
  question,
  onAsk,
  onBack,
  onChange,
  onContinue
}: {
  answer: { answer: string; evidence: string[] } | null;
  busy: boolean;
  prompts: string[];
  question: string;
  onAsk: (prompt?: string) => void;
  onBack: () => void;
  onChange: (value: string) => void;
  onContinue: () => void;
}) {
  return (
    <div className="screen narrow">
      <ScreenHeader
        icon={<MessageCircleQuestion size={18} />}
        title="Ask Your Memory"
        description="A focused follow-up after Morning-After Recall. Answers stay grounded in remembered Decisions and Evidence Excerpts."
      />
      {prompts.length ? (
        <div className="prompts">
          {prompts.map((prompt) => (
            <button className="prompt-btn" key={prompt} onClick={() => onAsk(prompt)}>
              {prompt}
            </button>
          ))}
        </div>
      ) : null}
      <div className="ask-row">
        <input
          className="input"
          value={question}
          onChange={(event) => onChange(event.target.value)}
          aria-label="Ask a question"
          placeholder="What did I do last night?"
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              onAsk();
            }
          }}
        />
        <button className="btn btn-primary" aria-busy={busy} disabled={busy} onClick={() => onAsk()}>
          Ask
          <ArrowRight size={17} />
        </button>
      </div>
      {answer ? (
        <article className="answer-card">
          <p className="answer-card__text">{answer.answer}</p>
          {answer.evidence.length ? (
            <div className="answer-card__evidence">
              <span className="answer-card__label">Grounding evidence</span>
              {answer.evidence.map((item) => (
                <p className="evidence-excerpt" key={item}>
                  {item}
                </p>
              ))}
            </div>
          ) : null}
        </article>
      ) : null}
      <div className="btn-row">
        <button className="btn btn-secondary" onClick={onBack}>
          <ArrowLeft size={17} />
          Back
        </button>
        <button className="btn btn-primary" onClick={onContinue}>
          Done
          <ArrowRight size={17} />
        </button>
      </div>
    </div>
  );
}

function FinishScreen({
  busy,
  armed,
  forgotten,
  onArm,
  onCancelArm,
  onConfirmForget,
  onReset
}: {
  busy: boolean;
  armed: boolean;
  forgotten: boolean;
  onArm: () => void;
  onCancelArm: () => void;
  onConfirmForget: () => void;
  onReset: () => void;
}) {
  return (
    <div className="screen narrow finish">
      <div className="finish-card">
        <h2 className="finish-card__title">
          {forgotten ? "Window forgotten" : "You're caught up"}
        </h2>
        <p className="finish-card__body">
          {forgotten
            ? "This Late-Night Window is out of Morning-After Recall and Ask Your Memory."
            : "Your night has been reviewed. You can keep this memory, or forget the whole window."}
        </p>
        {forgotten ? null : armed ? (
          <div className="confirm-inline" role="alertdialog" aria-label="Confirm forget">
            <span>Forget the entire Late-Night Window? This cannot be undone.</span>
            <span className="confirm-inline__actions">
              <button
                className="btn confirm-btn confirm-btn--yes"
                disabled={busy}
                onClick={onConfirmForget}
              >
                Forget
              </button>
              <button className="btn confirm-btn confirm-btn--no" onClick={onCancelArm}>
                Keep
              </button>
            </span>
          </div>
        ) : (
          <button className="btn btn-danger" disabled={busy} onClick={onArm}>
            <Trash2 size={17} />
            Forget this window
          </button>
        )}
        <button className="btn btn-ghost" onClick={onReset}>
          <RotateCcw size={16} />
          Start over
        </button>
      </div>
    </div>
  );
}

function ScreenHeader({
  description,
  icon,
  title,
  meta
}: {
  description: string;
  icon: ReactNode;
  title: string;
  meta?: string;
}) {
  return (
    <header className="screen-head">
      <span className="screen-head__icon" aria-hidden="true">
        {icon}
      </span>
      <h2 className="screen-head__title">{title}</h2>
      {meta ? <span className="screen-head__meta">{meta}</span> : null}
      <p className="screen-head__desc">{description}</p>
    </header>
  );
}

function DecisionCard({ decision, featured = false }: { decision: Decision; featured?: boolean }) {
  const icon = categoryIcon[decision.category] ?? categoryIcon.other;
  return (
    <article className={`decision-card ${featured ? "decision-card--featured" : ""}`}>
      <div className="decision-top">
        <div className="decision-top__left">
          <span className="timestamp">{decision.timestamp}</span>
          <span className={`chip cat--${decision.category}`}>
            {icon}
            {decision.category}
          </span>
          <span className="source">{decision.source_type}</span>
        </div>
        <div className="decision-top__right">
          {decision.amount ? <span className="amount">{decision.amount}</span> : null}
          {decision.feedback_label ? (
            <span className={`chip fb--${feedbackSuffix(decision.feedback_label)}`}>
              {decision.feedback_label}
            </span>
          ) : null}
        </div>
      </div>
      <h3 className="decision-summary">{decision.summary}</h3>
      {decision.regret_signals.length ? (
        <div className="signal-row">
          {decision.regret_signals.map((signal) => (
            <span className="signal" key={signal}>
              {signal}
            </span>
          ))}
        </div>
      ) : null}
      <p className="evidence-excerpt">{decision.evidence_excerpt}</p>
    </article>
  );
}

function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <p className="empty-state">
      <strong>{title}</strong>
      {hint ? <span>{hint}</span> : null}
    </p>
  );
}