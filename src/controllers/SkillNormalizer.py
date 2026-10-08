"""
SkillNormalizer
───────────────
Single source of truth for skill canonicalization.

Problem it solves:
- JD extraction (LLM free-form) produces "rest apis", "http protocols",
  "linux commands", "problem-solving skills"
- CV extraction (taxonomy matcher) produces "rest api", "http", "linux"
- Old code compared with exact `lower()` equality → false misses → 7% skill match.

This module normalizes BOTH sides to the same canonical form before any
set intersection, and provides fuzzy fallback for near-misses.
"""

import re
import difflib
from typing import Dict, Iterable, List, Set, Tuple

# Canonical aliases: variant -> canonical.
# Keys AND values are post-normalization (lowercase, hyphen->space, trimmed).
ALIASES: Dict[str, str] = {
    # REST / HTTP
    "rest apis": "rest api",
    "rest api's": "rest api",
    "restful apis": "rest api",
    "restful api": "rest api",
    "rest": "rest api",
    "http protocols": "http",
    "http protocol": "http",
    "https": "http",
    # Linux
    "linux commands": "linux",
    "linux command": "linux",
    "linux administration": "linux",
    # Soft skills
    "problem-solving skills": "problem solving",
    "problem solving skills": "problem solving",
    "problem solving skill": "problem solving",
    "problem-solving skill": "problem solving",
    "teamwork skills": "teamwork",
    # Cloud
    "google cloud platform": "gcp",
    "google cloud": "gcp",
    "amazon web services": "aws",
    # DB
    "postgres": "postgresql",
    "postgress": "postgresql",
    "my sql": "mysql",
    # JS ecosystem
    "nodejs": "node.js",
    "node js": "node.js",
    "vuejs": "vue.js",
    "vue js": "vue.js",
    "nextjs": "next.js",
    "next js": "next.js",
    "expressjs": "express.js",
    "express js": "express.js",
    # Containers / misc
    "k8s": "kubernetes",
    "ci cd": "ci/cd",
    "cicd": "ci/cd",
    "scikit learn": "scikit-learn",
    "machine-learning": "machine learning",
}


def _basic_clean(raw: str) -> str:
    s = (raw or "").strip().lower()
    if not s:
        return ""
    # unify separators, keep + # . / because they matter (c++, c#, node.js, ci/cd)
    s = s.replace("_", " ").replace("-", " ")
    # strip quotes / trailing punctuation
    s = s.strip("\"'“”‘’.,;:!?()[]{}")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _singularize_phrase(phrase: str) -> str:
    """Singularize only the last word to fix 'rest apis' -> 'rest api'.

    Conservative: only touches the final token, skips short words and
    words ending in 'ss' (e.g. 'glass') or 'us' (e.g. 'status').
    """
    parts = phrase.split(" ")
    if not parts:
        return phrase
    last = parts[-1]
    if len(last) <= 3 or last.endswith("ss") or last.endswith("us"):
        return phrase
    singular = last
    if last.endswith("ies") and len(last) > 4:
        singular = last[:-3] + "y"
    elif last.endswith(("ses", "xes", "zes", "ches", "shes")) and len(last) > 4:
        # 'addresses' -> 'address', 'branches' -> 'branch'
        if last.endswith(("ches", "shes")):
            singular = last[:-2]
        else:
            singular = last[:-2] if last.endswith("es") else last
            # 'boxes' -> 'box': strip 'es'
            if last.endswith(("ses", "xes", "zes")):
                singular = last[:-2]
    elif last.endswith("s") and not last.endswith("ss"):
        singular = last[:-1]
    if singular != last:
        parts[-1] = singular
        return " ".join(parts)
    return phrase


def normalize_skill(raw: str) -> str:
    """Normalize a single skill string to canonical form."""
    s = _basic_clean(raw)
    if not s:
        return ""
    # strip generic trailing 'skill(s)' suffix: 'problem solving skills' -> 'problem solving'
    s = re.sub(r"\s+skills?$", "", s).strip()
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return ""
    # alias lookup on the cleaned form
    if s in ALIASES:
        return ALIASES[s]
    # singularize last token, then re-check aliases
    sing = _singularize_phrase(s)
    if sing in ALIASES:
        return ALIASES[sing]
    return sing


def normalize_skill_list(items: Iterable[str] | None) -> List[str]:
    """Normalize, dedupe (preserve order), drop empties."""
    seen: Set[str] = set()
    out: List[str] = []
    for raw in items or []:
        if not isinstance(raw, str):
            continue
        v = normalize_skill(raw)
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def normalize_classified(skills: Dict | None) -> Dict[str, List[str]]:
    """Normalize {'essential': [...], 'elective': [...]} + elective≠essential."""
    skills = skills or {}
    essential = normalize_skill_list(skills.get("essential", []))
    elective = normalize_skill_list(skills.get("elective", []))
    essential_set = set(essential)
    elective = [s for s in elective if s not in essential_set]
    return {"essential": essential, "elective": elective}


def _fuzzy_hit(need: str, have: Set[str], threshold: float = 0.88) -> str | None:
    """Return best fuzzy hit from `have` for `need`, or None.

    Uses difflib (stdlib, no new dependency). Threshold 0.88 catches
    'problem solving' vs 'problem-solving', 'postgres' vs 'postgresql'
    leftovers without merging unrelated skills ('java' vs 'javascript' = 0.66).
    """
    best: str | None = None
    best_score = 0.0
    for h in have:
        if abs(len(h) - len(need)) > 4:
            # still allow, but skip obvious length mismatches for speed
            # e.g. 'go' vs 'google cloud platform'
            if max(len(h), len(need)) > 0 and abs(len(h) - len(need)) / max(len(h), len(need)) > 0.6:
                continue
        score = difflib.SequenceMatcher(None, need, h).ratio()
        if score > best_score:
            best_score = score
            best = h
    if best is not None and best_score >= threshold:
        return best
    return None


def match_skills(
    candidate_skills: Iterable[str] | None,
    required_skills: Iterable[str] | None,
    fuzzy_threshold: float = 0.88,
) -> Tuple[List[str], List[str], Dict[str, str]]:
    """Match required skills against candidate skills (both normalized first).

    Returns (matched, missing, alias_map) where matched/missing contain the
    REQUIRED skill names, and alias_map maps required -> actual candidate string
    that satisfied it (exact or fuzzy).
    """
    req = normalize_skill_list(required_skills)
    cand_raw = list(candidate_skills or [])
    # candidate may already be normalized; normalizing again is idempotent
    cand_norm = normalize_skill_list(cand_raw)
    cand_set = set(cand_norm)

    matched: List[str] = []
    missing: List[str] = []
    mapping: Dict[str, str] = {}
    for r in req:
        if r in cand_set:
            matched.append(r)
            mapping[r] = r
        else:
            hit = _fuzzy_hit(r, cand_set, threshold=fuzzy_threshold)
            if hit:
                matched.append(r)
                mapping[r] = hit
            else:
                missing.append(r)
    return matched, missing, mapping


def score_from_matches(
    essential_matched: List[str],
    essential_total: int,
    elective_matched: List[str],
    elective_total: int,
) -> Tuple[float, float, float]:
    """Shared 75/25 + strict-mode scoring used by both match directions."""
    if essential_total:
        essential_score = len(essential_matched) / essential_total
    else:
        essential_score = 1.0
    if elective_total:
        elective_score = len(elective_matched) / elective_total
    else:
        elective_score = 0.0
    if essential_total and elective_total:
        if essential_score < 0.5:
            keyword_score = essential_score
        else:
            keyword_score = (essential_score * 0.75) + (elective_score * 0.25)
    elif essential_total:
        keyword_score = essential_score
    else:
        keyword_score = 0.0
    return keyword_score, essential_score, elective_score
