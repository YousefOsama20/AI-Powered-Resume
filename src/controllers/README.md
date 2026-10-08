# Controllers Directory

Business logic between `routes/` and data layers (Postgres, ChromaDB, files). Import via `from controllers import X`. Shared base: `BaseController` (loads `Settings`, `base_dir`).

## `SkillNormalizer.py` ⭐ canonical skill layer
Single source of truth so JD free-form and CV taxonomy strings compare equally.
- `normalize_skill(s)` — lower → `-`/`_`→space → strip quotes/punct → drop trailing `skill(s)` → `ALIASES` → singularize last token (`apis→api`). Idempotent.
- `ALIASES` (seed): `rest apis→rest api`, `http protocols→http`, `linux commands→linux`, `problem-solving skills→problem solving`, `google cloud platform→gcp`, `amazon web services→aws`, `postgres→postgresql`, `nodejs→node.js`, `k8s→kubernetes`, `ci cd→ci/cd`, …
- `normalize_skill_list(items)` — normalize + dedupe (order-preserving).
- `normalize_classified({essential, elective})` — normalize both + `elective −= essential`.
- `match_skills(candidate, required, threshold=0.88)` — exact on canonical + difflib fuzzy fallback → `(matched, missing, map)` in required-name space.
- `score_from_matches(m_ess, n_ess, m_ele, n_ele)` — shared scorer: `ess=len(m)/n (empty-ess→1.0)`, `ele=len(m)/n (empty→0.0)`; both present: strict mode (`ess<0.5 → kw=ess`, else `ess*0.75+ele*0.25`); only-ess → `kw=ess`; neither → `0.0`.
- Consumed by: `LLMExtractionController`, `ExtractionController`, `JDController`, `routes/nlp._normalize_classified_skills`, both `MatchController` paths, `routes/ats` personalized overlap, `scripts/reindex_skills`.

## `MatchController.py` — hybrid ranker (both directions)
- `__init__` — wires VectorDB, Embedding, Extraction, Experience, LLMExtraction, JD controllers.
- `match_candidates(db, customer_id?, job_description?, jd_name?, top_k≤50, company_id?) -> (results, jd_skills)` — **company side.** Resolves JD (company-scoped `{company_id}::{jd_name}` first), canonicalizes skills, pulls up to 5000 chunks (whole pool, not top-100), groups by `file_id`, scores: `hybrid = .25 sem + .25 kw + .20 exp + .10 loc + .10 type + .10 func`; collapses to best-row-per-customer; skips orphan vectors (no PG profile). Used by `POST /nlp/match`.
- `recommend_jobs(db, document_id, top_k) -> [jobs]` — **candidate side.** Loads primary `CandidateDocument`, averages its chunk embeddings, queries `jds` (`top_k*3` for re-rank), filters `is_public==1`, same keyword/strict-mode + experience + loc/type/func enrichment. Returns per-JD scores **plus** `matched/missing_essential/elective[]` + `candidate_skills[]` (dashboard chips). Used by `GET /nlp/recommend-jobs`.

## `JDController.py` (`JD_COLLECTION = "jds"`)
- `_chroma_id(jd_name, company_id)` — `{company_id}::{jd_name}` (legacy bare `jd_name` read fallback); `_display_name`, `_parse_skill_string` (JSON-list/comma tolerant + canonical).
- `store_jd(jd_name, company_id, job_description, skills{essential,elective}, required_exp, embedding)` — upsert doc + `essential_skills/elective_skills/required_experience/company_id/jd_name` metadata; enforces `elective −= essential`.
- `get_jd(jd_name, company_id?)` — scoped-then-legacy fetch; legacy flat `skills` → essential; returns `{job_description, skills{essential,elective}, required_experience, embedding}`.
- `list_jds(company_id?)`, `delete_jd(jd_name, company_id?)` (scoped + legacy sweep).

## `LLMExtractionController.py`
- `is_available` — true when `GENERATION_MODEL_ID` configured (`LLMProvider` via `GENERATION_BACKEND/KEY/URL`).
- `extract_skills_from_jd(text) -> {essential, elective}` — system/user prompts from `stores/llm/templates/locales/en/skill_extraction.py` (canonical-name rules: `rest api` not `apis`, etc.); tolerant JSON/code-fence/comma parsing; flat-list fallback → all-essential.
- `extract_skills_from_cv(text) -> [...]` — same prompt system for resumes; flat list.
- `_normalize_skill_list` — delegates to `SkillNormalizer` (legacy lower/dedupe fallback).

## `ExtractionController.py` (spaCy fallback, no LLM needed)
- Taxonomy from `assets/taxonomy/skills-taxonomy.json` (seeded from `DefaultTaxonomy`); `_flatten_taxonomy`, `_build_matcher`/`_init_matcher` (`PhraseMatcher` on `LOWER`), lazy `en_core_web_sm` (auto-download).
- `extract_skills(text, filter_skills?)` — full-taxonomy (indexing) or restricted matcher; output canonicalized via `SkillNormalizer`.
- `split_jd_sections(text)` — splits on `nice to have|preferred|bonus|a plus|desirable|beneficial|optional|…`; `extract_classified_skills(jd)` — required-part vs nice-part sets (`elective −= essential`; no marker → all-essential). Used when LLM down/empty (`routes/nlp`, `routes/ats` read-repair).

## `ExperienceController.py`
- `extract_required_experience(jd)` (regex `JD_EXPERIENCE_PATTERNS`), `extract_candidate_experience(text)` (date-range merge + stated-exp regex), `calculate_experience_score(required?, actual)`; helpers `_parse_month/_parse_date_ranges/_merge_overlapping_ranges/_calculate_total_years`. Patterns in `models/enums/ExperienceControllerEnums.py`.

## `EmbeddingController.py` + `VectorDBController.py`
- Embedding: lazy `SentenceTransformer(EMBEDDING_MODEL_NAME)`; `embed_text`, `embed_texts` (batch `EMBEDDING_BATCH_SIZE`). Used by `/nlp/index` and JD store/match.
- VectorDB: `_get_collection`, `index_chunks(chunks, embeddings, collection)` (writes `skills, experience_years, file_id, customer_id, section`), `search(query_embedding, customer_id?, n_results, collection)` (cosine → score), `delete_by_file/customer`, `get_collection_count`. Collections: `CANDIDATE_COLLECTION="candidates"` (import from `VectorDBController`), `JD_COLLECTION="jds"`.

## `ProcessController.py` / `DataController.py` / `ProjectController.py` / `loaderController.py`
- Process: `get_file_extension/get_file_loader (PDF/DOCX)/get_file_content/clean_text/match_section_header/segment_text_into_sections/process_file_content(chunk_size, overlap)` — sections via `ResumeSectionEnum`. `__init__(customer_id)` (not project).
- Data: `validate_uploaded_file` (type/size vs `FILE_ALLOWED_TYPES/MAX_SIZE`), `generate_unique_filepath` (+ `get_clean_file_name`).
- Project: `get_customer_path(customer_id)` → `assets/files/<customer_id>/` (legacy name kept).
- loader: `load_pdf` (PyMuPDF/pypdf), `load_docx` (python-docx).

## `__init__.py`
Exports all of the above + `SkillNormalizer` helpers (`normalize_skill`, `normalize_skill_list`, `normalize_classified`, `match_skills`, `score_from_matches`).
