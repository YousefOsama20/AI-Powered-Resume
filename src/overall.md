# AI-Powered Resume — Project Overview

> **Version:** 0.1 · **Stack:** FastAPI · ChromaDB · sentence-transformers · LangChain

---

## Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [Architecture Overview](#2-architecture-overview)
3. [Project Structure](#3-project-structure)
4. [Environment Variables & API Keys](#4-environment-variables--api-keys)
5. [API Endpoints](#5-api-endpoints)
6. [How to Run Locally](#6-how-to-run-locally)
7. [How to Run with Docker](#7-how-to-run-with-docker)
8. [End-to-End Workflow](#8-end-to-end-workflow)
9. [Key Components Explained](#9-key-components-explained)
10. [Dependencies](#10-dependencies)

---

## 1. What Is This Project?

**AI-Powered Resume** is a **FastAPI** backend service that lets you:

- 📤 **Upload** a resume (PDF or DOCX).
- ✂️ **Parse & chunk** it into section-aware pieces (Skills, Experience, Education, Projects, Certifications, Summary).
- 🧠 **Embed** every chunk into a dense vector using `sentence-transformers` (`all-MiniLM-L6-v2`).
- 🗄️ **Store** the vectors in a persistent **ChromaDB** vector database.
- 🔍 **Search** across all indexed resumes with natural-language queries, optionally filtered by resume section.
- 🗑️ **Delete** indexed data by file or by project.

The system is designed to be stateless at the HTTP layer — all state lives in ChromaDB on disk.

---

## 2. Architecture Overview

```
Client (HTTP) / Streamlit Frontend
      │
      ▼
┌─────────────────────────────────────┐
│           FastAPI (main.py)         │
│  ┌──────────┬──────────┬──────────┐ │
│  │ /api/v1/ │ /data/   │  /nlp/   │ │
│  │  (base)  │ (upload) │ (match)  │ │
│  └──────────┴──────────┴──────────┘ │
└─────────────────────────────────────┘
      │               │
      ▼               ▼
DataController   ProcessController
(validate/save)  (parse/extract)
                      │
                      ▼
        NLP & Extraction Layer (spaCy)
        (skills-taxonomy.json NER)
                      │
                      ▼
               EmbeddingEngine
           (sentence-transformers)
                      │
                      ▼
       Storage Layer (ChromaDB) & Ranking
       (Hybrid: 60% Semantic / 40% Keyword)
```

---

## 3. Project Structure

```
AI_Powered_Resume/
├── overall.md                ← YOU ARE HERE
├── docker/
│   ├── Dockerfile            # Docker image definition
│   └── .dockerignore
│
├── src/                      # All application code lives here
│   ├── main.py               # FastAPI app entry point
│   ├── requirements.txt      # Python dependencies
│   ├── .env                  # Environment variables (API keys, config)
│   │
│   ├── routes/               # HTTP route definitions
│   │   ├── base.py           # GET /api/v1/ — health/welcome
│   │   ├── data.py           # POST /api/v1/data/upload, /process
│   │   ├── nlp.py            # POST/DELETE /api/v1/nlp/...
│   │   └── schemes/
│   │       └── data.py       # Pydantic request schemas
│   │
│   ├── controllers/          # Business logic layer
│   │   ├── BaseController.py       # Shared settings & helpers
│   │   ├── DataController.py       # File validation & unique path generation
│   │   ├── ProjectController.py    # Project directory management
│   │   ├── ProcessController.py    # File parsing, section detection, chunking
│   │   ├── EmbeddingController.py  # sentence-transformers embedding
│   │   ├── VectorDBController.py   # ChromaDB CRUD + semantic search
│   │   └── loaderController.py     # PDF/DOCX file loaders
│   │
│   ├── models/
│   │   └── enums/
│   │       ├── ResumeSectionEnum.py   # Section names + regex patterns
│   │       ├── ResponseEnums.py       # Standardised signal strings
│   │       └── ProcessingEnum.py      # .pdf / .docx file type enum
│   │
│   ├── helpers/
│   │   └── config.py         # Pydantic-Settings loader (reads .env)
│   │
│   └── assets/
│       ├── files/            # Uploaded resume files (per project sub-folders)
│       └── vectordb/         # ChromaDB persistent storage
```

---

## 4. Environment Variables & API Keys

All configuration lives in **`src/.env`**. Edit and fill in your values.

```dotenv
# ── Application ────────────────────────────────────────────────────────────
APP_NAME="ai-power-resume"
APP_VERSION="0.1"

# ── API Keys ───────────────────────────────────────────────────────────────
OPENAI_API_KEY=""          # Required only if you add OpenAI-based features
                            # (not used by the current embedding pipeline,
                            #  which uses sentence-transformers locally)

# ── File Upload Settings ───────────────────────────────────────────────────
FILE_ALLOWED_TYPES=["application/pdf","application/msword","application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
FILE_MAX_SIZE=16                  # Maximum file size in MB
FILE_DEFAULT_CHUNK_SIZE=512000    # Read chunk size in bytes (512 KB)

# ── Vector DB (ChromaDB) ──────────────────────────────────────────────────
VECTOR_DB_PATH="./assets/vectordb"         # Where ChromaDB persists data
VECTOR_DB_COLLECTION="resume_chunks"       # Default collection name

# ── Embedding Model (sentence-transformers) ───────────────────────────────
EMBEDDING_MODEL_NAME="all-MiniLM-L6-v2"   # HuggingFace model (auto-downloaded)
EMBEDDING_BATCH_SIZE=64                    # Batch size for embedding
```

### API Key Summary Table

| Key | Required? | Purpose |
|-----|-----------|---------|
| `OPENAI_API_KEY` | Optional (currently unused) | Placeholder for future OpenAI-based features (GPT analysis, re-ranking, etc.) |

> **Note:** The current embedding pipeline runs **100% locally** using `sentence-transformers`.
> No external API calls are made. The `OPENAI_API_KEY` field is defined but not actively used in this version.

---

## 5. API Endpoints

Base URL: `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`

### 5.1 Health Check

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/` | Returns app name and version |

**Response:**
```json
{
  "app_name": "ai-power-resume",
  "app_version": "0.1"
}
```

---

### 5.2 Data Routes — `/api/v1/data`

#### `POST /api/v1/data/upload/{project_id}`

Upload a resume file. Files are validated (type + size) and stored under `assets/files/{project_id}/`.

**Path params:** `project_id` — your logical project/user identifier
**Body:** `multipart/form-data` with a `file` field (PDF or DOCX, max 16 MB)

**Success Response:**
```json
{
  "signal": "file_upload_success",
  "file_id": "abc123xyz_resume.pdf"
}
```

**Error Signals:**
- `file_type_not_supported` — Not a PDF or DOCX
- `file_size_exceeded` — File larger than 16 MB
- `file_upload_failed` — Disk write error

---

#### `POST /api/v1/data/process/{project_id}`

Parse an uploaded file and return section-aware chunks (does **not** store in vector DB — useful for preview/debugging).

**Body (JSON):**
```json
{
  "file_id": "abc123xyz_resume.pdf",
  "chunk_size": 500,
  "overlap_size": 50
}
```

**Success Response:**
```json
{
  "signal": "processing_success",
  "total_chunks": 12,
  "chunks": [
    {
      "page_content": "[Technical Skills]\nPython, FastAPI, Docker...",
      "metadata": {
        "project_id": "my_project",
        "file_id": "abc123xyz_resume.pdf",
        "section": "Technical Skills",
        "chunk_id": "abc123xyz_resume.pdf_technical_skills_0"
      }
    }
  ]
}
```

---

### 5.3 NLP Routes — `/api/v1/nlp`

#### `POST /api/v1/nlp/index/{project_id}`

Parse → embed → store a file's chunks into ChromaDB. **This is the main indexing step.**

**Body (JSON):**
```json
{
  "file_id": "abc123xyz_resume.pdf",
  "chunk_size": 500,
  "overlap_size": 50,
  "collection_name": null
}
```

**Success Response:**
```json
{
  "signal": "vectordb_index_success",
  "project_id": "my_project",
  "file_id": "abc123xyz_resume.pdf",
  "indexed_chunks": 12,
  "collection": "resume_chunks",
  "total_in_collection": 45
}
```

---

#### `POST /api/v1/nlp/match/{project_id}`

Compares a Job Description against all indexed candidates in a project using a Hybrid Scoring Engine (60% Semantic Cosine Similarity + 40% Keyword Jaccard Index).

**Body (JSON):**
```json
{
  "job_description": "Looking for a Python Developer with experience in FastAPI and Machine Learning...",
  "top_k": 5
}
```

**Success Response:**
```json
{
  "signal": "match_success",
  "project_id": "job_123",
  "results": [
    {
      "candidate_id": "abc123xyz_resume.pdf",
      "match_score": 87.5,
      "semantic_score": 85.0,
      "keyword_score": 91.2,
      "extracted_skills": ["Python", "FastAPI", "Machine Learning", "Docker"],
      "missing_skills": ["Kubernetes"]
    }
  ]
}
```

---

#### `DELETE /api/v1/nlp/{project_id}/file/{file_id}`

Remove all indexed vectors for a specific file.

**Success Response:**
```json
{
  "signal": "vectordb_delete_success",
  "project_id": "my_project",
  "file_id": "abc123xyz_resume.pdf",
  "deleted_chunks": 12
}
```

---

#### `DELETE /api/v1/nlp/{project_id}`

Remove **all** vectors for an entire project.

**Success Response:**
```json
{
  "signal": "vectordb_delete_success",
  "project_id": "my_project",
  "deleted_chunks": 45
}
```

---

## 6. How to Run Locally

### Prerequisites

- Python **3.10+**
- `pip` or `pip3`
- `libmagic` system library (for MIME type detection):
  ```bash
  # Ubuntu/Debian
  sudo apt-get install libmagic1

  # macOS
  brew install libmagic
  ```

### Steps

```bash
# 1. Clone the repo (if not already done)
git clone <repo-url>
cd AI_Powered_Resume

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r src/requirements.txt

# 4. Configure your environment
nano src/.env                      # fill in OPENAI_API_KEY if needed

# 5. Run the server from the src/ directory  ← IMPORTANT
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server will be available at:
- **API:** `http://localhost:8000`
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

> **Important:** Always run `uvicorn` from inside the `src/` directory so that
> relative paths (`.env`, `assets/`) resolve correctly.

---

## 7. How to Run with Docker

```bash
# 1. Build the image (run from repo root)
docker build -f docker/Dockerfile -t ai-powered-resume .

# 2. Run the container
docker run -d \
  --name resume-api \
  -p 8000:8000 \
  -v $(pwd)/src/assets:/app/assets \
  --env-file src/.env \
  ai-powered-resume

# 3. Check logs
docker logs -f resume-api
```

> The `-v` volume mount persists uploaded files and ChromaDB data across container restarts.

---

## 8. End-to-End Workflow

```
Step 1: Upload Resumes
  POST /api/v1/data/upload/{project_id}
  → returns file_id (Candidate ID)

Step 2: Index Resumes (Parse + Extract Skills + Embed + Store)
  POST /api/v1/nlp/index/{project_id}
  body: { "file_id": "<returned file_id>" }
  → skills extracted and vectors stored in ChromaDB

Step 3: Match Job Description (ATS Scoring)
  POST /api/v1/nlp/match/{project_id}
  body: { "job_description": "Your JD here...", "top_k": 5 }
  → returns ranked candidates with hybrid scores (Semantic + Keyword) and missing skills

Step 4 (optional): Cleanup
  DELETE /api/v1/nlp/{project_id}/file/{file_id}   ← single candidate
  DELETE /api/v1/nlp/{project_id}                   ← entire job/project
```

### Quick cURL Example

```bash
PROJECT_ID="job_123"

# Step 1 — Upload
curl -X POST "http://localhost:8000/api/v1/data/upload/${PROJECT_ID}" \
  -F "file=@/path/to/resume.pdf"
# → { "file_id": "abc123_resume.pdf" }

# Step 2 — Index
curl -X POST "http://localhost:8000/api/v1/nlp/index/${PROJECT_ID}" \
  -H "Content-Type: application/json" \
  -d '{"file_id": "abc123_resume.pdf"}'

# Step 3 — Match ATS
curl -X POST "http://localhost:8000/api/v1/nlp/match/${PROJECT_ID}" \
  -H "Content-Type: application/json" \
  -d '{"job_description": "We need Python and ML experts.", "top_k": 3}'
```

---

## 9. Key Components Explained

| Component | File | Role |
|-----------|------|------|
| `ProcessController` | `controllers/ProcessController.py` | Reads PDF/DOCX, extracts text, handles raw data ingestion. |
| `ExtractionController` (TBD) | `controllers/ExtractionController.py` | Uses spaCy and a `skills-taxonomy.json` for Named Entity Recognition (NER) to extract skills. |
| `EmbeddingController` | `controllers/EmbeddingController.py` | Loads `all-MiniLM-L6-v2` as a singleton; returns L2-normalised 384-dim vectors. |
| `VectorDBController` | `controllers/VectorDBController.py` | Wraps ChromaDB persistent client; stores candidate vectors and metadata (extracted skills). |
| `MatchController` (TBD) | `controllers/MatchController.py` | Implements the Hybrid Ranking Engine: calculates Semantic Score (Cosine) and Keyword Score (Jaccard). |
| `DataController` | `controllers/DataController.py` | Validates MIME type & size; generates collision-free file paths. |
| `Settings` | `helpers/config.py` | `pydantic-settings` singleton loaded from `.env` |

### Section Detection Logic

`ProcessController` scans each line of the resume text against regex patterns:

| Section | Matched Headers |
|---------|----------------|
| `Technical Skills` | "Skills", "Tech Stack", "Programming Languages", "Core Competencies", "Technologies", "Tools" |
| `Experience` | "Work Experience", "Professional Experience", "Employment History", "Internships" |
| `Education` | "Education", "Academic Background", "Qualifications", "Degrees" |
| `Projects` | "Projects", "Personal Projects", "Academic Projects", "Key Projects" |
| `Certifications` | "Certifications", "Licenses & Certifications", "Courses", "Credentials" |
| `Summary` | "Professional Summary", "Profile", "About Me", "Objective", "Career Objective" |

---

## 10. Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn[standard]` | ASGI server |
| `python-multipart` | File upload support |
| `python-dotenv` / `pydantic-settings` | `.env` configuration |
| `aiofiles` | Async file I/O |
| `langchain` / `langchain-community` / `langchain-text-splitters` | Document model + text chunking |
| `pypdf` / `python-docx` / `PyMuPDF` | PDF and DOCX parsing |
| `sentence-transformers` | Local embedding model (`all-MiniLM-L6-v2`) |
| `chromadb` | Vector store (persistent, embedded) |
| `python-magic` | MIME type detection |

---

*Generated from project source — 2026-09-27*
