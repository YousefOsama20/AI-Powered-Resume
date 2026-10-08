# Helpers Directory Overview

Reusable app-wide utilities: typed settings + auth crypto. Import via `from helpers.config import get_settings` / `from helpers.security import …`.

## `config.py` — typed `.env` schema

`Settings(BaseSettings)` — every env var is typed; file resolved relative to `src/.env` (`Config.env_file = <src>/.env`). `get_settings()` is `lru_cache`d (read once).

| Group | Vars |
|---|---|
| App | `APP_NAME`, `APP_VERSION` (returned by `GET /welcome/`) |
| DB | `DATABASE_URL` (postgres prod, sqlite dev) |
| Auth | `JWT_SECRET_KEY`, `JWT_ALGORITHM` (e.g. `HS256`), `ACCESS_TOKEN_EXPIRE_MINUTES` (10080 = 7d) |
| Files | `FILE_ALLOWED_TYPES[]` (pdf/msword/docx MIME), `FILE_MAX_SIZE` (MB), `FILE_DEFAULT_CHUNK_SIZE` (bytes per `aiofiles` write) |
| ChromaDB | `VECTOR_DB_PATH`, `VECTOR_DB_COLLECTION` |
| Embeddings | `EMBEDDING_MODEL_NAME` (e.g. `all-MiniLM-L6-v2`), `EMBEDDING_BATCH_SIZE` (=64) |
| LLM (OpenAI-compatible; all nullable — empty disables LLM, heuristic fallback runs) | `GENERATION_BACKEND`, `GENERATION_API_KEY`, `GENERATION_API_URL`, `GENERATION_MODEL_ID`, `GENERATION_MAX_TOKENS`, `GENERATION_TEMPERATURE` |
| Prompts | `PRIMARY_LANG`, `DEFAULT_LANG` (`en`) |
| Misc | `INPUT_DAFAULT_MAX_CHARACTERS` (nullable legacy cap) |

Used in: `controllers/BaseController` (`self.app_settings`), `routes/base|data`, `main.py` lifespan (LLM factory), `stores/llm/*`. Copy `src/.env.example → src/.env` then fill secrets.

## `security.py` — passwords + JWT

- `get_password_hash(password)` — bcrypt `gensalt` + `hashpw`, returns utf-8 str. Used by `POST /auth/register`.
- `verify_password(plain, hashed)` — `bcrypt.checkpw` (utf-8 encode both). Used by `POST /auth/login`.
- `create_access_token(data, expires_delta?)` — adds `exp` (default `ACCESS_TOKEN_EXPIRE_MINUTES`), `jose.jwt.encode` with `JWT_SECRET_KEY`/`JWT_ALGORITHM`. Payload is `{sub: user.id, role}`; verified by `routes/deps.get_current_user`.
- Module-level `settings = get_settings()` (cached).
