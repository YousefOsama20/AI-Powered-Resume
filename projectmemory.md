# NextHire AI Copilot - Project Memory & State

Comprehensive tracker for the AI-Powered Resume & ATS Platform (NextHire): architecture, what shipped, key fixes, roadmap.

## 1. Project Overview

AI recruitment platform with two discovery directions:
*   **Candidate Portal:** onboarding with unlimited multi-select Job Functions/Types, CV upload + scan, reverse-matched feed (`GET /nlp/recommend-jobs`) with honest skill overlap (green = in CV, red = missing), job detail with ✓/✗ personalization, profile/applications/resumes pages.
*   **Company Portal:** JD creator (type/function/location/public), global AI sourcing (`POST /nlp/match`), Kanban ATS (`APPLIED→CONTACTED→CONSIDERED→INTERVIEWING→OFFER_SENT→HIRED`, +`REJECTED`/`CANCELLED`), board with email/phone/match score, CV download once accepted.

## 2. Tech Stack Architecture

*   **Frontend:** Next.js 16 (App Router), React 19, Tailwind 4, axios JWT interceptor, Lucide icons. Key components: `SplitScreenLayout`, `DashboardLayout`, `MatchRing`, `MultiSelectDropdown` (unlimited checkbox dropdown, count badge, Clear all).
*   **Backend:** FastAPI, SQLAlchemy, routers `/auth /profile /data /nlp /ats /dev /welcome` (no `/api` prefix), JWT deps (`get_current_customer/company`).
*   **Databases:**
    *   **PostgreSQL:** Users, Customer/Company profiles, CandidateDocument (multi-CV, `is_primary`), JobDescription ownership (`is_public/location/job_type_id/job_function_id`), JobApplication pipeline, JobType/JobFunction + M2M prefs.
    *   **ChromaDB:** `candidates` chunks (`skills, experience_years, file_id, customer_id, section`) + `jds` single-doc per JD (company-scoped `{company_id}::{jd_name}`, `essential_skills/elective_skills/required_experience`).
*   **AI/NLP:** sentence-transformers embeddings, spaCy `en_core_web_sm` taxonomy matcher, LLM extraction (OpenAI-compatible, canonical prompts) with heuristic fallback, shared hybrid scorer `0.30 sem + 0.30 kw + 0.20 exp + 0.10 type + 0.10 func` (+ strict mode; location is display-only), `SkillNormalizer` canonical layer (aliases/plurals/fuzzy ≥0.88).

## 3. Features Implemented & Development History

### Phase 1: Authentication & Layouts (Completed)
*   Split-screen `/login` + `/register` (Candidate vs Company cards), auto-login → role onboarding.
*   axios JWT interceptor; `CORSMiddleware` for `:3000` → `:8000` in `main.py`.

### Phase 2: Candidate Portal (Completed)
*   **Onboarding (`/candidate/onboarding`):** taxonomy fetch, unlimited Job Functions via `MultiSelectDropdown` + chip-grid Job Types + location; CV upload (`POST /data/upload` → `POST /nlp/index`); scanning animation.
*   **Dashboard (`/candidate/dashboard`):** `GET /nlp/recommend-jobs`; Skill ring = true `keyword_score` (tooltip: essential/elective/semantic); `You have`/`Missing` chips from `matched/missing_*`; amber `Low skill overlap` banner when keyword <30.
*   **Job detail (`/candidate/jobs/[jd_id]`):** `GET /ats/jobs/public/{id}` personalized overlap; Essential vs Nice-to-have with ✓/✗; company card; Easy Apply.
*   **Profile (`/candidate/profile`):** same multi-select (loads all `job_functions`, not `[0]`); Applications tracker; Resumes manager.

### Phase 3: Company Portal & ATS (Completed)
*   **JD Creator (`/company/jobs/new`):** fixed payload mismatches; stores skills + embedding + ownership.
*   **ATS Kanban (`/company/ats/[jd_id]`):** HTML5 drag-and-drop; fixed `board.columns→board.board` + `id→application_id`; shows email/phone/match score.
*   **AI Matcher (`/company/jobs/[jd_id]/matches`):** global Chroma search + Contact → pipeline; orphan-vector filtering.

### Phase 3.5: Backend Finalization (Completed — was "upcoming")
*   ✅ `CompanyProfile.website/industry/location` columns + migration `7c4e1a2b3d5f`.
*   ✅ `GET /profile/customer`, `GET /ats/jobs/public/{jd_id}` (SQL + Chroma join,incl. heuristic read-repair + personalized overlap).
*   ✅ `PUT /nlp/jd/{id}` + `DELETE /nlp/jd/{id}` (id or legacy name), `GET /profile/company`, board email/phone.

### Phase 4: Multi-Select Preferences (Completed)
*   Backend already M2M lists; frontend `selectedFunction: string|null` + `<select>` → `selectedFunctions: string[]` + `MultiSelectDropdown` in onboarding + profile; validation + payload `job_function_ids: string[]`; Job Type already multi (unchanged).

### Phase 5: Skill-Match Honesty / 7% Fix (Completed)
*   **New `controllers/SkillNormalizer.py`** + wiring (LLM/taxonomy/JD/nlp/match/ats/reindex); canonical prompts; index union + global safety net (`routes/nlp.py`); `recommend_jobs` returns `matched/missing_*` + `candidate_skills`; `GET /nlp/debug-match` audit; `scripts/reindex_skills.py`; dashboard/detail honest UI. Verified: sample JD `66.7%→100%` essential / `95%` keyword when CV has skills.

## 4. Key Technical Decisions & Bug Fixes

1.  **Next.js App Router strictness:** server `page.tsx` (`await params`) → `client.tsx` primitives.
2.  **ChromaDB ghost data:** match paths verify PG `CustomerProfile` exists; count `orphan_skipped`.
3.  **JD identity:** company-scoped Chroma `{company_id}::{jd_name}` + PG UUID `jd_id` for routing; legacy bare-name fallback.
4.  **Empty-skills read-repair:** `GET /ats/jobs/public/{id}` re-derives essential/elective via heuristic when stored empty (`skills_source` flag).
5.  **Exact-match trap:** fixed by canonicalization (`rest apis→rest api` etc.) + fuzzy ≥0.88 + reindex; display fixed (keyword ring, no forced average, conditional banner).
6.  **No `/api` prefix:** docs previously wrote `/api/auth` etc.; real mounts are `/auth`, `/profile`, `/data`, `/nlp`, `/ats`, `/dev`, `/welcome` — all READMEs + `endpoint_action.md` corrected in v3.1 pass.

## 5. Roadmap / Next

*   Reindex prod vectors once (`python -m scripts.reindex_skills`), ask users with old CVs to re-process.
*   Optional: JD-side alias editor, per-skill weight tuning, semantic skill similarity (embedding threshold) beyond fuzzy, notification emails on `CONTACTED`/`APPLIED`.
*   Docs: this file + `README.md` (v3.1) + `endpoint_action.md` + per-folder READMEs are now the source of truth — update together with code.
