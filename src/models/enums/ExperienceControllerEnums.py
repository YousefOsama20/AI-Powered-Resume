
import re

# ── Month name lookup ────────────────────────────────────────────────────────
MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# ── Regex patterns for JD experience requirements ────────────────────────────
# Order matters: more specific patterns first
JD_EXPERIENCE_PATTERNS = [
    # "minimum 5 years" / "minimum of 5 years"
    re.compile(
        r"minimum\s+(?:of\s+)?(\d+)\s*[\+]?\s*years?",
        re.IGNORECASE
    ),
    # "at least 5 years"
    re.compile(
        r"at\s+least\s+(\d+)\s*[\+]?\s*years?",
        re.IGNORECASE
    ),
    # "3-5 years" / "3 to 5 years" / "3 – 5 years"
    re.compile(
        r"(\d+)\s*[-–—]\s*(\d+)\s*[\+]?\s*years?",
        re.IGNORECASE
    ),
    re.compile(
        r"(\d+)\s+to\s+(\d+)\s*[\+]?\s*years?",
        re.IGNORECASE
    ),
    # "5+ years" / "5 + years"
    re.compile(
        r"(\d+)\s*\+\s*years?",
        re.IGNORECASE
    ),
    # "5 years of experience" / "5 years experience" / "5 years' experience"
    re.compile(
        r"(\d+)\s*years?\s*[''']?\s*(?:of\s+)?(?:experience|exp|work)",
        re.IGNORECASE
    ),
    # Generic "N years" near experience-related words
    re.compile(
        r"(\d+)\s*years?\s+(?:in|with|using|working|developing|managing|leading)",
        re.IGNORECASE
    ),
]

# ── Regex patterns for resume date ranges ────────────────────────────────────
# Match: "Month Year - Month Year" or "Month Year - Present"
MONTH_YEAR_PATTERN = re.compile(
    r"(?P<start_month>[A-Za-z]+)\.?\s+(?P<start_year>\d{4})"
    r"\s*[-–—]\s*"
    r"(?:(?P<end_month>[A-Za-z]+)\.?\s+(?P<end_year>\d{4})|(?P<present>present|current|now|ongoing))",
    re.IGNORECASE
)

# Match: "Year - Year" or "Year - Present"  (e.g., "2017 - 2020")
YEAR_ONLY_PATTERN = re.compile(
    r"(?<!\d)(?P<start_year>\d{4})"
    r"\s*[-–—]\s*"
    r"(?:(?P<end_year>\d{4})|(?P<present>present|current|now|ongoing))",
    re.IGNORECASE
)

# Match numeric dates: "MM/YYYY - MM/YYYY" or "DD/MM/YYYY - DD/MM/YYYY" or to "Present"
# Handles spaces around slashes, e.g., "1/11 / 2025"
NUMERIC_DATE_PATTERN = re.compile(
    r"(?:(?P<start_day>\d{1,2})\s*/\s*)?(?P<start_month>\d{1,2})\s*/\s*(?P<start_year>\d{4})"
    r"\s*[-–—]\s*"
    r"(?:(?:(?P<end_day>\d{1,2})\s*/\s*)?(?P<end_month>\d{1,2})\s*/\s*(?P<end_year>\d{4})|(?P<present>present|current|now|ongoing))",
    re.IGNORECASE
)

# Match: "Season Year - Season Year" or "Season Year - Present" (e.g. "Summer 2025 - Spring 2026")
SEASON_YEAR_PATTERN = re.compile(
    r"(?P<start_season>spring|summer|fall|autumn|winter)\s+(?P<start_year>\d{4})"
    r"\s*[-–—]\s*"
    r"(?:(?P<end_season>spring|summer|fall|autumn|winter)\s+(?P<end_year>\d{4})|(?P<present>present|current|now|ongoing))",
    re.IGNORECASE
)

# Match a single season year, like "Summer 2025" (for internships or short stints)
# Note: No \b before season because PDF parsing often mashes words (e.g., "InternSummer")
SINGLE_SEASON_PATTERN = re.compile(
    r"(?<!-)(?P<season>spring|summer|fall|autumn|winter)\s+(?P<year>\d{4})\b(?!.*(?:present|current|now|ongoing|-\s*\d{4}))",
    re.IGNORECASE
)

# ── Season mapping to starting month ─────────────────────────────────────────
SEASON_MAP = {
    "spring": 3,   # March
    "summer": 6,   # June
    "fall": 9,     # September
    "autumn": 9,   # September
    "winter": 12,  # December
}

# Match: "N years of experience" stated directly in resume summary
RESUME_STATED_EXP_PATTERN = re.compile(
    r"(\d+)\s*\+?\s*years?\s*(?:of\s+)?(?:experience|exp|professional)",
    re.IGNORECASE
)

