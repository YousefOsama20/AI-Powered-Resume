# AI-Powered Resume ATS — Jobright Platform

> **Version:** 3.1 · **Stack:** FastAPI · PostgreSQL · ChromaDB · sentence-transformers · spaCy · LLM (OpenAI-compatible) · Next.js 16 / React 19 / Tailwind 4

## Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [Architecture Overview](#2-architecture-overview)
3. [Repository Layout](#3-repository-layout)
4. [Global Talent Pool + Direct-Apply Model](#4-global-talent-pool--direct-apply-model)
5. [Frontend (Jobright UI)](#5-frontend-jobright-ui)
6. [Environment Variables & API Keys](#6-environment-variables--api-keys)
7. [API Endpoints (real prefixes)](#7-api-endpoints-real-prefixes)
8. [How to Run Locally](#8-how-to-run-locally)
9. [End-to-End User Flows](#9-end-to-end-user-flows)
10. [Hybrid Matching Engine](#10-hybrid-matching-engine)
11. [SkillNormalizer (canonical skills)](#11-skillnormalizer-canonical-skills)
12. [Scripts & Maintenance](#12-scripts--maintenance)

---

## 1. What Is This Project?

**AI-Powered Resume / Jobright** connects **Candidates (CUSTOMER)** with **Companies (COMPANY)** through an AI-driven ATS with two discovery directions:

- **Company → Candidates:** a JD is matched against the entire global CV pool (`POST /nlp/match`), then the company contacts candidates into a Kanban pipeline.
- **Candidate → Jobs:** a CV is reverse-matched against all public JDs (`GET /nlp/recommend-jobs`), with honest skill-overlap UI (green = in your CV, red = missing).

Core capabilities:

- 🔐 **Role-based JWT auth** (`CUSTOMER`, `COMPANY`, `ADMIN`) — `src/helpers/security.py` (bcrypt + jose), `src/routes/deps.py`.
- 🗄️ **PostgreSQL (SQLAlchemy):** Users, `CustomerProfile`, `CandidateDocument` (multi-CV, `is_primary`), `CompanyProfile` (website/industry/location), `JobDescription` ownership + `job_type_id`/`job_function_id`, `JobApplication` pipeline, `JobType`/`JobFunction` taxonomy with M2M candidate preferences.
- 📤 **CV ingestion:** PDF/DOCX upload → section segmentation → chunking → skill + experience extraction → embeddings → ChromaDB (`POST /data/upload` → `POST /nlp/index`).
- 🧠 **Vector engine:** local `sentence-transformers` embeddings; ChromaDB collections `candidates` (chunks) + `jds` (one doc per JD, company-scoped id `{company_id}::{jd_name}`).
- 🔍 **Hybrid matching:** 30% semantic + 30% keyword (75/25 essential/elective + strict mode) + 20% experience + 10% job-type + 10% job-function. Both directions return `matched/missing_essential/elective`.
- 🧹 **SkillNormalizer:** canonical aliases + plural handling + fuzzy fallback so `rest apis == rest api`, `http protocols == http`, `linux commands == linux`, `problem-solving skills == problem solving` (`src/controllers/SkillNormalizer.py`).
- 🖥️ **Next.js frontend:** split-screen auth, candidate onboarding with **unlimited multi-select Job Functions** (`MultiSelectDropdown.tsx`), dashboards, job detail with personalized overlap, company JD creator + AI matcher + Kanban ATS.
- 🛠️ **Ops:** `GET /nlp/debug-match` (raw vs canonical skill audit), `python -m scripts.reindex_skills` (metadata-only re-canonicalization), `DELETE /dev/reset-everything` (dev wipe + reseed).

---

## 2. Architecture Overview

Hybrid database: **PostgreSQL** is the source of truth (ownership, pipeline, preferences); **ChromaDB** holds NLP artifacts (chunks, skills metadata, vectors).

```mermaid
flowchart TD
    FE[Next.js Frontend :3000] --> API[FastAPI :8000]
    API --> Auth[JWT deps: get_current_customer / get_current_company]
    Auth --> Routes[Routers: auth / profile / data / nlp / ats / dev / welcome]
    Routes --> Ctrl[Controllers: Match / JD / SkillNormalizer / LLMExtraction / Extraction / Experience / Embedding / VectorDB / Process / Data / Project]
    Ctrl --> PG[(PostgreSQL)]
    Ctrl --> Chroma[(ChromaDB: candidates + jds)]
    Ctrl --> FS[assets/files: original CVs]
```

CORS allows `http://localhost:3000` and `http://127.0.0.1:3000` (`src/main.py`).

---

## 3. Repository Layout

```text
AI_powered_resume/
├── README.md                      # this handbook
├── endpoint_action.md             # full API reference with JSON in/out
├── projectmemory.md               # build history + decisions + roadmap
├── seed_candidates.py / seed_companies.py
├── docker-compose.yml / docker/
├── src/
│   ├── main.py                    # FastAPI app + CORS + router mounts (NO /api prefix)
│   ├── .env / .env.example
│   ├── requirements.txt
│   ├── routes/                    # auth, profile, data, nlp, ats, dev, base, deps + schemes/
│   ├── controllers/               # business logic (see src/controllers/README.md)
│   │   ├── SkillNormalizer.py     # canonical skill layer
│   │   ├── MatchController.py     # match_candidates + recommend_jobs
│   │   ├── JDController.py        # Chroma JD store (company-scoped ids)
│   │   └── ...
│   ├── models/
│   │   ├── sql_models.py          # User/Profile/Document/JD/Application/Taxonomy
│   │   └── enums/                 # taxonomy, sections, experience regex, responses
│   ├── stores/db + llm/           # PG session, LLM providers, prompt templates
│   ├── helpers/                   # config (Settings) + security (JWT/bcrypt)
│   ├── scripts/                   # seed_taxonomy, reindex_skills, simulate_pipeline...
│   └── assets/files + vectordb + taxonomy/
└── frontend/
    ├── src/app/
    │   ├── login / register
    │   ├── candidate/onboarding | dashboard | jobs/[jd_id] | profile | applications | resumes
    │   └── company/onboarding | dashboard | jobs | jobs/new | jobs/[jd_id]/edit+matches | ats/[jd_id] | profile
    ├── src/components/            # SplitScreenLayout, DashboardLayout, MatchRing, MultiSelectDropdown
    └── src/lib/axios.ts           # JWT interceptor
```

---

## 4. Global Talent Pool + Direct-Apply Model

1. Candidate registers → picks **unlimited Job Functions + Job Types** + location → uploads CV → CV indexed once.
2. Company creates JD (skills auto-extracted via LLM → heuristic fallback, canonicalized, embedded, stored in Chroma + ownership row in Postgres).
3. Discovery A (company): `POST /nlp/match {jd_id|jd_name|job_description, top_k}` ranks **every** candidate (orphan vectors without `CustomerProfile` skipped), contact via `POST /ats/company/contact` → `CONTACTED`.
4. Discovery B (candidate): `GET /nlp/recommend-jobs?top_k=10` reverse-ranks public JDs for the primary CV; candidate applies via `POST /ats/jobs/{jd_id}/apply` → `APPLIED`.
5. Shared Kanban pipeline: `APPLIED → CONTACTED → CONSIDERED → INTERVIEWING → OFFER_SENT → HIRED`, plus `REJECTED`/`CANCELLED`.

---

## 5. Frontend (Jobright UI)

- **Auth:** `/login`, `/register` — role cards (Candidate/Company), auto-login + redirect to the right onboarding.
- **Candidate:** `/candidate/onboarding` (step 1: `MultiSelectDropdown` for Job Functions — unlimited — + chip-grid Job Types + location; step 2: CV upload; step 3: scanning animation) → `/candidate/dashboard` (Recommended feed, true keyword Skill ring + tooltip with essential/elective/semantic, green `You have` / red `Missing` chips, amber `Low skill overlap` banner under 30%) → `/candidate/jobs/[jd_id]` (Essential vs Nice-to-have with ✓/✗ personalization) → `/candidate/profile` (same multi-select), `/candidate/applications`, `/candidate/resumes`.
- **Company:** `/company/onboarding`, `/company/dashboard`, `/company/jobs`, `/company/jobs/new` (title + description + type/function + location + public flag), `/company/jobs/[jd_id]/matches` (global AI sourcing + Contact button), `/company/ats/[jd_id]` (drag-and-drop Kanban), `/company/profile`.
- **Shared:** `SplitScreenLayout`, `DashboardLayout`, `MatchRing`, `MultiSelectDropdown` (count badge, Clear all, outside-click close).

---

## 6. Environment Variables & API Keys

Config lives in `src/.env` (see `src/.env.example`); schema in `src/helpers/config.py:Settings`.

```dotenv
APP_NAME="ai-power-resume"
APP_VERSION="3.1"

# PostgreSQL
DATABASE_URL="postgresql://user:pass@localhost:5432/resume"  # sqlite for quick dev

# Security
JWT_SECRET_KEY="YOUR_SUPER_SECRET_KEY"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 days

# Files
FILE_ALLOWED_TYPES=["application/pdf","application/msword","application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
FILE_MAX_SIZE=16
FILE_DEFAULT_CHUNK_SIZE=512000

# ChromaDB + embeddings
VECTOR_DB_PATH="./assets/vectordb"
VECTOR_DB_COLLECTION="resume_chunks"
EMBEDDING_MODEL_NAME="all-MiniLM-L6-v2"
EMBEDDING_BATCH_SIZE=64

# LLM (OpenAI-compatible; empty => heuristic taxonomy fallback)
GENERATION_BACKEND=""
GENERATION_API_KEY=""
GENERATION_API_URL=""
GENERATION_MODEL_ID=""
GENERATION_MAX_TOKENS=500
GENERATION_TEMPERATURE=0.1

# Prompts
PRIMARY_LANG="en"
DEFAULT_LANG="en"
```

Swagger: `http://localhost:8000/docs`. No `/api` prefix — routers mount at `/auth`, `/profile`, `/data`, `/nlp`, `/ats`, `/dev`, `/welcome`.

---

## 7. API Endpoints (real prefixes)

Full JSON contracts live in `endpoint_action.md`.

| Area | Method + Path | Role |
|---|---|---|
| Health | `GET /welcome/` | any |
| Auth | `POST /auth/register`, `POST /auth/login` | any |
| Profile | `GET /profile/customer`, `PUT /profile/customer`, `GET /profile/company`, `PUT /profile/company`, `GET /profile/taxonomy` | customer / company |
| Data | `POST /data/upload`, `POST /data/process` (legacy), `GET /data/download/me`, `GET /data/download/candidate/{id}`, `GET /data/customer/documents`, `DELETE /data/customer/documents/{id}` | customer / company |
| NLP index | `POST /nlp/index`, `GET /nlp/files`, `DELETE /nlp/delete/file`, `DELETE /nlp/delete/customer` | customer |
| NLP JD | `POST /nlp/jd`, `GET /nlp/jd`, `PUT /nlp/jd`, `PUT /nlp/jd/{jd_id}`, `DELETE /nlp/jd/{jd_identifier}` | company |
| NLP match | `POST /nlp/match`, `GET /nlp/recommend-jobs`, `GET /nlp/debug-match` | company / customer |
| ATS candidate | `GET /ats/jobs/public`, `GET /ats/jobs/public/{jd_id}` (+ personalized overlap when authed), `POST /ats/jobs/{jd_id}/apply`, `GET /ats/customer/applications`, `PUT /ats/customer/applications/{id}/accept` | customer |
| ATS company | `POST /ats/company/contact`, `GET /ats/board/{jd_id}`, `PUT /ats/board/{application_id}/move` | company |
| Dev | `DELETE /dev/reset-everything` | none (dev only!) |

---

## 8. How to Run Locally

Prerequisites: Python 3.10+, Node 20+, PostgreSQL (optional — SQLite works for dev), `en_core_web_sm` spaCy model auto-downloads on first run.

```bash
# Backend
source ~/miniconda3/etc/profile.d/conda.sh && conda activate base
pip install -r src/requirements.txt
cp src/.env.example src/.env  # then fill secrets
cd src/models/db_schemes/resume && python -m alembic upgrade head && cd ../../../..
cd src && python main.py  # :8000

# Seed taxonomy (job types + functions)
cd src && python -m scripts.seed_taxonomy

# Frontend
cd frontend && npm install && npm run dev  # :3000
```

Maintenance:

```bash
cd src
python -m scripts.reindex_skills --dry-run   # preview canonicalization
python -m scripts.reindex_skills             # metadata-only fix, no re-embed
```

---

## 9. End-to-End User Flows

**Candidate:** register → login → `/candidate/onboarding` (functions/types/location) → upload CV → `POST /data/upload` → `POST /nlp/index` → `/candidate/dashboard` (`GET /nlp/recommend-jobs`) → open job (`GET /ats/jobs/public/{jd_id}` shows ✓/✗) → apply → track in `/candidate/applications` → accept company contacts.

**Company:** register → login → `/company/onboarding` → create JD (`POST /nlp/jd`) → AI matcher (`POST /nlp/match {jd_id}`) → contact (`POST /ats/company/contact`) → Kanban (`GET /ats/board/{jd_id}`, drag to `INTERVIEWING…HIRED`) → download CV once accepted (`GET /data/download/candidate/{id}`).

---

## 10. Hybrid Matching Engine

Both `match_candidates` (company) and `recommend_jobs` (candidate) share one formula (`src/controllers/MatchController.py`):

```text
hybrid = 0.30*semantic + 0.30*keyword + 0.20*experience
       + 0.10*job_type + 0.10*job_function
```

- **Semantic (30%):** cosine similarity of `sentence-transformers` embeddings (JD vs CV-chunk average).
- **Keyword (30%):** essential/elective split; `essential*0.75 + elective*0.25`; **strict mode** — elective ignored when `essential_score < 0.5`; empty-essential JDs score `essential=1.0`.
- **Experience (20%):** `ExperienceController` required-vs-actual with gap reporting.
- **Type/Function (10% each):** exact-or-empty match (`empty == 1.0`); candidate prefs are M2M lists, so multi-select works natively. Location text is display-only (no location score).
- Responses include `match/semantic/keyword/essential/elective/experience/location/job_type/job_function` scores + `matched/missing_essential/elective` + `required_experience/candidate_experience/experience_gap`. Orphan Chroma vectors without PG profiles are skipped and counted (`orphan_skipped`).

---

## 11. SkillNormalizer (canonical skills)

`src/controllers/SkillNormalizer.py` — single source of truth, idempotent, no new dependencies (difflib fuzzy ≥0.88):

- `normalize_skill`: lowercase → `-`/`_`→space → strip quotes/punct → drop trailing `skill(s)` → alias map → singularize last token (`apis→api`).
- Seed aliases: `rest apis→rest api`, `http protocols→http`, `linux commands→linux`, `problem-solving skills→problem solving`, `google cloud platform→gcp`, `amazon web services→aws`, `postgres→postgresql`, `nodejs→node.js`, `k8s→kubernetes`, `ci cd→ci/cd`, …
- `match_skills(candidate, required)`: exact on canonical + fuzzy fallback; returns `(matched, missing, map)`.
- `score_from_matches`: shared 75/25 + strict-mode scorer.
- Applied in: `LLMExtractionController`, `ExtractionController`, `JDController`, `routes/nlp._normalize_classified_skills`, both `MatchController` paths, `routes/ats` personalized overlap, `scripts/reindex_skills`.
- Prompts (`stores/llm/templates/locales/en/skill_extraction.py`) force canonical output for new JDs/CVs.

---

## 12. Scripts & Maintenance

| Script | Purpose |
|---|---|
| `scripts/seed_taxonomy.py` | Seed `JobType` (6) + `JobFunction` (14) |
| `scripts/reindex_skills.py [--dry-run]` | Canonicalize stored Chroma skill metadata (no re-embed) |
| `scripts/simulate_pipeline.py`, `rewrite_matcher.py` | Manual matching experiments |
| `seed_candidates.py`, `seed_companies.py` (repo root) | Demo data |
| `GET /nlp/debug-match?jd_id=&document_id=` | Audit: raw vs canonical skills, matched/missing, keyword/essential/elective |
| `DELETE /dev/reset-everything` | Wipe Chroma + files + PG rows, reseed taxonomy (dev only) |
