import { Check, FileSearch, Globe2, ListTree, Loader2, PenLine, RefreshCw, ShieldCheck } from "lucide-react";
import type { NodeName, StepEvent } from "../types";
import { ProviderChip } from "./ui";

const STEPS: { node: NodeName; title: string; blurb: string; Icon: typeof Globe2 }[] = [
  { node: "plan", title: "Plan", blurb: "Break the question into search queries", Icon: ListTree },
  { node: "search", title: "Search", blurb: "Query web, encyclopedia and papers in parallel", Icon: Globe2 },
  { node: "extract", title: "Extract", blurb: "Pull atomic, checkable claims from each source", Icon: FileSearch },
  { node: "verify", title: "Cross-check", blurb: "Match claims across sources and flag conflicts", Icon: ShieldCheck },
  { node: "write", title: "Write", blurb: "Compose a cited report from verified findings", Icon: PenLine },
];

type StepState = "idle" | "active" | "done";

function stepState(node: NodeName, events: StepEvent[]): StepState {
  const mine = events.filter((e) => e.node === node);
  if (mine.some((e) => e.status === "completed")) {
    // Search can run twice when the refine loop kicks in.
    const lastStart = mine.findLastIndex((e) => e.status === "started");
    const lastDone = mine.findLastIndex((e) => e.status === "completed");
    return lastStart > lastDone ? "active" : "done";
  }
  return mine.length ? "active" : "idle";
}

function latest(node: NodeName, events: StepEvent[]) {
  return [...events].reverse().find((e) => e.node === node && e.status === "completed")?.data ?? {};
}

function Detail({ node, events }: { node: NodeName; events: StepEvent[] }) {
  const d = latest(node, events) as Record<string, any>;
  if (node === "plan" && d.sub_queries)
    return (
      <div className="mt-2 flex flex-wrap gap-1.5">
        {(d.sub_queries as string[]).map((q) => (
          <span key={q} className="chip bg-white/5 text-slate-300 ring-1 ring-white/10">
            {q}
          </span>
        ))}
      </div>
    );
  if (node === "search" && d.count !== undefined)
    return (
      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-slate-400">
        <span className="font-medium text-slate-200">{d.count} sources</span> from
        {(d.providers as string[]).map((p) => (
          <ProviderChip key={p} provider={p} />
        ))}
      </div>
    );
  if (node === "extract" && d.count !== undefined)
    return <p className="mt-1 text-xs text-slate-400"><span className="font-medium text-slate-200">{d.count}</span> claims extracted</p>;
  if (node === "verify" && d.confidence !== undefined)
    return (
      <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
        <span className="chip bg-emerald-500/15 text-emerald-300">{d.corroborated} corroborated</span>
        <span className="chip bg-amber-500/15 text-amber-200">{d.single_source} single-source</span>
        <span className="chip bg-rose-500/15 text-rose-300">{d.contradictions} contradictions</span>
      </div>
    );
  return null;
}

export default function AgentTimeline({ events, failed }: { events: StepEvent[]; failed?: boolean }) {
  const refined = events.some((e) => e.node === "refine");
  return (
    <ol className="glass relative p-5 sm:p-6">
      {STEPS.map(({ node, title, blurb, Icon }, i) => {
        const state = stepState(node, events);
        return (
          <li key={node} className="relative flex gap-4 pb-6 last:pb-0">
            {i < STEPS.length - 1 && (
              <span
                className={`absolute left-[19px] top-10 h-[calc(100%-2.5rem)] w-px ${
                  state === "done" ? "bg-gradient-to-b from-brand-400/70 to-brand-400/20" : "bg-white/10"
                }`}
              />
            )}
            <span
              className={`relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ring-1 transition ${
                state === "done"
                  ? "bg-brand-500/20 text-brand-300 ring-brand-400/40"
                  : state === "active"
                    ? "bg-brand-500/30 text-white ring-brand-300/60 shadow-[0_0_24px_rgba(129,140,248,0.45)]"
                    : "bg-white/[0.03] text-slate-600 ring-white/10"
              }`}
            >
              {state === "done" ? (
                <Check className="h-5 w-5" />
              ) : state === "active" && !failed ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Icon className="h-5 w-5" />
              )}
            </span>
            <div className="min-w-0 flex-1 pt-1">
              <div className="flex items-center gap-2">
                <h3 className={`font-display font-semibold ${state === "idle" ? "text-slate-500" : "text-white"}`}>{title}</h3>
                {node === "search" && refined && (
                  <span className="chip bg-cyan-500/15 text-cyan-200">
                    <RefreshCw className="h-3 w-3" /> refined
                  </span>
                )}
              </div>
              <p className="text-sm text-slate-500">{blurb}</p>
              {state === "active" && !failed && <div className="shimmer mt-2 h-1.5 w-40 rounded-full bg-white/5" />}
              <Detail node={node} events={events} />
            </div>
          </li>
        );
      })}
    </ol>
  );
}
