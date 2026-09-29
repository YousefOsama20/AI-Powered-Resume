# Routes Directory Overview

The `routes` folder in this project is responsible for defining the API endpoints (routes) of the FastAPI application. It handles incoming HTTP requests, performs basic data validation using Pydantic schemas (defined in the `schemes` subdirectory), delegates business logic to various controllers, and returns the appropriate HTTP responses. The routers defined in this folder are imported and registered in the main application entry point (`src/main.py`).

## File and Route Details

### `base.py`
- **Function/Route:** `welcome`
  - **What it does:** Handles the `GET /api/v1/` endpoint. It returns basic application information such as the app name and version by reading from the application settings.
  - **Type:** Main route function.
  - **Where it is used:** Registered in `src/main.py` via `base_router`. It uses the `get_settings` dependency to fetch application configurations.

### `data.py`
- **Function/Route:** `upload_data`
  - **What it does:** Handles the `POST /api/v1/data/upload/{project_id}` endpoint. It validates an uploaded file, generates a unique file path within a specific project directory, and saves the file in chunks asynchronously using `aiofiles`.
  - **Type:** Main route function.
  - **Where it is used:** Registered in `src/main.py` via `data_router`. It delegates logic to `DataController` and `ProjectController`.
- **Function/Route:** `process_endpoint`
  - **What it does:** Handles the `POST /api/v1/data/process/{project_id}` endpoint. It retrieves a previously uploaded file's content and chunks it into smaller pieces (with optional overlap) for further NLP processing.
  - **Type:** Main route function.
  - **Where it is used:** Registered in `src/main.py` via `data_router`. It delegates logic to `ProcessController`.

### `nlp.py`
- **Function/Route:** `index_file`
  - **What it does:** Handles the `POST /api/v1/nlp/index/{project_id}` endpoint. It parses and chunks a file, extracts skills and experience, generates vector embeddings for the text chunks, and stores the embedded chunks in a Vector DB.
  - **Type:** Main route function.
  - **Where it is used:** Registered in `src/main.py` via `nlp_router`. It utilizes `ProcessController`, `EmbeddingController`, `ExtractionController`, `ExperienceController`, and `VectorDBController`.
- **Function/Route:** `match_resumes`
  - **What it does:** Handles the `POST /api/v1/nlp/match/{project_id}` endpoint. It matches a provided job description against all indexed candidates in a project using a Hybrid ATS Scoring Engine (semantic + keyword).
  - **Type:** Main route function.
  - **Where it is used:** Registered in `src/main.py` via `nlp_router`. It utilizes `MatchController`.
- **Function/Route:** `delete_file_index`
  - **What it does:** Handles the `DELETE /api/v1/nlp/{project_id}/file/{file_id}` endpoint. It deletes the indexed chunks for a specific file within a project from the Vector DB.
  - **Type:** Main route function.
  - **Where it is used:** Registered in `src/main.py` via `nlp_router`. It utilizes `VectorDBController`.
- **Function/Route:** `delete_project_index`
  - **What it does:** Handles the `DELETE /api/v1/nlp/{project_id}` endpoint. It deletes all indexed chunks for an entire project from the Vector DB.
  - **Type:** Main route function.
  - **Where it is used:** Registered in `src/main.py` via `nlp_router`. It utilizes `VectorDBController`.

### `__init__.py`
- Empty file used to make the directory a Python package.

### `schemes/data.py`
- **Model:** `ProcessRequest`
  - **What it does:** Defines the Pydantic data model for the process endpoint request to ensure `file_id`, `chunk_size`, and `overlap_size` are correctly typed and formatted.
  - **Type:** Pydantic Schema (Class).
  - **Where it is used:** Imported and used in `src/routes/data.py` by the `process_endpoint` function for request validation.

### `schemes/nlp.py`
- **Model:** `NLPIndexRequest` & `NLPMatchRequest`
  - **What it does:** Defines Pydantic data models for NLP index and match requests, validating fields like `file_id`, `job_description`, `top_k`, etc.
  - **Type:** Pydantic Schemas (Classes).
  - **Where it is used:** Imported and used in `src/routes/nlp.py` by the `index_file` and `match_resumes` functions for request validation.

### `schemes/__init__.py`
- Used to make the `schemes` directory a Python package.
