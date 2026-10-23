import { AlertTriangle, BadgeCheck, FileText, Library, ListChecks, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, streamEvents } from "../api";
import AgentTimeline from "../components/AgentTimeline";
import { ContradictionCard, FindingRow, SourceCard } from "../components/Panels";
import ReportBody from "../components/ReportBody";
import { ConfidenceRing, confidenceTone } from "../components/ui";
import type { JobDetail, StepEvent } from "../types";

type Tab = "report" | "claims" | "sources";

export default function Research() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState<JobDetail | null>(null);
  const [events, setEvents] = useState<StepEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("report");
  const [highlight, setHighlight] = useState<number | null>(null);
  const sourcesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let close: (() => void) | undefined;
    let alive = true;
    setJob(null);
    setEvents([]);
    setError(null);
    setTab("report");

    api
      .getResearch(id)
      .then(async (detail) => {
        if (!alive) return;
        setJob(detail);
        close = await streamEvents(id, (e) => {
          if (e.type === "step") setEvents((prev) => [...prev, e]);
          if (e.type === "done") api.getResearch(id).then((d) => alive && setJob(d));
          if (e.type === "error") setError(e.message);
        });
        if (!alive) close();
      })
      .catch((e) => setError((e as Error).message));
    return () => {
      alive = false;
      close?.();
    };
  }, [id]);

  const report = job?.report ?? null;
  const counts = useMemo(() => {
    const claims = report?.claims ?? [];
    return {
      corroborated: claims.filter((c) => c.status === "corroborated").length,
      single: claims.filter((c) => c.status === "single-source").length,
      contested: claims.filter((c) => c.status === "contested").length,
    };
  }, [report]);

  function cite(n: number) {
    setHighlight(n);
    if (window.innerWidth < 1024) setTab("sources");
    requestAnimationFrame(() => document.getElementById(`source-${n}`)?.scrollIntoView({ behavior: "smooth", block: "center" }));
    window.setTimeout(() => setHighlight(null), 2200);
  }

  async function remove() {
    await api.deleteResearch(id);
    navigate("/");
  }

  if (error && !job) return <p className="text-rose-300">{error}</p>;
  if (!job) return <div className="shimmer h-40 rounded-2xl bg-white/[0.03]" />;

  const failed = job.status === "failed" || Boolean(error);

  return (
    <div className="animate-rise">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-brand-300">Research question</p>
          <h1 className="mt-2 font-display text-2xl font-semibold leading-snug text-white sm:text-3xl">{job.question}</h1>
        </div>
        <button onClick={remove} title="Delete" className="rounded-lg p-2 text-slate-600 transition hover:bg-white/5 hover:text-rose-300">
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      {!report && (
        <div className="mt-8 grid gap-6 lg:grid-cols-[1.1fr_1fr]">
          <AgentTimeline events={events} failed={failed} />
          <div className="glass flex flex-col justify-center p-6">
            {failed ? (
              <>
                <AlertTriangle className="h-6 w-6 text-rose-300" />
                <h2 className="mt-3 font-display text-lg font-semibold text-white">Research failed</h2>
                <p className="mt-1 text-sm text-slate-400">{error ?? job.error}</p>
              </>
            ) : (
              <>
                <h2 className="font-display text-lg font-semibold text-white">Agents at work</h2>
                <p className="mt-1 text-sm text-slate-400">
                  Sources are being gathered and cross-checked. The report appears here when verification finishes.
                </p>
                <div className="mt-6 space-y-3">
                  {[0.9, 0.75, 0.6, 0.8].map((w, i) => (
                    <div key={i} className="shimmer h-3 rounded-full bg-white/[0.04]" style={{ width: `${w * 100}%` }} />
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {report && (
        <>
          <section className="glass mt-8 grid gap-6 p-6 sm:grid-cols-[auto_1fr] sm:items-center">
            <div className="justify-self-center sm:justify-self-auto">
              <ConfidenceRing score={report.confidence} />
            </div>
            <div>
              <p className={`text-sm font-medium ${confidenceTone(report.confidence).text}`}>{confidenceTone(report.confidence).label}</p>
              <div className="mt-2 text-base leading-7 text-slate-200 [&_p]:mb-0">
                <ReportBody markdown={report.summary} sources={report.sources} onCite={cite} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                <span className="chip bg-white/5 text-slate-300 ring-1 ring-white/10">
                  <Library className="h-3.5 w-3.5" /> {report.sources.length} sources
                </span>
                <span className="chip bg-emerald-500/15 text-emerald-300">
                  <BadgeCheck className="h-3.5 w-3.5" /> {counts.corroborated} corroborated
                </span>
                <span className="chip bg-amber-500/15 text-amber-200">{counts.single} single-source</span>
                <span className="chip bg-rose-500/15 text-rose-300">
                  <AlertTriangle className="h-3.5 w-3.5" /> {report.contradictions.length} contradictions
                </span>
              </div>
            </div>
          </section>

          <div className="mt-6 flex gap-1 rounded-xl border border-white/[0.06] bg-white/[0.02] p-1 lg:hidden">
            {(
              [
                ["report", "Report", FileText],
                ["claims", "Claims", ListChecks],
                ["sources", "Sources", Library],
              ] as const
            ).map(([key, label, Icon]) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-sm ${
                  tab === key ? "bg-white/10 text-white" : "text-slate-500"
                }`}
              >
                <Icon className="h-4 w-4" /> {label}
              </button>
            ))}
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
            <div className={`space-y-6 ${tab === "sources" ? "hidden lg:block" : ""}`}>
              {report.contradictions.length > 0 && tab !== "claims" && (
                <section>
                  <h2 className="mb-3 flex items-center gap-2 font-display font-semibold text-white">
                    <AlertTriangle className="h-4 w-4 text-rose-300" /> Contradictions flagged
                  </h2>
                  <div className="space-y-3">
                    {report.contradictions.map((c, i) => (
                      <ContradictionCard key={i} c={c} sources={report.sources} onCite={cite} />
                    ))}
                  </div>
                </section>
              )}

              {tab !== "claims" && (
                <article className="glass p-6 sm:p-8">
                  <ReportBody markdown={report.markdown} sources={report.sources} onCite={cite} />
                </article>
              )}

              <section className={tab === "claims" ? "" : "hidden lg:block"}>
                <h2 className="mb-3 flex items-center gap-2 font-display font-semibold text-white">
                  <ListChecks className="h-4 w-4 text-brand-300" /> Verified claims
                </h2>
                <ul className="space-y-2">
                  {report.claims.map((f, i) => (
                    <FindingRow key={i} f={f} onCite={cite} />
                  ))}
                </ul>
              </section>
            </div>

            <aside ref={sourcesRef} className={`space-y-2.5 lg:sticky lg:top-6 lg:self-start ${tab === "sources" ? "" : "hidden lg:block"}`}>
              <h2 className="mb-1 flex items-center gap-2 font-display font-semibold text-white">
                <Library className="h-4 w-4 text-brand-300" /> Sources
              </h2>
              <div className="space-y-2.5 lg:max-h-[calc(100vh-8rem)] lg:overflow-y-auto lg:pr-1">
                {report.sources.map((s, i) => (
                  <SourceCard key={s.url} source={s} n={i + 1} highlighted={highlight === i + 1} />
                ))}
              </div>
            </aside>
          </div>
        </>
      )}
    </div>
  );
}
