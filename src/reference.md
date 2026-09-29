# Skills Taxonomy Reference

## Overview

The AI-Powered Resume system uses a **universal skills taxonomy** that covers all major career tracks. During **indexing**, all 763 skills are used to extract every possible skill from resumes. During **matching**, only skills mentioned in the job description are compared — making the system flexible enough to support any career track.

## Supported Career Tracks

| Track | Skills Count | Examples |
|-------|:------------:|---------|
| Software Engineering | 84 | Python, React, FastAPI, Docker, Kubernetes, SQL, Git |
| Data Science & Analytics | 83 | Machine Learning, PyTorch, Pandas, Tableau, LLM, RAG |
| DevOps & Cloud | 68 | AWS, GCP, Azure, Terraform, CI/CD, Prometheus, Helm |
| Mechanical & Electrical Eng. | 67 | AutoCAD, SolidWorks, ANSYS, PLC, MATLAB, Robotics |
| Finance & Accounting | 65 | Financial Modeling, GAAP, Bloomberg Terminal, SAP, DCF |
| Marketing & Growth | 60 | SEO, Google Analytics, HubSpot, Content Marketing, PPC |
| Healthcare | 59 | EHR, HIPAA, Medical Coding, Epic, Telemedicine |
| Human Resources | 54 | Recruiting, ATS, Workday, Performance Management, DEI |
| Project Management | 53 | Agile, Scrum, Jira, PMP, Risk Management, Six Sigma |
| Legal | 53 | Contract Management, eDiscovery, GDPR, IP, Compliance |
| Sales | 53 | Salesforce, Lead Generation, Negotiation, SaaS Sales |
| Cybersecurity | 51 | Penetration Testing, SIEM, Zero Trust, OWASP, SOC 2 |
| Design & UX | 45 | Figma, Adobe XD, Wireframing, User Research, WCAG |
| **Total** | **763 unique** | |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  skills-taxonomy.json                        │
│  Categorized dict: { track_name: [skill1, skill2, ...] }    │
│  13 tracks → 763 unique skills (flattened for matching)     │
└───────────────────────────┬─────────────────────────────────┘
                            │
              ┌─────────────┴──────────────┐
              │     ExtractionController    │
              │                             │
              │  extract_skills(text)        │  ← Full taxonomy (indexing)
              │  extract_skills(text,        │  ← JD-filtered (matching)
              │    filter_skills=[...])      │
              └─────────────┬──────────────┘
                            │
          ┌─────────────────┴─────────────────┐
          │                                     │
   ┌──────┴──────┐                     ┌───────┴───────┐
   │  Indexing    │                     │  Matching     │
   │  (nlp.py)   │                     │  (MatchCtrl)  │
   │             │                     │               │
   │  All skills │                     │  JD skills vs │
   │  extracted  │                     │  candidate    │
   │  per chunk  │                     │  skills via   │
   │             │                     │  Jaccard      │
   └─────────────┘                     └───────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `src/assets/taxonomy/skills-taxonomy.json` | Categorized skill definitions (13 tracks) |
| `src/controllers/ExtractionController.py` | spaCy-based skill extraction with full/filtered modes |
| `src/controllers/MatchController.py` | Hybrid ranking: 60% Semantic + 40% Keyword (Jaccard) |
| `src/routes/nlp.py` | API endpoints for indexing and matching |

## ExtractionController API

| Method | Description |
|--------|-------------|
| `extract_skills(text)` | Extract all matching skills using full taxonomy |
| `extract_skills(text, filter_skills=[...])` | Extract only specified skills from text |
| `get_all_skills()` | Returns flat list of all 763 skills |
| `get_skills_by_track(track_name)` | Returns skills for a specific track |
| `get_track_names()` | Returns list of all 13 track names |

## How Matching Works

1. **Indexing** — Resumes are parsed, chunked, and each chunk is matched against the **full 763-skill taxonomy**. Extracted skills are stored in vector DB metadata.
2. **Matching** — A job description is received. Skills are extracted from the JD using the full taxonomy. The Jaccard Index compares JD skills vs candidate skills. Combined with semantic similarity (60/40 weighting) for the final hybrid score.

## Adding New Skills

Edit `src/assets/taxonomy/skills-taxonomy.json`:

```json
{
    "your_new_track": [
        "skill one",
        "skill two",
        "skill three"
    ]
}
```

After adding skills, **re-index existing resumes** to capture the new skills.

## Backward Compatibility

The system supports both formats:
- **Categorized dict** (new): `{ "track": ["skill1", "skill2"] }`
- **Flat list** (legacy): `["skill1", "skill2"]`
