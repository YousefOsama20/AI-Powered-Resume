"""
ExperienceController
────────────────────
Extracts years-of-experience requirements from job descriptions
and calculates candidate experience from resume date ranges.
Uses pure regex — no extra dependencies needed.
"""
import logging
from datetime import datetime, date
from typing import Optional, List, Tuple

from models import (MONTH_MAP, JD_EXPERIENCE_PATTERNS, MONTH_YEAR_PATTERN, YEAR_ONLY_PATTERN,
                    NUMERIC_DATE_PATTERN, SEASON_YEAR_PATTERN, SINGLE_SEASON_PATTERN, 
                    SEASON_MAP, RESUME_STATED_EXP_PATTERN)

from .BaseController import BaseController

logger = logging.getLogger("uvicorn.error")

class ExperienceController(BaseController):
    """
    Extracts and compares years of experience between
    job descriptions and candidate resumes.
    """

    def __init__(self):
        # Type: Sub-function
        super().__init__()

    # ──────────────────────────────────────────────────────────────────────────
    # JD Experience Extraction
    # ──────────────────────────────────────────────────────────────────────────

    def extract_required_experience(self, text: str) -> Optional[float]:
        # Parse required years of experience from a JD text. | Company (JD parsing)
        # Type: Main function
        """
        Extracts the required years of experience from a job description.

        Returns:
            The required years as a float, or None if no requirement found.
            For ranges (e.g., "3-5 years"), returns the minimum.
            If multiple distinct requirements found, returns the maximum.
        """
        if not text:
            return None

        found_values = []
        matched_spans = []  # Track spans to avoid double-counting

        for pattern in JD_EXPERIENCE_PATTERNS:
            for match in pattern.finditer(text):
                # Skip if this overlaps with an already-matched span
                # (earlier patterns have higher priority)
                span = match.span()
                if any(s <= span[0] < e or s < span[1] <= e for s, e in matched_spans):
                    continue

                groups = match.groups()
                try:
                    if len(groups) == 2 and groups[1] is not None:
                        # Range pattern (e.g., "3-5 years"): take the minimum
                        val = float(groups[0])
                    else:
                        val = float(groups[0])

                    if 0 < val <= 50:  # Sanity check
                        found_values.append(val)
                        matched_spans.append(span)
                except (ValueError, IndexError):
                    continue
        if not found_values:
            return None

        # Return the maximum requirement found in the JD
        result = max(found_values)
        logger.info(f"[ExperienceController] JD required experience: {result} years")
        return result

    # ──────────────────────────────────────────────────────────────────────────
    # Resume Experience Extraction
    # ──────────────────────────────────────────────────────────────────────────

    def _parse_month(self, month_str: str) -> Optional[int]:
        # Convert month name string to month number. | Internal helper
        # Type: Sub-function
        """Converts a month name/abbreviation to a month number."""
        return MONTH_MAP.get(month_str.lower().rstrip("."))

    def _parse_date_ranges(self, text: str) -> List[Tuple[date, date]]:
        # Extract work date ranges (e.g. Jan 2020 - Dec 2022) from CV text. | Internal helper
        # Type: Sub-function
        """
        Extracts all employment date ranges from resume text.
        Returns a list of (start_date, end_date) tuples.
        """
        today = date.today()
        ranges = []

        # 1. Try Numeric Date Patterns (e.g. 01/2020 - 12/2021)
        for match in NUMERIC_DATE_PATTERN.finditer(text):
            try:
                start_month = int(match.group("start_month"))
                start_year = int(match.group("start_year"))

                if start_month < 1 or start_month > 12 or start_year < 1970 or start_year > today.year + 1:
                    continue

                start = date(start_year, start_month, 1)

                if match.group("present"):
                    end = today
                else:
                    end_month = int(match.group("end_month"))
                    end_year = int(match.group("end_year"))
                    
                    if end_month < 1 or end_month > 12 or end_year < 1970 or end_year > today.year + 1:
                        continue
                    
                    end = date(end_year, end_month, 1)

                if end >= start:
                    ranges.append((start, end))
            except (ValueError, TypeError):
                continue

        # 2. Try Month-Year patterns (more precise)
        for match in MONTH_YEAR_PATTERN.finditer(text):
            try:
                start_month = self._parse_month(match.group("start_month"))
                start_year = int(match.group("start_year"))

                if not start_month or start_year < 1970 or start_year > today.year + 1:
                    continue

                start = date(start_year, start_month, 1)

                if match.group("present"):
                    end = today
                else:
                    end_month = self._parse_month(match.group("end_month"))
                    end_year = int(match.group("end_year"))
                    if not end_month or end_year < 1970 or end_year > today.year + 1:
                        continue
                    end = date(end_year, end_month, 1)

                if end >= start:
                    ranges.append((start, end))
            except (ValueError, TypeError):
                continue

        # 3. Try Seasonal patterns (e.g. Summer 2025 - Spring 2026)
        for match in SEASON_YEAR_PATTERN.finditer(text):
            try:
                start_season = match.group("start_season").lower()
                start_month = SEASON_MAP.get(start_season)
                start_year = int(match.group("start_year"))

                if not start_month or start_year < 1970 or start_year > today.year + 1:
                    continue

                start = date(start_year, start_month, 1)

                if match.group("present"):
                    end = today
                else:
                    end_season = match.group("end_season").lower()
                    end_month = SEASON_MAP.get(end_season)
                    end_year = int(match.group("end_year"))
                    if not end_month or end_year < 1970 or end_year > today.year + 1:
                        continue
                    end = date(end_year, end_month, 1)

                if end >= start:
                    ranges.append((start, end))
            except (ValueError, TypeError):
                continue

        # 4. Try Single Season pattern (e.g. Summer 2025)
        for match in SINGLE_SEASON_PATTERN.finditer(text):
            try:
                season = match.group("season").lower()
                month = SEASON_MAP.get(season)
                year = int(match.group("year"))

                if not month or year < 1970 or year > today.year + 1:
                    continue

                start = date(year, month, 1)
                
                # A single season usually lasts about 3 months, so we just add 2 months to the start month
                end_month = month + 2
                end_year = year
                if end_month > 12:
                    end_month -= 12
                    end_year += 1
                
                end = date(end_year, end_month, 1)
                
                ranges.append((start, end))
            except (ValueError, TypeError):
                continue

        # 5. If no specific ranges found so far, try Year-only patterns
        if not ranges:
            for match in YEAR_ONLY_PATTERN.finditer(text):
                try:
                    start_year = int(match.group("start_year"))

                    if start_year < 1970 or start_year > today.year + 1:
                        continue

                    start = date(start_year, 1, 1)

                    if match.group("present"):
                        end = today
                    else:
                        end_year = int(match.group("end_year"))
                        if end_year < 1970 or end_year > today.year + 1:
                            continue
                        end = date(end_year, 12, 31)

                    if end >= start:
                        ranges.append((start, end))
                except (ValueError, TypeError):
                    continue

        return ranges

    def _merge_overlapping_ranges(self, ranges: List[Tuple[date, date]]) -> List[Tuple[date, date]]:
        # Merge overlapping date ranges to avoid double-counting experience. | Internal helper
        # Type: Sub-function
        """Merges overlapping date ranges to avoid double-counting."""
        if not ranges:
            return []

        # Sort by start date
        sorted_ranges = sorted(ranges, key=lambda r: r[0])
        merged = [sorted_ranges[0]]

        for current_start, current_end in sorted_ranges[1:]:
            last_start, last_end = merged[-1]

            if current_start <= last_end:
                # Overlapping — extend the end if needed
                merged[-1] = (last_start, max(last_end, current_end))
            else:
                merged.append((current_start, current_end))

        return merged

    def _calculate_total_years(self, ranges: List[Tuple[date, date]]) -> float:
        # Sum total years from a list of non-overlapping date ranges. | Internal helper
        # Type: Sub-function
        """Calculates total years from a list of non-overlapping date ranges."""
        total_days = 0
        for start, end in ranges:
            total_days += (end - start).days

        return round(total_days / 365.25, 1)

    def extract_candidate_experience(self, text: str) -> float:
        # Extract total years of work experience from a CV. | Customer (CV parsing)
        # Type: Main function
        """
        Extracts total years of experience from resume text.

        Strategy:
        1. Parse all date ranges from the text
        2. Merge overlapping periods
        3. Calculate total non-overlapping years

        Returns:
            Total years of experience as a float (rounded to 1 decimal).
            Returns 0.0 if no dates can be parsed.
        """
        if not text:
            return 0.0

        # Parse date ranges
        ranges = self._parse_date_ranges(text)

        if ranges:
            merged = self._merge_overlapping_ranges(ranges)
            total = self._calculate_total_years(merged)
            return total

        # Fallback: check for explicitly stated experience
        # e.g., "10+ years of professional experience"
        for match in RESUME_STATED_EXP_PATTERN.finditer(text):
            try:
                val = float(match.group(1))
                if 0 < val <= 50:
                    return val
            except (ValueError, IndexError):
                continue

        return 0.0

    # ──────────────────────────────────────────────────────────────────────────
    # Experience Scoring
    # ──────────────────────────────────────────────────────────────────────────

    def calculate_experience_score(self,required: Optional[float],candidate: float) -> float:
        # Score candidate experience vs JD requirement (0-100). | Company (matching)
        # Type: Main function
        """
        Calculates an experience score between 0.0 and 1.0.

        - required is None     → 1.0 (no requirement stated in JD)
        - candidate >= required → 1.0 (meets or exceeds)
        - candidate >= 70% req → 0.5–1.0 (close, partial credit via linear scale)
        - candidate < 70% req  → 0.0–0.5 (significant gap via linear scale)
        """
        if required is None or required <= 0:
            return 1.0

        if candidate >= required:
            return 1.0

        # Linear scale from 0.0 to 1.0
        ratio = candidate / required
        return round(min(max(ratio, 0.0), 1.0), 3)
