import { ArrowRight, BookOpenCheck, GitCompareArrows, Loader2, Quote, Sparkles } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

const EXAMPLES = [
  "Is the Great Wall of China visible from space?",
  "Does intermittent fasting help with weight loss?",
  "How much of global electricity comes from solar power?",
  "What caused the extinction of the woolly mammoth?",
];

const FEATURES = [
  { Icon: Sparkles, title: "Multi-agent research", text: "A LangGraph pipeline plans, searches, extracts and writes, each step visible live." },
  { Icon: GitCompareArrows, title: "Cross-checked facts", text: "Every claim is matched across sources and labelled corroborated, single-source or contested." },
  { Icon: Quote, title: "Cited to the sentence", text: "Each statement links to the exact source it came from, ranked by credibility." },
];

export default function Home() {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function submit(q = question) {
    if (q.trim().length < 8) {
      setError("Ask a slightly longer question (8+ characters).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const job = await api.startResearch(q.trim());
      navigate(`/research/${job.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl pt-6 sm:pt-14">
      <div className="animate-rise text-center">
        <span className="chip bg-brand-500/15 text-brand-200 ring-1 ring-brand-400/25">
          <BookOpenCheck className="h-3.5 w-3.5" /> Research you can verify
        </span>
        <h1 className="mt-5 font-display text-4xl font-semibold leading-tight text-white sm:text-5xl">
          Ask anything. Get a <span className="gradient-text">cited, cross-checked</span> report.
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-base text-slate-400">
          Agents search the web, Wikipedia and arXiv, compare what each source says, and flag where they disagree.
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="glass mt-10 p-2 shadow-2xl shadow-black/40 focus-within:ring-2 focus-within:ring-brand-400/40"
      >
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={3}
          placeholder="e.g. Is nuclear power safer than wind per unit of energy?"
          className="w-full resize-none bg-transparent px-4 py-3 text-base text-white placeholder:text-slate-600 focus:outline-none"
        />
        <div className="flex items-center justify-between gap-3 px-2 pb-1">
          <span className="text-xs text-slate-600">Enter to research · Shift+Enter for a new line</span>
          <button
            type="submit"
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-medium text-white shadow-lg shadow-brand-500/30 transition hover:bg-brand-400 disabled:opacity-60"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
            Research
          </button>
        </div>
      </form>
      {error && <p className="mt-3 text-center text-sm text-rose-300">{error}</p>}

      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {EXAMPLES.map((q) => (
          <button
            key={q}
            onClick={() => {
              setQuestion(q);
              submit(q);
            }}
            className="rounded-full border border-white/[0.08] bg-white/[0.03] px-3.5 py-1.5 text-sm text-slate-400 transition hover:border-brand-400/40 hover:text-slate-100"
          >
            {q}
          </button>
        ))}
      </div>

      <div className="mt-16 grid gap-4 sm:grid-cols-3">
        {FEATURES.map(({ Icon, title, text }) => (
          <div key={title} className="glass p-5">
            <Icon className="h-5 w-5 text-brand-300" />
            <h3 className="mt-3 font-display font-semibold text-white">{title}</h3>
            <p className="mt-1.5 text-sm leading-6 text-slate-400">{text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
