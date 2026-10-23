import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Source } from "../types";

// Turn bare "[3]" citations into links so the markdown renderer hands them to <Citation>.
const linkCitations = (md: string) => md.replace(/\[(\d{1,2})\](?!\()/g, "[$1](#cite-$1)");

function Citation({ n, source, onSelect }: { n: number; source?: Source; onSelect: (n: number) => void }) {
  return (
    <span className="group relative inline-block align-baseline">
      <button
        type="button"
        onClick={() => onSelect(n)}
        className="mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-md bg-brand-500/20 px-1.5 text-[11px] font-semibold text-brand-200 ring-1 ring-brand-400/30 transition hover:bg-brand-500/40 hover:text-white"
      >
        {n}
      </button>
      {source && (
        <span className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-64 -translate-x-1/2 rounded-xl border border-white/10 bg-ink-800 p-3 text-left text-xs shadow-2xl group-hover:block">
          <span className="block font-medium text-slate-100">{source.title}</span>
          <span className="mt-1 block text-slate-500">{new URL(source.url).hostname}</span>
        </span>
      )}
    </span>
  );
}

export default function ReportBody({
  markdown,
  sources,
  onCite,
}: {
  markdown: string;
  sources: Source[];
  onCite: (n: number) => void;
}) {
  return (
    <div className="prose-report">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            const m = href?.match(/^#cite-(\d+)$/);
            if (m) {
              const n = Number(m[1]);
              return <Citation n={n} source={sources[n - 1]} onSelect={onCite} />;
            }
            return (
              <a href={href} target="_blank" rel="noreferrer" className="text-brand-300 underline-offset-2 hover:underline">
                {children}
              </a>
            );
          },
        }}
      >
        {linkCitations(markdown)}
      </ReactMarkdown>
    </div>
  );
}
