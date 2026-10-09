# Routes Directory Overview

`routes/` defines every FastAPI endpoint: validate with Pydantic `schemes/`, enforce roles via `deps.py`, delegate to `controllers/`, return JSON. Mounted in `src/main.py` with **no `/api` prefix**: `/welcome`, `/auth`, `/profile`, `/data`, `/nlp`, `/ats`, `/dev`. Full JSON contracts: `endpoint_action.md`.

## Shared

### `deps.py`
- `oauth2_scheme` — `OAuth2PasswordBearer(tokenUrl="api/auth/login")` (Swagger hint).
- `get_current_user` — decode JWT (`JWT_SECRET_KEY`/`JWT_ALGORITHM`), load `User`, 401 otherwise.
- `get_current_customer` — 403 unless `role == CUSTOMER`.
- `get_current_company` — 403 unless `role == COMPANY`.

### `base.py` → `GET /welcome/`
Health check, returns `{app_name, app_version}` from `Settings`.

### `__init__.py`, `schemes/__init__.py`
Package markers. `schemes/` holds `auth.py` (`UserRegisterRequest`, `UserLoginRequest`, `TokenResponse`, `UserResponse`), `data.py` (`ProcessRequest`), `nlp.py` (`NLPIndexRequest`, `NLPMatchRequest`, `NLPJDStoreRequest`, `NLPJDUpdateRequest`, `NLPJDIdUpdateRequest`, `NLPdeleteRequest`), `profile.py` (`CustomerProfileUpdate`, `CompanyProfileUpdate`), `requests.py` (`CreateRequest{customer_id,jd_id}`, `MoveCandidate{stage}`, `UpdateRequestStatus`).

## `auth.py` → prefix `/auth`
- `POST /register` (201) — email-unique check, bcrypt hash, create `User` + `CustomerProfile(name)` or `CompanyProfile(company_name)`. Body: `{name, email, password, role}`.
- `POST /login` — JSON `{email, password}` (not form), verify bcrypt, mint JWT `{sub: user.id, role}` with `ACCESS_TOKEN_EXPIRE_MINUTES`. → `{access_token, role}`.

## `profile.py` → prefix `/profile`
- `GET /taxonomy` (any) — `{job_types[{id,name}], job_functions[{id,name}]}` for onboarding/forms.
- `GET /customer` (CUSTOMER) — `{email, name, phone, location, job_types[], job_functions[]}`.
- `PUT /customer` (CUSTOMER) — `{phone?, location?, job_type_ids[]?, job_function_ids[]?}`; clears + re-links M2M (unlimited multi-select; onboarding sends full arrays).
- `GET /company` / `PUT /company` (COMPANY) — `{email, company_name, description, website, industry, location}`.

## `data.py` → prefix `/data`
- `POST /upload` (CUSTOMER, multipart `file`) — `DataController.validate_uploaded_file` → `ProjectController.get_customer_path` → save → create `CandidateDocument(customer_id, file_name, file_path, vector_id=file_id, is_primary=1-if-first)`.
- `POST /process` (CUSTOMER) — legacy chunk preview via `ProcessController` (sections + chunks, no vector write).
- `GET /download/me` (CUSTOMER) — own CV file stream.
- `GET /download/candidate/{customer_id}` (COMPANY) — stream only with an application at `CONSIDERED+`, else 403.
- `GET /customer/documents` / `DELETE /customer/documents/{document_id}` (CUSTOMER) — list / delete own docs (+ vectors).

## `nlp.py` → prefix `/nlp`
- `GET /files` — indexed `{file_id, customer_id}` combos.
- `POST /index` (CUSTOMER) — the real CV indexer: `ProcessController` chunk → one global LLM CV extraction (canonicalized) ∪ per-chunk taxonomy skills + global safety net → `EmbeddingController` → `VectorDBController.index_chunks(candidates)`. Body: `{file_id, chunk_size?, overlap_size?, collection_name?}`.
- `DELETE /delete/file {file_id}` / `DELETE /delete/customer` (CUSTOMER) — vector deletes.
- `POST /jd` (COMPANY) — `_extract_jd_skills` (LLM classified → canonical → heuristic `extract_classified_skills` fallback) + required-exp + embed → `JDController.store_jd` (`{company_id}::{jd_name}`) + PG ownership row (`is_public, location, job_type_id, job_function_id`).
- `GET /jd` (COMPANY) — own JDs from PG (`jd_id, jd_name, is_public, location, created_at`).
- `PUT /jd` (by `jd_name`, legacy), `PUT /jd/{jd_id}` (by SQL id incl. metadata patch), `DELETE /jd/{jd_identifier}` (id or name; PG + Chroma).
- `POST /match` (COMPANY) — `MatchController.match_candidates(db, jd_id|jd_name|job_description, top_k≤50)`; skips orphan vectors, returns scores + `matched/missing_*` + `orphan_skipped`.
- `GET /recommend-jobs?document_id?&top_k=` (CUSTOMER) — `MatchController.recommend_jobs` (primary doc default); returns per-JD scores + `matched/missing_*` + `candidate_skills` for the dashboard's honest UI.
- `GET /debug-match?jd_id&document_id?` (CUSTOMER, own CV) — raw vs canonical skill audit + `match_map` + keyword/essential/elective scores.

## `ats.py` → prefix `/ats`
Stages: `APPLIED, CONTACTED, CONSIDERED, INTERVIEWING, OFFER_SENT, HIRED, REJECTED, CANCELLED`.
- Candidate: `GET /jobs/public`, `GET /jobs/public/{jd_id}` (public fields + personalized `matched/missing_*` + `candidate_skills` when `Authorization` present; `skills_source` = `stored|heuristic_fallback`), `POST /jobs/{jd_id}/apply` → `APPLIED` (400 if dup), `POST /jobs/{jd_id}/like` / `DELETE /jobs/{jd_id}/like` (idempotent save/unsave), `GET /customer/likes` (enriched + type filters) + `GET /customer/likes/ids` (heart painting), `GET /customer/applications`, `PUT /customer/applications/{id}/accept` (`CONTACTED→CONSIDERED`).
- Company: `POST /company/contact {customer_id, jd_id}` → `CONTACTED`, `GET /board/{jd_id}` (grouped incl. `candidate_email/phone/match_score`), `PUT /board/{application_id}/move {stage}`.

## `dev.py` → prefix `/dev`
- `DELETE /reset-everything` (no auth, **dev only**) — drop Chroma `candidates`+`jds`, rmtree `assets/files`, `TRUNCATE … CASCADE` PG (skip `alembic_version`), reseed taxonomy via `scripts/seed_taxonomy.seed()`.
