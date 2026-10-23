export type JobStatus = "queued" | "running" | "completed" | "failed";
export type ClaimStatus = "corroborated" | "single-source" | "contested";
export type NodeName = "plan" | "search" | "refine" | "extract" | "verify" | "write";

export interface Source {
  title: string;
  url: string;
  provider: string;
  snippet: string;
  content?: string;
  published?: string | null;
  credibility: number;
  relevance?: number;
}

export interface Finding {
  statement: string;
  sources: number[];
  status: ClaimStatus;
}

export interface Contradiction {
  topic: string;
  claim_a: string;
  source_a: number;
  claim_b: string;
  source_b: number;
  explanation: string;
  likely_correct: "a" | "b" | "unclear";
}

export interface Report {
  id: string;
  job_id: string;
  title: string;
  summary: string;
  markdown: string;
  confidence: number;
  sources: Source[];
  claims: Finding[];
  contradictions: Contradiction[];
  created_at: string;
}

export interface Job {
  id: string;
  question: string;
  status: JobStatus;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface JobSummary extends Job {
  title: string | null;
  confidence: number | null;
  contradictions: number;
}

export interface JobDetail extends Job {
  report: Report | null;
}

export interface StepEvent {
  type: "step";
  node: NodeName;
  status: "started" | "completed";
  data: Record<string, unknown>;
  ts: number;
}

export type StreamEvent =
  | StepEvent
  | { type: "status"; status: JobStatus }
  | { type: "done"; report_id: string }
  | { type: "error"; message: string };
