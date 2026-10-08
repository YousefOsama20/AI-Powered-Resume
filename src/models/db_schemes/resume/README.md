## SQL Migrations (Alembic)

Postgres schema is versioned; ChromaDB + files are **not** migrated (see `scripts/reindex_skills.py` for vector metadata fixes, `DELETE /dev/reset-everything` for full wipe).

### Configuration

```bash
cp alembic.ini.example alembic.ini   # if present, else edit alembic.ini directly
```

- Set `sqlalchemy.url` in `alembic.ini` to your `DATABASE_URL` (postgres prod; sqlite file for quick dev).
- `env.py` loads `models.sql_models.Base.metadata` — autogenerate sees `users, customer_profiles, candidate_documents, company_profiles, job_descriptions, job_types, job_functions, customer_job_type, customer_job_function, job_applications`.

### Migration chain (heads)

| Rev | Name | Contents |
|---|---|---|
| `aa68720ebb06` | initial commit | base tables |
| `213df9a0e310` | add ATS pipeline models | `job_applications` + `PipelineStage` |
| `f9a69b3496ce` | multiple CVs + JD enrichments | `candidate_documents` (multi-CV, `is_primary`), `job_descriptions.is_public/location/job_type_id/job_function_id` |
| `7c4e1a2b3d5f` | add company profile fields | `company_profiles.website/industry/location` |

### Commands (run from this directory)

```bash
# Upgrade to latest
alembic upgrade head

# New migration after editing src/models/sql_models.py (run from src/)
alembic revision --autogenerate -m "Add ..."
alembic upgrade head

# Fresh dev DB alternative (no alembic history): handled by /dev/reset-everything (TRUNCATE, keeps alembic_version)
```

### Seed after migrate

```bash
cd src && python -m scripts.seed_taxonomy   # 6 JobTypes + 14 JobFunctions
```
