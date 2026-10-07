# API Endpoint Documentation

This document provides a comprehensive guide to all the available API endpoints in the AI-Powered Resume Platform, detailing their required inputs (parameters, JSON bodies) and their expected outputs.

---

## 1. Authentication (`/auth`)

### `POST /auth/register`
**Description:** Registers a new user as either a Customer (Candidate) or a Company.
**Role Required:** ANY

**Input (JSON Body):**
```json
{
  "email": "user@example.com",
  "password": "strongpassword123",
  "role": "CUSTOMER", // OR "COMPANY"
  // For CUSTOMER:
  "name": "John Doe",
  "location": "New York",
  // For COMPANY:
  "company_name": "Tech Corp",
  "description": "Tech solutions"
}
```

**Output:**
```json
{
  "message": "User registered successfully",
  "user_id": "uuid-string-here"
}
```

---

### `POST /auth/login`
**Description:** Authenticates a user and returns a JWT access token.
**Role Required:** ANY

**Input (`application/x-www-form-urlencoded`):**
- `username`: The user's email address.
- `password`: The user's password.

**Output:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer"
}
```

---

## 2. Profiles (`/api/base`)

### `GET /api/base/me`
**Description:** Retrieves the profile information of the currently logged-in user.
**Role Required:** CUSTOMER or COMPANY

**Input:** *(None. Requires Bearer Token)*

**Output:**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "role": "CUSTOMER",
  "profile": {
    "name": "John Doe",
    "location": "New York",
    "cv_file_path": "/path/to/cv",
    "cv_vector_id": "file_id.pdf"
  }
}
```

---

## 3. Data & CVs (`/api/data`)

### `POST /api/data/upload`
**Description:** Customer uploads their resume file (PDF or DOCX).
**Role Required:** CUSTOMER

**Input (`multipart/form-data`):**
- `file`: The physical document.

**Output:**
```json
{
  "signal": "file_upload_success",
  "file_id": "uuid_filename.pdf"
}
```

---

### `POST /api/data/process`
**Description:** Parses the uploaded CV, extracts sections, chunks text, and indexes it into ChromaDB.
**Role Required:** CUSTOMER

**Input (JSON Body):**
```json
{
  "file_id": "uuid_filename.pdf",
  "chunk_size": 500,
  "overlap_size": 50
}
```

**Output:**
```json
{
  "signal": "processing_success",
  "total_chunks": 15,
  "chunks": [
    {
      "page_content": "Experienced in Python and FastAPI...",
      "metadata": { "section": "Experience", "chunk_id": "..." }
    }
  ]
}
```

---

### `GET /api/data/download/me`
**Description:** Allows a Customer to securely download the CV they previously uploaded.
**Role Required:** CUSTOMER

**Input:** *(None)*
**Output:** File stream (`application/pdf` or `application/msword`).

---

### `GET /api/data/download/candidate/{customer_id}`
**Description:** Allows a Company to download a Candidate's CV, **only if** the candidate is at `CONSIDERED` stage or beyond (`INTERVIEWING`, `OFFER_SENT`, `HIRED`) in the ATS pipeline.
**Role Required:** COMPANY

**Input (Path Parameter):**
- `customer_id`: The ID of the candidate.

**Output:** File stream. *(Returns 403 Forbidden if no qualifying application exists).*

---

## 4. Job Descriptions & NLP (`/api/nlp`)

### `POST /api/nlp/jd`
**Description:** Creates a new Job Description. Extracts skills via LLM, embeds the text, and stores ownership.
**Role Required:** COMPANY

**Input (JSON Body):**
```json
{
  "jd_name": "Senior Python Backend Engineer",
  "job_description": "We need someone with 5+ years of FastAPI..."
}
```

**Output:**
```json
{
  "message": "Job description stored successfully.",
  "jd_name": "Senior Python Backend Engineer",
  "company_id": "company-uuid",
  "essential_skills": ["Python", "FastAPI"],
  "elective_skills": ["Docker", "AWS"],
  "required_experience": 5.0
}
```

---

### `GET /api/nlp/jd`
**Description:** Lists all Job Descriptions owned by the logged-in Company.
**Role Required:** COMPANY

**Input:** *(None)*

**Output:**
```json
{
  "message": "Job descriptions retrieved successfully.",
  "total": 1,
  "jds": [
    {
      "jd_name": "Senior Python Backend Engineer",
      "company_id": "company-uuid",
      "essential_skills_count": 2,
      "elective_skills_count": 2,
      "required_experience": 5.0
    }
  ]
}
```

---

### `PUT /api/nlp/jd`
**Description:** Updates an existing Job Description. Overwrites the vector and re-extracts skills.
**Role Required:** COMPANY

**Input (JSON Body):**
```json
{
  "jd_name": "Senior Python Backend Engineer",
  "job_description": "Updated requirements text..."
}
```
**Output:** Same as `POST /api/nlp/jd`.

---

### `DELETE /api/nlp/jd/{jd_name}`
**Description:** Deletes a Job Description from both PostgreSQL and ChromaDB.
**Role Required:** COMPANY

**Input (Path Parameter):**
- `jd_name`: The name of the JD to delete.

**Output:**
```json
{
  "message": "Job description deleted successfully.",
  "jd_name": "Senior Python Backend Engineer"
}
```

---

### `POST /api/nlp/match`
**Description:** Evaluates a JD against the Global Candidate Pool using Hybrid Search (Semantic + Keywords + Experience).
**Role Required:** COMPANY

**Input (JSON Body):**
```json
{
  "jd_name": "Senior Python Backend Engineer", // Use stored JD
  "job_description": "", // OR pass raw text
  "top_k": 10
}
```

**Output:**
```json
{
  "signal": "match_success",
  "total_matches": 10,
  "results": [
    {
      "candidate_id": "file_id.pdf",
      "customer_id": "customer-uuid",
      "candidate_name": "John Doe",
      "candidate_location": "New York",
      "match_score": 87.5,
      "semantic_score": 85.0,
      "keyword_score": 90.0,
      "experience_score": 100.0,
      "matched_essential_skills": ["Python", "FastAPI"],
      "missing_essential_skills": []
    }
  ]
}
```

---

## 5. ATS Kanban Pipeline (`/api/ats`)

The ATS (Applicant Tracking System) router manages the pipeline lifecycle of a Candidate applying to a Job Description. Valid pipeline stages are:
`APPLIED`, `CONTACTED`, `CONSIDERED`, `INTERVIEWING`, `OFFER_SENT`, `HIRED`, `REJECTED`, `CANCELLED`.

### `GET /api/ats/jobs/public`
**Description:** Candidates can browse all publicly available job descriptions.
**Role Required:** ANY (No auth required, or CUSTOMER)

**Input:** *(None)*

**Output:**
```json
{
  "jobs": [
    {
      "jd_id": "job-uuid",
      "jd_name": "Senior Python Backend Engineer",
      "company_name": "Tech Corp",
      "created_at": "2024-01-01T12:00:00.000Z"
    }
  ]
}
```

---

### `POST /api/ats/jobs/{jd_id}/apply`
**Description:** A Candidate applies directly to a public Job Description. Places them in the `APPLIED` stage.
**Role Required:** CUSTOMER

**Input (Path Parameter):** `jd_id`

**Output:**
```json
{
  "message": "Successfully applied to job.",
  "application_id": "app-uuid"
}
```

---

### `GET /api/ats/customer/applications`
**Description:** Candidate views all jobs they have applied to or were contacted for.
**Role Required:** CUSTOMER

**Input:** *(None)*

**Output:**
```json
{
  "applications": [
    {
      "application_id": "app-uuid",
      "company_name": "Tech Corp",
      "jd_name": "Senior Python Backend Engineer",
      "stage": "APPLIED",
      "created_at": "2024-01-01T12:00:00.000Z"
    }
  ]
}
```

---

### `PUT /api/ats/customer/applications/{application_id}/accept`
**Description:** If a company reaches out first (candidate is in `CONTACTED` stage), the candidate can accept the invite to move to the `CONSIDERED` stage.
**Role Required:** CUSTOMER

**Input (Path Parameter):** `application_id`

**Output:**
```json
{
  "message": "Request accepted. You are now being considered.",
  "stage": "CONSIDERED"
}
```

---

### `POST /api/ats/company/contact`
**Description:** Company finds a candidate via the AI Matcher and reaches out. Places the candidate in the `CONTACTED` stage.
**Role Required:** COMPANY

**Input (JSON Body):**
```json
{
  "customer_id": "candidate-uuid-here",
  "jd_id": "jd-database-id-here"
}
```

**Output:**
```json
{
  "message": "Candidate contacted successfully.",
  "application_id": "app-uuid"
}
```

---

### `GET /api/ats/board/{jd_id}`
**Description:** Returns the Kanban board data for a specific job. Automatically groups all candidates into arrays based on their current stage.
**Role Required:** COMPANY

**Input (Path Parameter):** `jd_id`

**Output:**
```json
{
  "jd_name": "Senior Python Backend Engineer",
  "board": {
    "APPLIED": [
      {
        "application_id": "app-uuid",
        "candidate_id": "candidate-uuid",
        "candidate_name": "John Doe",
        "match_score": null,
        "created_at": "2024-01-01T12:00:00.000Z"
      }
    ],
    "CONTACTED": [],
    "CONSIDERED": [],
    "INTERVIEWING": [],
    "OFFER_SENT": [],
    "HIRED": [],
    "REJECTED": [],
    "CANCELLED": []
  }
}
```

---

### `PUT /api/ats/board/{application_id}/move`
**Description:** The Company drags and drops a candidate from one stage to another (e.g., from `INTERVIEWING` to `OFFER_SENT`).
**Role Required:** COMPANY

**Input (Path Parameter):** `application_id`

**Input (JSON Body):**
```json
{
  "stage": "OFFER_SENT"
}
```

**Output:**
```json
{
  "message": "Candidate moved to OFFER_SENT.",
  "stage": "OFFER_SENT"
}
```
