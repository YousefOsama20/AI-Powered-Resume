# API Endpoint Documentation

Base URL: `http://localhost:8000` · Swagger: `http://localhost:8000/docs`
Auth: `Authorization: Bearer <JWT>` (from `POST /auth/login`).
**No `/api` prefix** — routers mount at `/auth`, `/profile`, `/data`, `/nlp`, `/ats`, `/dev`, `/welcome` (see `src/main.py`).

Conventions: `CUSTOMER` = candidate, `COMPANY` = recruiter. Scores are 0–100. Skill lists are canonical (see `SkillNormalizer`).

---

## 1. Health (`/welcome`)

### `GET /welcome/`
Any. Returns `{app_name, app_version}` from `Settings`.

---

## 2. Authentication (`/auth`)

### `POST /auth/register` → 201
Any. Creates `User` + `CustomerProfile(name)` or `CompanyProfile(company_name)`.

```json
{ "name": "John Doe", "email": "j@x.com", "password": "secret123", "role": "CUSTOMER" }
```
`role`: `CUSTOMER | COMPANY | ADMIN`. Output: created `User` (`id, email, role, created_at...`).

### `POST /auth/login`
Any. JSON body (not form): `{ "email": "...", "password": "..." }` → `{ "access_token": "eyJ...", "role": "CUSTOMER" }`.

---

## 3. Profiles (`/profile`)

### `GET /profile/taxonomy` (any, used by onboarding + forms)
```json
{ "job_types": [{"id": "...", "name": "Remote"}], "job_functions": [{"id": "...", "name": "Backend Development"}] }
```

### `GET /profile/customer` (CUSTOMER)
```json
{ "email": "...", "name": "...", "phone": null, "location": " US",
  "job_types": [{"id": "...", "name": "..."}], "job_functions": [{"id": "...", "name": "..."}] }
```

### `PUT /profile/customer` (CUSTOMER)
Unlimited multi-select arrays (used by onboarding + profile page):
```json
{ "phone": "+1 555...", "location": "New York, NY",
  "job_type_ids": ["<uuid>", "..."], "job_function_ids": ["<uuid>", "..."] }
```
→ `{ "message": "Profile updated successfully." }`

### `GET /profile/company` (COMPANY)
`{ email, company_name, description, website, industry, location }`

### `PUT /profile/company` (COMPANY)
```json
{ "company_name": "...", "description": "...", "website": "...", "industry": "...", "location": "..." }
```

---

## 4. Data & CVs (`/data`)

### `POST /data/upload` (CUSTOMER, `multipart/form-data: file`)
Validates type/size (`DataController`), saves under `assets/files/<customer_id>/`, creates `CandidateDocument(customer_id, file_name, file_path, vector_id=file_id, is_primary=1-if-first)`.
→ `{ "signal": "file_upload_success", "file_id": "<vector_id>", "document_id": "<uuid>", "file_name": "..." }`

### `POST /data/process` (CUSTOMER, legacy chunk preview)
`{ file_id, chunk_size?, overlap_size? }` → section-segmented chunks (no vector write; use `/nlp/index` to embed).

### `POST /nlp/index` (CUSTOMER — the real indexer; documented here for flow)
`{ "file_id": "<vector_id>", "chunk_size": 500, "overlap_size": 50, "collection_name": null }`
LLM CV skills (canonicalized) ∪ taxonomy skills per chunk + global-skill safety net → embed → Chroma `candidates`.
→ `{ signal: "vectordb_index_success", customer_id, file_id, indexed_chunks, collection, total_in_collection }`

### `GET /data/download/me` (CUSTOMER) — file stream of own primary CV.
### `GET /data/download/candidate/{customer_id}` (COMPANY) — file stream; 403 unless an application exists at `CONSIDERED+`.
### `GET /data/customer/documents` (CUSTOMER) — list own `CandidateDocument`s.
### `DELETE /data/customer/documents/{document_id}` (CUSTOMER) — delete doc + vectors.

---

## 5. NLP — index, JD, match (`/nlp`)

### `GET /nlp/files` — list indexed `{file_id, customer_id}` combos in Chroma.
### `DELETE /nlp/delete/file` (CUSTOMER) `{ file_id }` · `DELETE /nlp/delete/customer` (CUSTOMER) — vector deletes.

### `POST /nlp/jd` (COMPANY)
```json
{ "jd_name": "Junior Backend Developer", "job_description": "Looking for...",
  "is_public": 1, "location": "Remote", "job_type_id": "<uuid|null>", "job_function_id": "<uuid|null>" }
```
LLM classified skills → canonical → embed → Chroma id `{company_id}::{jd_name}` + PG ownership row.
→ `{ message, jd_name, company_id, essential_skills[], elective_skills[], essential_count, elective_count, total_skills, required_experience }`

### `GET /nlp/jd` (COMPANY) — own JDs from PG: `[{ jd_id, jd_name, is_public, location, created_at }]`, `{ message, total, jds }`.
### `PUT /nlp/jd` (COMPANY) `{ jd_name, job_description }` — legacy update by name (re-extract + re-embed).
### `PUT /nlp/jd/{jd_id}` (COMPANY) `{ job_description, is_public?, location?, job_type_id?, job_function_id? }` — update by SQL id.
### `DELETE /nlp/jd/{jd_identifier}` (COMPANY) — accepts SQL id or legacy `jd_name`; deletes PG + Chroma. → `{ message, jd_id, jd_name }`.

### `POST /nlp/match` (COMPANY) — rank global pool for a JD.
```json
{ "jd_id": "<uuid>", "jd_name": "optional", "job_description": "or raw text", "top_k": 10 }
```
→ `{ signal: "match_success", company_id, jd_skills: {essential[], elective[]}, total_matches, orphan_skipped, results: [{
  candidate_id, file_id, customer_id, candidate_name, candidate_location, file_name, document_id, has_accepted_request,
  match_score, semantic_score, keyword_score, essential_score, elective_score, experience_score,
  job_type_score, job_function_score,
  required_experience, candidate_experience, experience_gap,
  matched_essential_skills[], matched_elective_skills[], missing_essential_skills[], missing_elective_skills[], extracted_skills[] }] }`
Weights: `0.30 sem + 0.30 kw + 0.20 exp + 0.10 type + 0.10 func`. Keyword: `ess*0.75+ele*0.25`, strict mode drops elective when `ess<0.5`. Location text is display-only (no location score).

### `GET /nlp/recommend-jobs?document_id=&top_k=10` (CUSTOMER) — reverse-match primary CV vs public JDs.
→ `{ recommended_jobs: [{ jd_id, jd_name, company_name, match_score, semantic_score, keyword_score, essential_score, elective_score, experience_score, job_type_score, job_function_score, required_experience, essential_skills[], elective_skills[], matched_essential_skills[], missing_essential_skills[], matched_elective_skills[], missing_elective_skills[], candidate_skills[] }] }`
Dashboard renders Skill ring = `keyword_score` (tooltip adds essential/elective/semantic).

### `GET /nlp/debug-match?jd_id=&document_id=` (CUSTOMER, own CV)
Audit bundle: `{ document_id, jd_id, jd_name, candidate_skills_raw[], candidate_skills_canonical[], jd_essential_raw[], jd_elective_raw[], jd_essential_canonical[], jd_elective_canonical[], matched_essential[], missing_essential[], matched_elective[], missing_elective[], match_map{}, scores: {keyword_score, essential_score, elective_score} }`.

---

## 6. ATS pipeline (`/ats`) — stages: `APPLIED, CONTACTED, CONSIDERED, INTERVIEWING, OFFER_SENT, HIRED, REJECTED, CANCELLED`

### `GET /ats/jobs/public` (any) → `{ jobs: [{ jd_id, jd_name, company_name, created_at }] }`
### `GET /ats/jobs/public/{jd_id}` (any; personalized when authed)
Always: `{ jd_id, jd_name, location, job_type{id,name}, job_function{id,name}, is_public, created_at, company{...}, job_description, essential_skills[], elective_skills[], skills_source: stored|heuristic_fallback, required_experience }`.
With `Authorization` (candidate): adds `candidate_skills[], matched_essential_skills[], missing_essential_skills[], matched_elective_skills[], missing_elective_skills[]` (detail page renders ✓ green / ✗ red).

### `POST /ats/jobs/{jd_id}/apply` (CUSTOMER) → 201 `{ message, application_id }` (400 if already in pipeline).
### `GET /ats/customer/applications` (CUSTOMER) → `{ applications: [{ application_id, company_name, jd_name, stage, created_at }] }`
### `PUT /ats/customer/applications/{application_id}/accept` (CUSTOMER) — `CONTACTED → CONSIDERED`.
### `POST /ats/company/contact` (COMPANY) `{ customer_id, jd_id }` → 201 (candidate enters `CONTACTED`).
### `GET /ats/board/{jd_id}` (COMPANY) → `{ jd_name, board: { APPLIED: [{application_id, candidate_id, candidate_name, candidate_email, candidate_phone, match_score, created_at}], CONTACTED: [], ... } }`
### `PUT /ats/board/{application_id}/move` (COMPANY) `{ stage: "INTERVIEWING" }` → `{ message, stage }`

---

## 7. Dev (`/dev`)

### `DELETE /dev/reset-everything` — **no auth, dev only.** Wipes Chroma collections + `assets/files` + truncates PG (keeps `alembic_version`), reseeds taxonomy. → `{ message: "System completely wiped and reset. Ready for clean testing!" }`
