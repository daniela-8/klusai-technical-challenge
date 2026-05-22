# KlusAI — Competitor Intelligence PoC

A recruitment agency intelligence platform that automatically monitors competitor job boards, infers the likely hiring company behind each anonymized posting, scores targets by outreach priority, and generates one-page briefs ready for cold calls.

---

## The Problem

Specialized recruitment agencies in tech and finance spend 15–30 minutes per company manually preparing outreach. A recruiter monitors competitor job boards, reads anonymized postings, guesses which company is hiring, checks their LinkedIn and career page, reads recent news, and writes a brief before picking up the phone. That process is entirely manual and does not scale.

This platform automates every step: scrape → identify → score → brief. The recruiter opens the dashboard, sees a prioritized list of companies worth calling today, and has a ready-made brief for each one.

---

## Quick Start

### Option A — Docker (recommended for evaluators)

```bash
# 1. Clone the repository
git clone <repo-url> && cd KlusAI-TechnicalChallenge

# 2. Create your environment file
cp backend/.env.example backend/.env
# Edit backend/.env and set GEMINI_API_KEY and OPENAI_API_KEY (same key works for both)

# 3. Start both services
docker compose up --build

# 4. Open the app
open http://localhost:3000
```

The backend starts on port 8000, the frontend on port 3000. The frontend waits for the backend health check to pass before starting.

### Option B — Local Development

**Prerequisites:** Python 3.11+, Node.js 20+

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

---

## API Keys and Model Configuration

The system is configured to use the **Google Gemini API** routed through the OpenAI-compatible endpoint. This means the same Gemini API key is used for everything: LLM inference, embeddings, and Google Search Grounding.

```env
# backend/.env — the actual configuration used in this PoC

# Gemini key used for all OpenAI-compatible calls (LLM + embeddings)
OPENAI_API_KEY=your-gemini-key-here
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/

# Model for reasoning (company matching, scoring, brief generation)
OPENAI_MODEL=gemini-3.1-flash-lite

# Model for lightweight tasks
OPENAI_MODEL_MINI=gemini-3.1-flash-lite

# Embedding model
OPENAI_EMBEDDING_MODEL=gemini-embedding-2

# Separate Gemini key for the native google-genai SDK (Google Search Grounding)
GEMINI_API_KEY=your-gemini-key-here

# Optional: Serper supplementary search
SERPER_API_KEY=your-serper-key-here
```

| Key | Purpose | Required? | Where to get it |
|---|---|---|---|
| `OPENAI_API_KEY` (Gemini key) | LLM inference + embeddings via OpenAI-compatible endpoint | **Yes** | [aistudio.google.com](https://aistudio.google.com) — free tier |
| `GEMINI_API_KEY` | Google Search Grounding via native `google-genai` SDK | **Yes** | Same key from AI Studio |
| `SERPER_API_KEY` | Supplementary web search injected into prompts | Optional | [serper.dev](https://serper.dev) — 2,500 searches/month free |

> Both `OPENAI_API_KEY` and `GEMINI_API_KEY` can be set to the same Gemini API key. They serve different SDK paths: one for the OpenAI-compatible HTTP client, one for the native `google-genai` Python SDK.

---

## How to Run a Demo

1. **Reset** — click "Reset All Data" in the header to start fresh.
2. **Scrape** — click "Run Pipeline", select 2–4 competitors, click "Scrape".
3. **Analyze** — from the Jobs tab, select the scraped listings, click "Run AI Analysis".
4. **Review Matches** — open the Matches tab to see identified companies with confidence scores and enrichment data.
5. **Priority Board** — open Priorities to see ranked targets with radar scoring charts.
6. **Generate Briefs** — click "Generate Brief" on any priority company for a one-page outreach brief.

> For a demo, run analysis on 2–4 listings. Each listing requires 2 LLM calls (match + score) with a 5-second rate-limit gap — approximately 60–90 seconds total.

### Resetting for a Clean Demo

The reset button (`/api/pipeline/reset`) deletes all job postings, matches, scores, briefs, and alerts. Competitors are always preserved. After reset:

- Scrape fresh listings — all newly scraped jobs show "Awaiting analysis" (correct and expected).
- Select them individually and run AI analysis.
- ChromaDB embeddings persist across resets intentionally — they accumulate cross-session similarity context. To fully clear them, delete `backend/data/chromadb/`.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Browser (Next.js 15)                          │
│  Dashboard · Jobs · Matches · Priority Board · Briefs · Alerts       │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ HTTP (rewrites /api/* → backend)
┌────────────────────────────▼─────────────────────────────────────────┐
│                   FastAPI Backend (Python 3.11)                       │
│                                                                       │
│  ┌─────────────┐  ┌──────────────────────────────────────────────┐   │
│  │  Scraping   │  │              AI Pipeline                      │   │
│  │  Manager    │  │                                               │   │
│  │             │  │  CompanyMatcher → PriorityScorer → BriefGen  │   │
│  │  4 custom   │  │       │               │                       │   │
│  │  BS4 parsers│  │  Gemini + Google   Gemini LLM                │   │
│  │  + mock     │  │  Search Grounding  (OpenAI-compat endpoint)  │   │
│  │  fallback   │  │       │                                       │   │
│  └──────┬──────┘  │  ChromaDB (gemini-embedding-2 vectors)       │   │
│         │         │  Serper API (supplementary search, optional) │   │
│         │         └───────────────────────────────┬──────────────┘   │
│         │                                         │                   │
│  ┌──────▼─────────────────────────────────────────▼──────────────┐   │
│  │                  SQLite (SQLAlchemy async)                      │   │
│  │  competitor_sources · job_postings · company_matches           │   │
│  │  priority_scores · prospect_briefs · alerts                    │   │
│  └────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Competitor URLs
     │
     ▼
[Scraping Manager]
 httpx fetches listing page
 → extracts job detail URLs from HTML (BeautifulSoup4 + lxml)
 → fetches each detail page (up to 5 per competitor)
 → custom BS4 parser extracts all fields deterministically
 → persists to SQLite (upsert on URL)
 → mock fallback if live scraping is blocked (Robert Walters)
     │
     ▼
[AI Pipeline — per job, sequential with rate-limit spacing]
 1. EmbeddingService: embed job text with gemini-embedding-2
    → store vector in ChromaDB (cosine similarity index)
 2. EmbeddingService: query ChromaDB for 3 most similar past jobs
    → inject as context into the matching prompt
 3. CompanyMatcher: gemini-3.1-flash-lite via google-genai SDK
    → Google Search Grounding: live web search during inference
    → Serper pre-search results injected if key configured
    → returns company name + confidence + 8 signals + enrichment
 4. PriorityScorer: gemini-3.1-flash-lite via OpenAI-compat endpoint
    → 10-signal deterministic scoring + LLM rationale
    → stores PriorityScore in SQLite
     │
     ▼
[Brief Generation — on demand per company]
 BriefGenerator: single gemini-3.1-flash-lite call
 → structured JSON brief with contact strategy
 → stored in SQLite
```

---

## Technology Stack

| Layer | Technology | Why chosen for a PoC |
|---|---|---|
| Backend API | FastAPI | Async-native, auto-generates Swagger docs, minimal boilerplate |
| ORM | SQLAlchemy 2 async | Type-safe, async sessions, clean migration path to PostgreSQL |
| Database | SQLite (aiosqlite) | Zero configuration, file-based, trivial to reset for demos |
| Vector store | ChromaDB | Embeds in-process, no separate service, persistent by default |
| LLM interface | OpenAI Python SDK (compatibility mode) | Routes to Gemini by changing one base URL — no vendor lock-in |
| Primary LLM | `gemini-3.1-flash-lite` | Free tier: 1,500 RPD, 15 RPM; fast; supports Search Grounding |
| Embeddings | `gemini-embedding-2` | Same API key as the LLM; 768-dimensional vectors; ChromaDB handles transparently |
| Web search (primary) | Gemini Google Search Grounding | Agentic live search during inference — model decides what to search |
| Web search (supplementary) | Serper API | Pre-built query injection into prompt; optional enhancement |
| Scraping | httpx + BeautifulSoup4 + lxml | Lightweight, no browser overhead; sufficient for static HTML pages |
| Frontend | Next.js 15 (App Router) | API proxy rewrites for backend, React ecosystem, SSR-optional |
| Styling | Tailwind CSS v4 | Utility-first, consistent dark glassmorphism theme |
| Charts | Recharts | Radar charts for scoring visualization |
| Containerization | Docker + Docker Compose | Single command to reproduce the full environment |

---

## Codebase Structure

```
KlusAI-TechnicalChallenge/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, CORS, lifespan (DB init + seeding)
│   │   ├── core/
│   │   │   ├── __init__.py          # Pydantic Settings — all config from .env
│   │   │   ├── database.py          # SQLAlchemy async engine + session factory
│   │   │   └── logging.py           # structlog structured logging
│   │   ├── models/
│   │   │   └── __init__.py          # ORM: JobPosting, CompanyMatch, PriorityScore, etc.
│   │   ├── api/routes/
│   │   │   ├── pipeline.py          # /scrape, /process, /reset, /status endpoints
│   │   │   ├── companies.py         # /matches, /priorities endpoints
│   │   │   ├── jobs.py              # Job CRUD + manual upload endpoint
│   │   │   ├── briefs.py            # Brief retrieval
│   │   │   ├── dashboard.py         # Aggregate stats
│   │   │   ├── competitors.py       # Competitor management
│   │   │   └── alerts.py            # Alert feed
│   │   ├── scrapers/
│   │   │   ├── html_parsers.py      # 4 competitor-specific BS4 parsers
│   │   │   ├── competitors.py       # httpx scraper classes (listing → detail URLs)
│   │   │   ├── manager.py           # Orchestrates scraping + mock fallback
│   │   │   ├── mock_data.py         # Curated realistic mock jobs per competitor
│   │   │   └── base.py              # ScrapedJob and ScrapeResult dataclasses
│   │   ├── ai/
│   │   │   ├── llm_client.py        # Rate-limited OpenAI-compat + Gemini Search client
│   │   │   ├── company_matcher.py   # LLM-based company identification (8 signals)
│   │   │   ├── priority_scorer.py   # 10-signal weighted priority scoring
│   │   │   ├── brief_generator.py   # One-page prospect brief generation
│   │   │   ├── embeddings.py        # ChromaDB + gemini-embedding-2 service
│   │   │   ├── web_search.py        # Serper API supplementary search
│   │   │   └── pipeline.py          # Orchestrator (match → score → brief)
│   │   └── services/
│   │       └── seeder.py            # Auto-seeds competitor sources on startup
│   ├── html_examples/               # Real captured HTML for parser unit tests
│   ├── test_parsers.py              # Parser unit tests using real HTML snapshots
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx             # Main page: pipeline orchestration, polling, toasts
│       │   └── globals.css          # CSS variables, animations, dark theme
│       ├── components/
│       │   ├── Jobs.tsx             # Job list with selection + analysis trigger
│       │   ├── Matches.tsx          # Company matches with enrichment detail
│       │   ├── Priorities.tsx       # Priority board with radar scoring charts
│       │   ├── Briefs.tsx           # Prospect brief viewer
│       │   ├── Competitors.tsx      # Competitor management
│       │   └── Dashboard.tsx        # Stats overview
│       └── lib/
│           ├── api.ts               # Typed API client (all backend calls)
│           └── types.ts             # Shared TypeScript interfaces
├── docker-compose.yml
└── README.md
```

---

## Where AI Is Used

### 1. Company Matching — `app/ai/company_matcher.py`

**What it does:** For each anonymized job posting, the system infers the likely end-client company behind it.

**How it works:** The matcher uses `gemini-3.1-flash-lite` via the native `google-genai` SDK specifically to enable **Google Search Grounding**: the model performs live web searches autonomously during inference, browsing LinkedIn, career pages, and press releases without predefined query templates. The full job posting, 3 semantically similar past jobs from ChromaDB, and optional Serper results are included in the prompt.

**Output:** Company name, confidence score (0–100), 8 structured signals (career page match, description similarity, location, industry, seniority, hiring activity, tech stack, public news), alternative candidates, and enrichment data (LinkedIn URL, potential hiring contacts, salary competitiveness).

**Model:** `gemini-3.1-flash-lite` via `google-genai` SDK for search-grounded inference.

### 2. Semantic Similarity — `app/ai/embeddings.py` + ChromaDB

**What it does:** Each job posting is embedded and stored in ChromaDB before the LLM call. The 3 most semantically similar past jobs are retrieved and injected into the matching prompt as supporting context.

**How it works:** The embedding model `gemini-embedding-2` converts job title + description into a 768-dimensional dense vector. ChromaDB indexes these vectors with cosine similarity (HNSW index). This creates a cross-session memory: the more jobs are analyzed, the richer the context becomes for future matches.

**Current behavior:** The vector store starts empty and grows as the pipeline runs. It is not pre-populated with a training dataset. Each analysis stores its embedding, so subsequent runs benefit from accumulated prior matches. A production improvement would pre-seed the collection with a labeled dataset.

### 3. Priority Scoring — `app/ai/priority_scorer.py`

**What it does:** Assigns a 0–100 priority score to each matched company, determining which to contact first.

**How it works:** Ten weighted signals are computed deterministically from structured data, then a single `gemini-3.1-flash-lite` call generates a human-readable rationale:

| Signal | Weight | Logic |
|---|---|---|
| Role relevance | 15% | Industry match to FinTech / SaaS / Banking; title seniority |
| Hiring volume | 12% | Number of open roles detected for this company |
| Seniority | 12% | Junior / Mid / Senior / Executive — higher means larger placement fee |
| Urgency | 12% | Urgency language in description (ASAP, immédiat, urgent, etc.) |
| Recency | 10% | Days since posting — penalized linearly, 5 pts/day |
| Company context | 10% | Funding rounds, M&A, expansion, major contracts in text |
| Department activity | 8% | Multiple roles in the same function or sector |
| Company growth | 8% | Growth stage signals (startup, scale-up, Series A–D) |
| Reposting signals | 8% | Language suggesting the role was previously posted |
| Competitor overlap | 5% | How many competitor agencies are sourcing for this company |

**Threshold:** Only companies with a match confidence of at least 50% appear on the Priority Board.

### 4. Brief Generation — `app/ai/brief_generator.py`

**What it does:** Generates a structured one-page prospect brief ready to use before a cold call.

**How it works:** A single `gemini-3.1-flash-lite` call receives all company context (match explanation, job postings, priority score breakdown, enrichment data) and outputs a structured JSON brief covering: company overview, hiring intelligence, why to target now, competitor intelligence context, contact strategy with realistic French contact details, suggested talking points, and recommended next actions.

---

## Scraping Approach and Limitations

### Why Custom HTML Parsers (Not LLM-based or Playwright)

The most pragmatic approach for a PoC demonstrating live scraping — without anti-bot overhead, without black-box LLM parsing, and without complex browser automation — is to study the HTML source of each competitor's job pages and write a targeted parser for each.

Before building the parsers, the structure of each competitor's job detail pages was manually analyzed. Each one uses a different CMS with a different HTML structure:

- **CPA Partners** — Webflow CMS with predictable CSS class-based structure; fully live-scrapable
- **Michael Page** — Drupal CMS; combines visible HTML, a `thunderheadDataLayer` JavaScript object, and LD+JSON structured data; salary extracted from `<div class="job-salary">` in European number format (`€65.000 - €70.000 par an`), normalized to `€65,000 – €70,000/yr`
- **Robert Half** — React SPA; all job data is embedded as JSON inside a `<script>` tag; fully live-scrapable
- **Robert Walters** — AEM CMS; their WAF (Web Application Firewall) consistently returns HTTP 403 Forbidden for all server-side requests; the parser works correctly on saved HTML (verified by unit tests), but live scraping is blocked; this competitor always uses curated mock data, which deliberately showcases the fallback mechanism

The scraping flow for each live competitor:
1. `httpx` fetches the listing page (the configured `careers_url`)
2. BeautifulSoup4 + lxml extracts up to 5 job detail URLs from the listing
3. Each detail page is fetched and passed to the corresponding parser
4. Structured fields are extracted deterministically: title, description, location, sector, salary, URL, posting date

Note: `playwright` appears in `requirements.txt` as an initially considered dependency but is not used in any production scraping code. All scraping is done via `httpx` (plain HTTP) + `BeautifulSoup4`.

### Current Limitations

**Volume cap:** Each scraping run collects up to 5 jobs per competitor. The system scrapes the listing page at a fixed URL and does not paginate across multiple listing pages.

**Layout fragility:** If a competitor redesigns their website, the corresponding parser will break. This is the fundamental trade-off of custom HTML selectors. For production, the recommended alternatives are:
- LLM-based universal extraction (pass raw HTML to the model and ask it to extract fields)
- Playwright or Puppeteer for JavaScript-rendered pages, managed via a service like Browserless or Apify
- A commercial extraction service such as Diffbot or Zyte

**Anti-scraping:** The system uses a realistic browser User-Agent but does not rotate IPs or use proxy networks. Some competitors actively block server-side requests.

**Rate limiting:** The pipeline processes a maximum of 5 jobs per run to stay within the Gemini free tier (15 RPM). A 5-second minimum interval is enforced globally between LLM calls. Running 5 jobs takes approximately 60–90 seconds.

### Web Search: From Serper to Gemini Search Grounding

The initial implementation used Serper API to pre-build search queries and inject results into the LLM prompt. This worked but was constrained: queries were template-based, results were static snapshots at query time, and Serper required a separate API key with its own quota.

The current primary approach uses **Gemini's native Google Search Grounding** via the `google-genai` SDK. This is architecturally superior for a PoC:
- No fixed query templates — the model decides what to search based on what it reads in the job description
- Results are live at inference time, not pre-fetched snapshots
- The model can chain searches autonomously (read a description → search for the company → check their LinkedIn → search for recent funding news)
- Single API key covers everything

Serper is still supported as an optional supplementary mechanism that pre-fetches results and injects them into the prompt alongside the grounding.

---

## What Would Change in Production

**Scraping:** Replace the 4 custom BS4 parsers with a universal LLM-based extraction layer or Playwright-based headless browsing. This removes the fragility of hardcoded selectors and works across any competitor without code changes.

**Vector store pre-seeding:** Build a labeled dataset of historical job postings with known companies and ingest it into ChromaDB on startup. This gives the matching system a meaningful similarity baseline from the first run rather than starting empty.

**LLM rate limits:** Move from the free Gemini tier (15 RPM) to a paid plan to process jobs in parallel. The current sequential processing with mandatory 5-second gaps between calls is a deliberate PoC constraint.

**Scheduling:** Add a background scheduler (APScheduler or Celery) to scrape competitors automatically on a fixed cadence and trigger the pipeline for new jobs only.

**Authentication:** Add user accounts with JWT-based auth. Pipeline state and briefs should be scoped per user or team.

**Database:** Migrate from SQLite to PostgreSQL for production workloads, concurrent writes, and proper indexing.

**Contact enrichment:** Integrate Hunter.io, Apollo, or Clearbit to find verified contact names, email addresses, and LinkedIn profiles rather than generating them heuristically.

**Monitoring:** Structured log shipping (Datadog, Sentry) and pipeline observability metrics (match rate, average confidence, quota consumption).

---

## API Documentation

Interactive API documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Key endpoints:

| Method | Path | Description |
|---|---|---|
| POST | `/api/pipeline/scrape` | Scrape all or selected competitors |
| POST | `/api/pipeline/process` | Run AI matching + scoring on unprocessed jobs |
| GET | `/api/pipeline/status` | Poll background pipeline state |
| POST | `/api/pipeline/reset` | Delete all jobs, matches, scores, briefs, alerts |
| GET | `/api/companies/matches` | List all company matches with enrichment |
| GET | `/api/companies/priorities` | Ranked priority board (≥ 50% confidence) |
| POST | `/api/pipeline/brief` | Generate a prospect brief for a company |
| POST | `/api/pipeline/scrape-url` | Scrape a single job URL directly |
| POST | `/api/jobs` | Upload a job description manually |

---

## Running Tests

```bash
cd backend
source venv/bin/activate
pytest test_parsers.py -v      # Parser unit tests using real HTML snapshots (no API key needed)
pytest tests/ -v               # Full test suite
```

The parser tests use real captured HTML from `backend/html_examples/` and do not require an API key or network access.

---

## Assumptions and Design Decisions

- **Single worker:** The AI pipeline uses a process-level `asyncio.Lock` to prevent concurrent LLM bursts. The backend runs with a single Uvicorn worker; adding multiple workers would require moving the lock to Redis.
- **Confidence threshold:** The Priority Board shows only companies where the best match confidence is ≥ 50%. Below this the match is too speculative to act on.
- **Mock fallback:** When live scraping returns no results, the system falls back to curated mock job data. The data source is always visible — jobs show "Mocked", "Scraped", or "Uploaded" badges. Robert Walters always uses mock data due to WAF blocking.
- **Salary display:** If no salary is found, the UI shows "Salary unavailable" with a red-tinted badge rather than an empty field.
- **ChromaDB persistence:** The vector store persists across resets intentionally. To fully wipe it, delete `backend/data/chromadb/`.
- **Gemini API key dual use:** The same Gemini key works for both `OPENAI_API_KEY` (OpenAI-compatible endpoint) and `GEMINI_API_KEY` (native `google-genai` SDK). They serve different code paths in the backend.
