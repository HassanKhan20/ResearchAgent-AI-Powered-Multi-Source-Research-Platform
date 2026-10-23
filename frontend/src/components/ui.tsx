import { AlertTriangle, BadgeCheck, CircleDashed } from "lucide-react";
import type { ClaimStatus } from "../types";

export const PROVIDER_STYLES: Record<string, string> = {
  wikipedia: "bg-slate-500/15 text-slate-200 ring-1 ring-slate-400/20",
  arxiv: "bg-rose-500/15 text-rose-200 ring-1 ring-rose-400/20",
  web: "bg-sky-500/15 text-sky-200 ring-1 ring-sky-400/20",
  offline: "bg-violet-500/15 text-violet-200 ring-1 ring-violet-400/20",
};

export function ProviderChip({ provider }: { provider: string }) {
  return <span className={`chip ${PROVIDER_STYLES[provider] ?? PROVIDER_STYLES.web}`}>{provider}</span>;
}

const STATUS: Record<ClaimStatus, { label: string; cls: string; Icon: typeof BadgeCheck }> = {
  corroborated: { label: "Corroborated", cls: "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/25", Icon: BadgeCheck },
  "single-source": { label: "Single source", cls: "bg-amber-500/15 text-amber-200 ring-1 ring-amber-400/25", Icon: CircleDashed },
  contested: { label: "Contested", cls: "bg-rose-500/15 text-rose-300 ring-1 ring-rose-400/25", Icon: AlertTriangle },
};

export function StatusBadge({ status }: { status: ClaimStatus }) {
  const { label, cls, Icon } = STATUS[status];
  return (
    <span className={`chip ${cls}`}>
      <Icon className="h-3.5 w-3.5" />
      {label}
    </span>
  );
}

export function confidenceTone(score: number) {
  if (score >= 75) return { label: "High confidence", color: "#34d399", text: "text-emerald-300" };
  if (score >= 55) return { label: "Moderate confidence", color: "#fbbf24", text: "text-amber-300" };
  return { label: "Low confidence", color: "#fb7185", text: "text-rose-300" };
}

export function ConfidenceRing({ score, size = 132 }: { score: number; size?: number }) {
  const stroke = 10;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const tone = confidenceTone(score);
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="rgba(255,255,255,0.07)" strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={tone.color}
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - score / 100)}
          style={{ transition: "stroke-dashoffset 1s ease-out", filter: `drop-shadow(0 0 8px ${tone.color}55)` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-3xl font-semibold text-white">{Math.round(score)}</span>
        <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500">trust</span>
      </div>
    </div>
  );
}

export function CredibilityBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.85 ? "bg-emerald-400" : value >= 0.7 ? "bg-sky-400" : "bg-amber-400";
  return (
    <div className="flex items-center gap-2" title={`Source credibility ${pct}%`}>
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-white/10">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] tabular-nums text-slate-500">{pct}</span>
    </div>
  );
}
