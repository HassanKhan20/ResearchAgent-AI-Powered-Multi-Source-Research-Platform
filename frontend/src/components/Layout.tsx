import { AlertTriangle, Loader2, Menu, Plus, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "../api";
import type { JobSummary } from "../types";
import { confidenceTone } from "./ui";

function HistoryItem({ job }: { job: JobSummary }) {
  return (
    <NavLink
      to={`/research/${job.id}`}
      className={({ isActive }) =>
        `block rounded-xl px-3 py-2.5 transition ${isActive ? "bg-white/[0.07]" : "hover:bg-white/[0.04]"}`
      }
    >
      <p className="line-clamp-2 text-sm text-slate-200">{job.title ?? job.question}</p>
      <div className="mt-1.5 flex items-center gap-2 text-[11px] text-slate-500">
        {job.status === "completed" && job.confidence !== null ? (
          <span className={confidenceTone(job.confidence).text}>● {Math.round(job.confidence)} trust</span>
        ) : job.status === "failed" ? (
          <span className="text-rose-300">failed</span>
        ) : (
          <span className="flex items-center gap-1 text-brand-300">
            <Loader2 className="h-3 w-3 animate-spin" /> researching
          </span>
        )}
        {job.contradictions > 0 && (
          <span className="flex items-center gap-1 text-rose-300/80">
            <AlertTriangle className="h-3 w-3" /> {job.contradictions}
          </span>
        )}
      </div>
    </NavLink>
  );
}

export default function Layout() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    let alive = true;
    const load = () => api.listResearch().then((j) => alive && setJobs(j)).catch(() => {});
    load();
    const id = setInterval(load, 4000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [location.pathname]);

  useEffect(() => setOpen(false), [location.pathname]);

  const sidebar = (
    <div className="flex h-full flex-col">
      <Link to="/" className="flex items-center gap-2.5 px-2">
        <img src="/logo.svg" alt="" className="h-8 w-8" />
        <span className="font-display text-lg font-semibold text-white">ResearchAgent</span>
      </Link>
      <Link
        to="/"
        className="mt-6 flex items-center justify-center gap-2 rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-medium text-white shadow-lg shadow-brand-500/25 transition hover:bg-brand-400"
      >
        <Plus className="h-4 w-4" /> New research
      </Link>
      <p className="mt-8 px-3 text-[11px] font-medium uppercase tracking-[0.18em] text-slate-600">History</p>
      <nav className="mt-2 flex-1 space-y-1 overflow-y-auto pr-1">
        {jobs.length === 0 && <p className="px-3 text-sm text-slate-600">Your reports will appear here.</p>}
        {jobs.map((j) => (
          <HistoryItem key={j.id} job={j} />
        ))}
      </nav>
      <p className="px-3 pt-4 text-[11px] text-slate-600">LangGraph agents · FastAPI · Postgres · Redis</p>
    </div>
  );

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-72 shrink-0 border-r border-white/[0.06] bg-ink-900/60 p-4 backdrop-blur-xl lg:block">
        {sidebar}
      </aside>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 border-r border-white/10 bg-ink-900 p-4">
            <button onClick={() => setOpen(false)} className="absolute right-3 top-4 text-slate-400" aria-label="Close menu">
              <X className="h-5 w-5" />
            </button>
            {sidebar}
          </aside>
        </div>
      )}

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-white/[0.06] bg-ink-950/80 px-4 py-3 backdrop-blur lg:hidden">
          <button onClick={() => setOpen(true)} aria-label="Open menu" className="text-slate-300">
            <Menu className="h-5 w-5" />
          </button>
          <img src="/logo.svg" alt="" className="h-6 w-6" />
          <span className="font-display font-semibold text-white">ResearchAgent</span>
        </header>
        <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-10 lg:py-12">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
