import { ArrowUpRight, Scale, ThumbsUp } from "lucide-react";
import type { Contradiction, Finding, Source } from "../types";
import { CredibilityBar, ProviderChip, StatusBadge } from "./ui";

export function SourceCard({ source, n, highlighted }: { source: Source; n: number; highlighted?: boolean }) {
  return (
    <a
      id={`source-${n}`}
      href={source.url}
      target="_blank"
      rel="noreferrer"
      className={`group block rounded-xl border p-4 transition ${
        highlighted
          ? "border-brand-400/60 bg-brand-500/10 shadow-[0_0_0_4px_rgba(129,140,248,0.12)]"
          : "border-white/[0.06] bg-white/[0.02] hover:border-white/15 hover:bg-white/[0.04]"
      }`}
    >
      <div className="flex items-start gap-3">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-brand-500/20 text-xs font-semibold text-brand-200">
          {n}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h4 className="line-clamp-2 text-sm font-medium text-slate-100">{source.title}</h4>
            <ArrowUpRight className="h-4 w-4 shrink-0 text-slate-600 transition group-hover:text-brand-300" />
          </div>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">{source.snippet}</p>
          <div className="mt-2.5 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <ProviderChip provider={source.provider} />
              <span className="truncate text-[11px] text-slate-600">{new URL(source.url).hostname}</span>
            </div>
            <CredibilityBar value={source.credibility} />
          </div>
        </div>
      </div>
    </a>
  );
}

export function ContradictionCard({ c, sources, onCite }: { c: Contradiction; sources: Source[]; onCite: (n: number) => void }) {
  const side = (label: "a" | "b", text: string, n: number) => {
    const winner = c.likely_correct === label;
    return (
      <button
        type="button"
        onClick={() => onCite(n)}
        className={`flex-1 rounded-xl border p-3.5 text-left transition hover:bg-white/[0.04] ${
          winner ? "border-emerald-400/30 bg-emerald-500/[0.06]" : "border-white/[0.06] bg-white/[0.02]"
        }`}
      >
        <div className="mb-1.5 flex items-center justify-between gap-2">
          <span className="truncate text-[11px] font-medium uppercase tracking-wider text-slate-500">
            [{n}] {sources[n - 1]?.title ?? "Source"}
          </span>
          {winner && (
            <span className="chip shrink-0 bg-emerald-500/15 text-emerald-300">
              <ThumbsUp className="h-3 w-3" /> more likely
            </span>
          )}
        </div>
        <p className="text-sm leading-6 text-slate-200">“{text}”</p>
      </button>
    );
  };
  return (
    <div className="rounded-2xl border border-rose-400/20 bg-rose-500/[0.04] p-4">
      <div className="mb-3 flex items-center gap-2">
        <Scale className="h-4 w-4 text-rose-300" />
        <h4 className="font-display text-sm font-semibold capitalize text-rose-100">{c.topic}</h4>
      </div>
      <div className="flex flex-col gap-2 md:flex-row md:items-stretch">
        {side("a", c.claim_a, c.source_a)}
        <span className="self-center font-display text-xs font-bold text-rose-300/70">VS</span>
        {side("b", c.claim_b, c.source_b)}
      </div>
      <p className="mt-3 text-xs text-slate-400">{c.explanation}</p>
    </div>
  );
}

export function FindingRow({ f, onCite }: { f: Finding; onCite: (n: number) => void }) {
  return (
    <li className="flex flex-col gap-2 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 sm:flex-row sm:items-start sm:justify-between">
      <p className="text-sm leading-6 text-slate-200">{f.statement}</p>
      <div className="flex shrink-0 items-center gap-2">
        <div className="flex gap-1">
          {f.sources.map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => onCite(n)}
              className="h-5 min-w-5 rounded-md bg-brand-500/20 px-1.5 text-[11px] font-semibold text-brand-200 hover:bg-brand-500/40"
            >
              {n}
            </button>
          ))}
        </div>
        <StatusBadge status={f.status} />
      </div>
    </li>
  );
}
