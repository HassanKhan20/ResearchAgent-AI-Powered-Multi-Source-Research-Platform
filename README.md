<div align="center">

<img src="docs/assets/banner.svg" alt="ResearchAgent: ask anything, get a cited, cross-checked report" width="100%" />

<br />

![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=white&labelColor=0b0f1c)
![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?style=for-the-badge&logo=typescript&logoColor=white&labelColor=0b0f1c)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=0b0f1c)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white&labelColor=0b0f1c)
![LangGraph](https://img.shields.io/badge/LangGraph-agents-818cf8?style=for-the-badge&labelColor=0b0f1c)
<br />
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white&labelColor=0b0f1c)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white&labelColor=0b0f1c)
![Tailwind](https://img.shields.io/badge/Tailwind-3-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white&labelColor=0b0f1c)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED?style=for-the-badge&logo=docker&logoColor=white&labelColor=0b0f1c)
![Claude](https://img.shields.io/badge/Claude-Opus_5.5-D97757?style=for-the-badge&labelColor=0b0f1c)

**Ask a question in plain English. Agents search multiple sources, cross-check every claim,<br/>flag contradictions, and hand back a report where every sentence is cited.**

[Features](#-features) · [Screenshots](#-screenshots) · [How it works](#-how-it-works) · [Quick start](#-quick-start) · [API](#-rest-api) · [Project layout](#-project-layout)

</div>

---

## ✨ Features

<table>
<tr>
<td width="33%" valign="top">

### 🧭 Multi-agent pipeline
A **LangGraph** state machine plans sub-queries, searches, extracts claims, verifies them and writes the report. It loops back to refine the search when too few sources turn up.

</td>
<td width="33%" valign="top">

### 🔍 Multi-source search
Queries **Wikipedia**, **arXiv** and the **web** (Tavily) in parallel, de-duplicates by URL, and ranks each source by **relevance × credibility**.

</td>
<td width="33%" valign="top">

### ⚖️ Contradiction detection
Claims are matched across sources. Conflicting figures (unit-aware) and opposite conclusions are **flagged side by side**, and the more credible source is marked as more likely correct.

</td>
</tr>
<tr>
<td valign="top">

### 📎 Cited to the sentence
Every statement carries `[n]` citations. In the UI they are hover-able chips that jump to the source card.

</td>
<td valign="top">

### 📡 Live progress over SSE
Each agent step streams to the browser as it happens. Events are stored in **Redis**, so a client that reconnects picks up where it left off.

</td>
<td valign="top">

### 🛡️ Works with or without an LLM
With `ANTHROPIC_API_KEY` set, every agent uses **Claude** structured outputs. Without a key, the same agents fall back to deterministic heuristics, so the app always runs.

</td>
</tr>
</table>

---

## 📸 Screenshots

<div align="center">

**Ask a question**

<img src="docs/assets/home.png" alt="Home screen with question box and example questions" width="90%" />

<br/><br/>

**Watch the agents work (live timeline over SSE)**

<img src="docs/assets/timeline.png" alt="Live agent timeline showing plan and search complete" width="90%" />

<br/><br/>

**Get a cited report with trust score, flagged contradictions and ranked sources**

<img src="docs/assets/report.png" alt="Report view with confidence ring, contradiction cards and source list" width="90%" />

<br/><br/>

<table>
<tr>
<td align="center" width="40%"><b>Mobile</b><br/><br/><img src="docs/assets/mobile.png" alt="Mobile report view" width="280" /></td>
<td valign="top">

**Claim status legend**

| Badge | Meaning |
|:--|:--|
| 🟢 **Corroborated** | Two or more independent sources agree |
| 🟡 **Single source** | Only one source states it. Treat with caution |
| 🔴 **Contested** | Sources disagree. Both sides are shown |

**Trust score** (0–100)

```text
trust = 100 × ( 0.6 × agreement      ← weighted claim statuses
              + 0.3 × credibility    ← mean source credibility
              + 0.1 × diversity )    ← distinct source types / 3
```

<sub>Screenshots were taken in offline demo mode (`OFFLINE_MODE=true`), which uses a built-in corpus that deliberately contains conflicting claims.</sub>

</td>
</tr>
</table>

</div>

---

## 🧠 How it works

### System architecture

```mermaid
flowchart TB
    subgraph Client["🖥️ React + TypeScript (Vite · Tailwind)"]
        direction LR
        UI["Ask box"] --> TL["Live agent timeline"] --> RV["Cited report<br/>contradictions · sources"]
    end

    subgraph API["⚡ FastAPI"]
        direction LR
        R1["POST /api/research"] --> BG["Background runner"]
        R2["GET /events · SSE"]
        R3["GET /api/research/:id"]
    end

    subgraph Agents["🧭 LangGraph agents"]
        direction LR
        P["Plan"] --> S["Search"] --> E["Extract"] --> V["Cross-check"] --> W["Write"]
    end

    subgraph Data["💾 Data"]
        direction LR
        PG[("🐘 PostgreSQL<br/>users · sessions · jobs · reports")]
        RD[("🟥 Redis<br/>sessions · event log · search cache")]
    end

    subgraph Ext["🌐 External"]
        direction LR
        SRC["Wikipedia · arXiv · Web"]
        LLM["🤖 Claude"]
    end

    Client -- "question" --> R1
    R2 -. "SSE stream" .-> TL
    R3 -- "report JSON" --> RV
    BG --> Agents
    S <--> SRC
    Agents <-- "structured outputs" --> LLM
    Agents -- "step events · cache" --> RD
    R2 -- "read events" --> RD
    W -- "save report" --> PG
    R3 --> PG
```

### The agent graph

```mermaid
stateDiagram-v2
    direction LR
    [*] --> plan
    plan --> search: sub-queries
    search --> refine: fewer than 3 sources
    refine --> search: broadened queries
    search --> extract: enough sources
    extract --> verify: atomic claims
    verify --> write: findings + contradictions
    write --> [*]: cited report

    note right of verify
        Groups claims into findings,
        labels them corroborated,
        single-source or contested,
        pairs up contradictions
    end note
```

| Agent | Job | With Claude | Without a key (fallback) |
|:--|:--|:--|:--|
| 🗺️ **Plan** | Turn the question into focused search queries | `PlanOut` schema | Keyword extraction + query variants |
| 🌐 **Search** | Fan out to every provider in parallel, de-dupe, rank | — | Cached per provider/query in Redis |
| 🔁 **Refine** | Broaden queries if results are thin (max 1 round) | — | Conditional LangGraph edge |
| ✂️ **Extract** | Pull atomic, checkable claims from each source | `ClaimsOut` schema | Sentence ranking by question overlap |
| ⚖️ **Verify** | Cluster agreeing claims, detect conflicts, score trust | `VerifyOut` schema | Jaccard similarity + unit-aware numeric and negation checks |
| ✍️ **Write** | Compose the Markdown report with `[n]` citations | `ReportOut` schema | Templated report from verified findings |

### Request lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as React app
    participant API as FastAPI
    participant RQ as Redis
    participant AG as LangGraph agents
    participant DB as PostgreSQL

    U->>FE: Ask a question
    FE->>API: POST /api/sessions (first visit)
    API->>DB: create user + session
    API->>RQ: cache session token
    FE->>API: POST /api/research
    API->>DB: insert job (queued)
    API-->>FE: 202 Accepted {job id}
    FE->>API: GET /events (EventSource)
    API->>AG: run graph in background
    loop each agent step
        AG->>RQ: append step event
        API->>RQ: read new events
        API-->>FE: SSE: step started / completed
    end
    AG->>DB: save report (sources, claims, contradictions)
    API-->>FE: SSE: done {report id}
    FE->>API: GET /api/research/:id
    API-->>FE: report JSON → rendered with citations
```

---

## 🚀 Quick start

### Option A: Docker (full stack)

```bash
# optional: enable Claude and web search
export ANTHROPIC_API_KEY=sk-ant-...
export TAVILY_API_KEY=tvly-...

docker compose up --build
```

| Service | URL |
|:--|:--|
| 🖥️ Frontend | http://localhost:3000 |
| ⚡ API + Swagger docs | http://localhost:8000/docs |
| 🐘 PostgreSQL | `localhost:5432` (research / research) |
| 🟥 Redis | `localhost:6379` |

### Option B: Local dev (no Docker needed)

Without `DATABASE_URL` and `REDIS_URL`, the backend falls back to **SQLite** and an **in-memory cache**.

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                # edit keys / URLs as needed
uvicorn app.main:app --reload --port 8000

# frontend (new terminal)
cd frontend
npm install
npm run dev                                         # http://localhost:5173 (proxies /api → :8000)
```

> 💡 **Demo mode:** `OFFLINE_MODE=true STEP_DELAY=1.5 uvicorn app.main:app` runs the whole pipeline against a built-in corpus with deliberate contradictions, pausing between steps so you can watch the timeline. No network or API keys needed.

### ⚙️ Configuration

| Variable | Default | Purpose |
|:--|:--|:--|
| `DATABASE_URL` | `sqlite+aiosqlite:///./research.db` | Postgres: `postgresql+asyncpg://user:pass@host/db` |
| `REDIS_URL` | *(empty → in-memory)* | Sessions, SSE event log, search cache |
| `ANTHROPIC_API_KEY` | *(empty → heuristics)* | Enables Claude for every agent |
| `LLM_MODEL` | `claude-opus-5-5` | Claude model ID |
| `LLM_EFFORT` | `medium` | `low` · `medium` · `high` · `xhigh` · `max` |
| `TAVILY_API_KEY` | *(empty)* | Adds general web search |
| `OFFLINE_MODE` | `false` | Use the built-in fixture corpus |
| `STEP_DELAY` | `0` | Seconds to pause after each agent step |
| `MAX_SOURCES` | `12` | Sources kept per report |

> **Answer quality:** the heuristic fallback is there so the app always runs. For real research, set `ANTHROPIC_API_KEY` (and ideally `TAVILY_API_KEY`). Claude then handles planning, claim extraction, fact-checking and writing.

---

## 📡 REST API

All endpoints except session creation and health need `Authorization: Bearer <token>`. EventSource can't set headers, so it passes the token as `?token=`.

| Method | Endpoint | Description |
|:--:|:--|:--|
| `POST` | `/api/sessions` | Create an anonymous session → `{ token, user }` |
| `GET` | `/api/sessions/me` | Current user |
| `POST` | `/api/research` | Start a job `{ question }` → `202 { id, status }` |
| `GET` | `/api/research` | Your recent jobs with title, trust score and contradiction count |
| `GET` | `/api/research/{id}` | Job + full report |
| `GET` | `/api/research/{id}/events` | **SSE** stream: `step` · `status` · `done` · `error` |
| `DELETE` | `/api/research/{id}` | Delete a job and its report |
| `GET` | `/api/reports/{id}` | A report by ID |
| `GET` | `/api/health` | DB, cache and LLM status |

<details>
<summary><b>Example: SSE event stream</b></summary>

```text
event: step
data: {"type":"step","node":"plan","status":"completed","data":{"sub_queries":["great wall china visible space", "..."]}}

event: step
data: {"type":"step","node":"search","status":"completed","data":{"count":4,"providers":["arxiv","web","wikipedia"]}}

event: step
data: {"type":"step","node":"verify","status":"completed","data":{"corroborated":1,"single_source":3,"contradictions":2,"confidence":60.6}}

event: done
data: {"type":"done","report_id":"9f2c..."}
```

</details>

<details>
<summary><b>Example: a flagged contradiction</b></summary>

```json
{
  "topic": "great wall kilometres",
  "claim_a": "A 2012 archaeological survey ... measured the total length of all wall sections at 21,196 kilometres.",
  "source_a": 1,
  "claim_b": "Contrary to popular belief, the Great Wall is about 8,850 kilometres long.",
  "source_b": 4,
  "explanation": "Sources report different figures for the same point.",
  "likely_correct": "a"
}
```

</details>

---

## 🗂️ Project layout

```text
.
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── graph.py        # LangGraph pipeline: plan → search → (refine) → extract → verify → write
│   │   │   ├── llm.py          # Claude structured-output client (returns None → heuristic fallback)
│   │   │   ├── heuristics.py   # claim extraction, unit-aware contradiction detection, trust score
│   │   │   └── state.py        # typed graph state + Claim / Finding / Contradiction models
│   │   ├── search/
│   │   │   ├── providers.py    # Wikipedia, arXiv, Tavily
│   │   │   ├── hub.py          # parallel fan-out, Redis caching, URL de-dupe
│   │   │   └── offline.py      # deterministic corpus for tests and demos
│   │   ├── routers/            # sessions + research/report endpoints (incl. SSE)
│   │   ├── cache.py            # Redis / in-memory cache + event log
│   │   ├── models.py           # SQLAlchemy: users, sessions, research_jobs, reports
│   │   ├── services.py         # background job runner
│   │   └── main.py             # FastAPI app, CORS, health
│   ├── tests/                  # pytest: heuristics, graph, API lifecycle, auth isolation
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/         # AgentTimeline, ReportBody, Panels, Layout, ui primitives
│   │   ├── pages/              # Home, Research
│   │   ├── api.ts              # typed client + EventSource
│   │   └── types.ts
│   ├── nginx.conf              # SPA + unbuffered SSE proxy
│   └── Dockerfile
├── docker-compose.yml          # postgres · redis · backend · frontend
└── .github/workflows/ci.yml    # pytest + frontend build
```

---

## 🧪 Tests

```bash
cd backend && pytest -q
```

```text
..........                                                    [100%]
10 passed
```

The suite runs the **whole agent graph and API end to end** against the offline corpus. It covers contradiction flagging, the refine loop, the job lifecycle over SSE, and per-user isolation, all without network access or API keys.

---

<div align="center">

Built with React · TypeScript · FastAPI · LangGraph · PostgreSQL · Redis

</div>
