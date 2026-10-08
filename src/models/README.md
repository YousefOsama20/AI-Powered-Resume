# Models Directory

Central data shapes: SQL tables (`sql_models.py`), shared enums/constants (`enums/`). Import via `from models.sql_models import …` / `from models import …`.

## `sql_models.py` — PostgreSQL schema (SQLAlchemy `Base`)

| Table / Class | Key columns | Relationships |
|---|---|---|
| `User` (`users`) | `id (uuid pk)`, `email (unique, indexed)`, `hashed_password`, `role: UserRole`, `created_at/updated_at` | `customer_profile` 1-1, `company_profile` 1-1 (cascade delete) |
| `UserRole` | `CUSTOMER` (candidate), `COMPANY`, `ADMIN` | — |
| `CustomerProfile` (`customer_profiles`) | `id`, `user_id (unique FK)`, `name`, `phone?`, `location?` | `job_types[]` + `job_functions[]` (M2M, unlimited), `applications[]`, `documents[]` |
| `customer_job_type` / `customer_job_function` | assoc tables `(customer_profile_id, job_type_id / job_function_id)` composite PK | backs the M2M lists above |
| `CandidateDocument` (`candidate_documents`) | `id`, `customer_id FK`, `file_name`, `file_path`, `vector_id` (= Chroma `file_id`), `is_primary (1/0, first upload wins)`, `created_at` | `customer`, `applications[]` |
| `CompanyProfile` (`company_profiles`) | `id`, `user_id (unique FK)`, `company_name`, `description?`, `website?`, `industry?`, `location?` | `applications[]`, `jds[]` (cascade) |
| `JobDescription` (`job_descriptions`) | `id`, `company_id FK`, `jd_name` (Chroma id suffix), `is_public (1/0)`, `location?`, `job_type_id? FK`, `job_function_id? FK`, `created_at` | `job_type`, `job_function`, `company`, `applications[]` (cascade). Heavy text/skills/vectors live in Chroma, not here |
| `JobType` (`job_types`) | `id`, `name (unique)` — Full Time, Part Time, Remote, Contract, Freelance, Internship | — |
| `JobFunction` (`job_functions`) | `id`, `name (unique)` — 14 tracks incl. Backend/Frontend/Full Stack, AI/ML, Data, DevOps/Cloud… | — |
| `JobApplication` (`job_applications`) | `id`, `company_id FK`, `customer_id FK`, `jd_id FK`, `document_id? FK`, `stage: PipelineStage (default APPLIED)`, `match_score?`, `created_at/updated_at` | `company`, `customer`, `job_description`, `document` |
| `PipelineStage` | `APPLIED → CONTACTED → CONSIDERED → INTERVIEWING → OFFER_SENT → HIRED`, plus `REJECTED`, `CANCELLED` | candidate apply enters `APPLIED`; company contact enters `CONTACTED`; accept moves `CONTACTED→CONSIDERED` |

## `enums/`

- `__init__.py` — re-exports everything (import from `models` directly).
- `ProcessingEnum.py` — `ProcessingEnum`: allowed CV extensions (`.pdf`, `.docx`); used by `ProcessController`.
- `ResponseEnums.py` — `ResponseSignal`: `file_upload_success/failed`, `processing_*`, `embedding_*`, `vectordb_index/delete_*`, `match_success/failed`, `no_files`, `empty_job_description`… returned by `/data` + `/nlp` routes.
- `ResumeSectionEnum.py` — canonical CV sections + `SECTION_PATTERNS` regexes (Experience, Education, Skills…); used by `ProcessController` segmentation and `VectorDBController` section metadata.
- `TaxonomyDefaultEnums.py` — `DefaultTaxonomy`: 13-track seed skill lists (software, data, devops/cloud, security, design, marketing, finance, healthcare, HR, PM, legal, sales, mechanical/electrical). Seeds `assets/taxonomy/skills-taxonomy.json`; note canonical store uses singular `rest api`, `http`, `linux` — LLM variants are mapped by `SkillNormalizer`.
- `ExperienceControllerEnums.py` — `MONTH_MAP`, `SEASON_MAP`, `JD_EXPERIENCE_PATTERNS`, `MONTH_YEAR/YEAR_ONLY/NUMERIC/SEASON` patterns, `RESUME_STATED_EXP_PATTERN`; used by `ExperienceController`.
