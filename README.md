# 🚀 AI-Powered Resume & Job Matching ATS

A powerful backend service built with **FastAPI** that acts as an intelligent Applicant Tracking System (ATS). It evaluates how well candidate resumes match a given Job Description (JD) using a hybrid scoring system (semantic similarity + keyword/skill extraction).

---

## 📖 The Core Idea

Recruiters and job seekers struggle to quickly assess how well a resume matches a job description, leading to missed opportunities or overlooked qualified candidates. **AI-Powered Resume ATS** solves this by:

1. **Intelligent Parsing & NLP Extraction:** It takes PDF or DOCX resumes and uses custom logic alongside `spaCy` (Tokenization & NER) to extract specific technical skills based on a skills taxonomy.
2. **Local AI Embeddings:** It uses the `sentence-transformers` library (`all-MiniLM-L6-v2`) to turn resume content and job descriptions into 384-dimensional dense semantic vectors locally. **Zero external AI API costs.**
3. **Hybrid Ranking Engine:** It stores candidate vectors and metadata in **ChromaDB**. When a Job Description is provided, it calculates a **Weighted Hybrid Score**:
   - **60% Semantic Score** (Cosine Similarity via ChromaDB)
   - **40% Keyword Score** (Jaccard Index matching extracted skills vs JD required skills)
4. **Actionable Insights:** It outputs ranked candidates with their overall match score and lists missing skills/keyword gaps to provide actionable feedback for job seekers and recruiters.

### 🏗 Architecture Overview

The system adheres to an **MVC-inspired architecture**:
- **Controllers** handle the heavy lifting:
  - `ProcessController`: Document ingestion and parsing.
  - `ExtractionController` (spaCy): NLP pipeline for extracting skills using `skills-taxonomy.json`.
  - `EmbeddingController` (sentence-transformers): Semantic vector generation.
  - `VectorDBController` (ChromaDB): Storage and similarity retrieval.
  - `MatchController`: Hybrid scoring (Cosine + Jaccard) and ranking logic.
- **Routes** (`data.py`, `nlp.py`) act as the HTTP presentation layer.
- **Models** (`schemas`, `enums`) strictly define inputs, outputs, and status signals.

---

## 🛠 Tech Stack

- **Backend Framework:** FastAPI (Python 3.10+)
- **Embeddings:** `sentence-transformers` (Local HuggingFace Models)
- **Vector Database:** ChromaDB (Embedded/Persistent)
- **NLP & Extraction:** `spaCy`
- **Document Processing:** PyMuPDF, python-docx, LangChain
- **File Validation:** `python-magic`

---

## 🚀 How to Run Locally

### 1. Prerequisites
Ensure you have Python 3.10+ installed. You also need the `libmagic` C library installed on your system for file MIME type validation:
- **Ubuntu/Debian:** `sudo apt-get install libmagic1`
- **macOS:** `brew install libmagic`
- **Windows:** Installed automatically via `python-magic-bin` (if needed).

### 2. Setup Virtual Environment
```bash
git clone <your-repo-url>
cd AI_Powered_Resume

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r src/requirements.txt
# Download spaCy English model
python -m spacy download en_core_web_sm
```

### 4. Configure Environment
Copy the example environment file:
```bash
cp src/.env.example src/.env
```
*(The defaults in `.env` are ready to go for local usage).*

### 5. Start the Server
**Important:** Always start the server from inside the `src` directory so relative paths resolve correctly.
```bash
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Navigate to [http://localhost:8000/docs](http://localhost:8000/docs) to access the interactive Swagger API documentation.

---

## 🔌 API Workflow & Usage

The application centers around matching multiple candidate resumes against a Job Description.

### Step 1: Upload Candidate Resumes
Upload raw PDF or DOCX files for your candidates.
* **Endpoint:** `POST /api/v1/data/upload/{project_id}`
* **Returns:** A unique `file_id` (candidate ID).

### Step 2: Index the Candidates (Parse + Extract + Embed + Store)
Extracts the text, extracts skills using spaCy, generates embeddings, and saves it to ChromaDB with skill metadata.
* **Endpoint:** `POST /api/v1/nlp/index/{project_id}`
* **Body:** `{"file_id": "<returned_file_id>"}`

### Step 3: Match Job Description (Hybrid Ranking)
Provide a Job Description text. The engine extracts required skills, computes semantic similarity, calculates the Jaccard index for skills, and returns a ranked list of candidates.
* **Endpoint:** `POST /api/v1/nlp/match/{project_id}`
* **Body:**
```json
{
  "job_description": "We are looking for a Python developer with experience in FastAPI, Machine Learning, and ChromaDB.",
  "top_k": 5
}
```
* **Returns:** Ranked dashboard data containing `candidate_id`, `match_score` (0-100%), and `missing_skills`.

### Step 4: Cleanup (Optional)
* **Delete a Candidate:** `DELETE /api/v1/nlp/{project_id}/file/{file_id}`
* **Delete a Project/Job:** `DELETE /api/v1/nlp/{project_id}`

---

## 📂 Folder Structure

```text
src/
├── controllers/          # Business logic (File Handling, NLP, Matching, ChromaDB)
├── routes/               # API endpoints (Uploads, Indexing, Match)
│   └── schemes/          # Pydantic request models
├── models/               # Application-wide Enums and Constants
├── helpers/              # Settings & Configurations (.env loader)
├── assets/               # Persistent data
│   ├── files/            # Uploaded PDF/DOCX resumes
│   ├── taxonomy/         # skills-taxonomy.json for spaCy NER
│   └── vectordb/         # ChromaDB SQLite persistence files
├── requirements.txt      # Python dependencies
└── main.py               # FastAPI entry point
docker/                   # Dockerfile and ignore rules
```
