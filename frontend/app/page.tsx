"use client";

import {
  ArrowLeft,
  ArrowRight,
  Brain,
  Check,
  CircleAlert,
  Clock3,
  Eye,
  MessageCircleQuestion,
  Moon,
  NotebookText,
  RotateCcw,
  Sparkles,
  Trash2
} from "lucide-react";
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
  finish: "Finish"
};

const steps: Step[] = ["welcome", "evidence", "recall", "feedback", "insights", "ask", "finish"];
const feedbackLabels = ["Regret", "Fine", "Funny", "Worth it"];
const apiBaseUrl = process.env.NEXT_PUBLIC_BLACKOUT_API_BASE_URL || "http://127.0.0.1:5000";

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

function categoryTone(category: string) {
  const tones: Record<string, string> = {
    purchase: "tone-gold",
    message: "tone-blue",
    note: "tone-green",
    commit: "tone-violet",
    plan: "tone-pink",
    subscription: "tone-red"
  };
  return tones[category] || "tone-gray";
}

function feedbackTone(label: string | null) {
  const tones: Record<string, string> = {
    Regret: "feedback-regret",
    Fine: "feedback-fine",
    Funny: "feedback-funny",
    "Worth it": "feedback-worth"
  };
  return label ? tones[label] || "feedback-fine" : "";
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
  const [busy, setBusy] = useState(false);
  const [forgetConfirmed, setForgetConfirmed] = useState(false);

  const currentDecision = recall?.timeline[feedbackIndex] ?? null;
  const hasInsights = Boolean(recall?.pattern_insights.length);
  const progressIndex = steps.indexOf(step);

  const visibleSteps = useMemo(
    () => steps.filter((item) => item !== "welcome"),
    []
  );

  async function runAction<T>(label: string, action: () => Promise<ApiResult<T>>) {
    setBusy(true);
    setStatus(label);
    try {
      const result = await action();
      if (!result.success) {
        setStatus(result.error || "Something did not work.");
        return null;
      }
      setStatus("");
      return result;
    } catch {
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
    setStatus(`Saving ${label} feedback...`);
    try {
      const result = await postApi<{ decision: Decision }>("/api/feedback", {
        window,
        decision,
        label
      });
      if (!result.success) {
        setStatus(result.error || "Feedback was not saved.");
        return;
      }
      setStatus("");
    } catch {
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
  }

  return (
    <main className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <section className="product-frame">
        <aside className="side-rail" aria-label="BlackOut progress">
          <div className="brand-lockup">
            <span className="brand-mark">
              <Moon size={18} />
            </span>
            <span>BlackOut</span>
          </div>
          <nav className="step-list">
            {visibleSteps.map((item) => {
              const itemIndex = steps.indexOf(item);
              const isActive = step === item;
              const isDone = progressIndex > itemIndex;
              return (
                <span
                  className={`step-item ${isActive ? "active" : ""} ${isDone ? "done" : ""}`}
                  key={item}
                >
                  <span>{isDone ? <Check size={14} /> : itemIndex}</span>
                  {stepLabels[item]}
                </span>
              );
            })}
          </nav>
        </aside>

        <section className="workspace">
          {status ? <div className="status-line">{status}</div> : null}

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
              onContinue={() => setStep(recall.timeline.length ? "feedback" : hasInsights ? "insights" : "ask")}
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
            <InsightsScreen insights={recall.pattern_insights} onBack={() => setStep("feedback")} onContinue={() => setStep("ask")} />
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
              forgotten={forgetConfirmed}
              onForget={forgetWindow}
              onReset={resetApp}
            />
          ) : null}
        </section>
      </section>
    </main>
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
    <div className="screen welcome-grid">
      <div className="intro-copy">
        <div className="moon-orbit">
          <Moon size={30} />
        </div>
        <h1>Late-night decisions, morning clarity</h1>
        <p>
          Reconstruct the previous Late-Night Window, recognize repeat patterns,
          and repair memory with feedback or forgetting.
        </p>
        <div className="hero-actions">
          <button className="primary-button" disabled={busy} onClick={onLoadDemo}>
            <Sparkles size={18} />
            Load demo
          </button>
          <button className="secondary-button" onClick={onPaste}>
            <NotebookText size={18} />
            Paste Evidence
          </button>
        </div>
      </div>
      <div className="memory-card">
        <div className="memory-card-header">
          <Clock3 size={18} />
          00:00 - 05:00
        </div>
        <DecisionPreview title="Bought an espresso machine" meta="purchase · $249" />
        <DecisionPreview title="Promised slides by breakfast" meta="message · emotionally loaded" />
        <DecisionPreview title="Started a new branch" meta="commit · repeat pattern" />
      </div>
    </div>
  );
}

function DecisionPreview({ title, meta }: { title: string; meta: string }) {
  return (
    <div className="preview-row">
      <span />
      <div>
        <strong>{title}</strong>
        <small>{meta}</small>
      </div>
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
    <div className="screen narrow-screen">
      <ScreenHeader
        icon={<NotebookText size={20} />}
        title="Add Evidence"
        description="Paste receipts, messages, notes, commits, or other traces from the previous Late-Night Window."
      />
      <textarea
        className="evidence-input"
        value={evidence}
        onChange={(event) => onChange(event.target.value)}
        placeholder={"Late-Night Window: Last night\n00:12 - ShopSwift receipt: novelty keyboard, $129.\n01:05 - Text to Priya: \"I can totally redesign the slides by breakfast.\""}
      />
      <div className="button-row">
        <button className="secondary-button" onClick={onBack}>
          <ArrowLeft size={18} />
          Back
        </button>
        <button className="primary-button" disabled={busy} onClick={onRemember}>
          <Brain size={18} />
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
        icon={<Eye size={20} />}
        title="Your Night"
        description={`${recall.window.starts_at} -> ${recall.window.ends_at}`}
      />
      <div className="timeline">
        {recall.timeline.length ? (
          recall.timeline.map((decision) => (
            <DecisionCard decision={decision} key={decision.evidence_excerpt} />
          ))
        ) : (
          <EmptyState text="No Decisions found in this Late-Night Window." />
        )}
      </div>
      <div className="button-row">
        <button className="secondary-button" onClick={onBack}>
          <ArrowLeft size={18} />
          Back
        </button>
        <button className="primary-button" onClick={onContinue}>
          Continue
          <ArrowRight size={18} />
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
  return (
    <div className="screen narrow-screen">
      <ScreenHeader
        icon={<CircleAlert size={20} />}
        title="How does this one land?"
        description={`Decision ${index + 1} of ${total}`}
      />
      <DecisionCard decision={decision} featured />
      <div className="feedback-grid">
        {feedbackLabels.map((label) => (
          <button
            className={`feedback-button ${feedbackTone(label)}`}
            disabled={busy}
            key={label}
            onClick={() => onApply(label)}
          >
            {label}
          </button>
        ))}
      </div>
      <button className="primary-button full-width" onClick={onNext}>
        {decision.feedback_label ? "Next Decision" : "Skip"}
        <ArrowRight size={18} />
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
        icon={<Sparkles size={20} />}
        title="Patterns"
        description="Decisions that resemble previous Late-Night Windows."
      />
      <div className="insight-list">
        {insights.length ? (
          insights.map((insight) => (
            <article className="insight-card" key={insight.current_decision_excerpt}>
              <span className={insight.status === "confirmed regret" ? "risk confirmed" : "risk"}>
                {insight.status}
              </span>
              <h3>{insight.summary}</h3>
              {insight.related_prior_decisions.map((decision) => (
                <p key={`${decision.timestamp}-${decision.summary}`}>
                  {decision.timestamp} - {decision.summary}
                  {decision.amount ? ` (${decision.amount})` : ""}
                </p>
              ))}
            </article>
          ))
        ) : (
          <EmptyState text="No repeat patterns found yet." />
        )}
      </div>
      <div className="button-row">
        <button className="secondary-button" onClick={onBack}>
          <ArrowLeft size={18} />
          Back
        </button>
        <button className="primary-button" onClick={onContinue}>
          Ask Memory
          <ArrowRight size={18} />
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
    <div className="screen narrow-screen">
      <ScreenHeader
        icon={<MessageCircleQuestion size={20} />}
        title="Ask Your Memory"
        description="Ask a focused follow-up after Morning-After Recall."
      />
      <div className="prompt-row">
        {prompts.map((prompt) => (
          <button className="prompt-button" key={prompt} onClick={() => onAsk(prompt)}>
            {prompt}
          </button>
        ))}
      </div>
      <input
        className="question-input"
        value={question}
        onChange={(event) => onChange(event.target.value)}
      />
      <button className="primary-button full-width" disabled={busy} onClick={() => onAsk()}>
        Ask
        <ArrowRight size={18} />
      </button>
      {answer ? (
        <article className="answer-card">
          <strong>{answer.answer}</strong>
          {answer.evidence.map((item) => (
            <code key={item}>{item}</code>
          ))}
        </article>
      ) : null}
      <div className="button-row">
        <button className="secondary-button" onClick={onBack}>
          <ArrowLeft size={18} />
          Back
        </button>
        <button className="primary-button" onClick={onContinue}>
          Done
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}

function FinishScreen({
  busy,
  forgotten,
  onForget,
  onReset
}: {
  busy: boolean;
  forgotten: boolean;
  onForget: () => void;
  onReset: () => void;
}) {
  return (
    <div className="screen narrow-screen finish-screen">
      <ScreenHeader
        icon={<Check size={20} />}
        title={forgotten ? "Window forgotten" : "You're caught up"}
        description={
          forgotten
            ? "This Late-Night Window is out of Morning-After Recall and Ask Your Memory."
            : "Your night has been reviewed. You can keep this memory or forget the whole window."
        }
      />
      <div className="finish-actions">
        <button className="danger-button" disabled={busy || forgotten} onClick={onForget}>
          <Trash2 size={18} />
          Forget this window
        </button>
        <button className="secondary-button" onClick={onReset}>
          <RotateCcw size={18} />
          Start over
        </button>
      </div>
    </div>
  );
}

function ScreenHeader({
  description,
  icon,
  title
}: {
  description: string;
  icon: React.ReactNode;
  title: string;
}) {
  return (
    <header className="screen-header">
      <span>{icon}</span>
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </header>
  );
}

function DecisionCard({ decision, featured = false }: { decision: Decision; featured?: boolean }) {
  return (
    <article className={`decision-card ${featured ? "featured" : ""}`}>
      <div className="decision-topline">
        <div>
          <span className="timestamp">{decision.timestamp}</span>
          <span className={`category ${categoryTone(decision.category)}`}>
            {decision.category}
          </span>
          <span className="source-type">{decision.source_type}</span>
        </div>
        <div>
          {decision.amount ? <span className="amount">{decision.amount}</span> : null}
          {decision.feedback_label ? (
            <span className={`feedback-chip ${feedbackTone(decision.feedback_label)}`}>
              {decision.feedback_label}
            </span>
          ) : null}
        </div>
      </div>
      <h3>{decision.summary}</h3>
      {decision.regret_signals.length ? (
        <div className="signal-row">
          {decision.regret_signals.map((signal) => (
            <span key={signal}>{signal}</span>
          ))}
        </div>
      ) : null}
      <code>{decision.evidence_excerpt}</code>
    </article>
  );
}

function EmptyState({ text }: { text: string }) {
  return <p className="empty-state">{text}</p>;
}
