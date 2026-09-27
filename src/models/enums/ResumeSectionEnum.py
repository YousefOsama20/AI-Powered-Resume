from enum import Enum
import re


class ResumeSectionEnum(Enum):
    TECHNICAL_SKILLS = "Technical Skills"
    EXPERIENCE = "Experience"
    EDUCATION = "Education"
    PROJECTS = "Projects"
    CERTIFICATIONS = "Certifications"
    SUMMARY = "Summary"


# Canonical section definitions with regex patterns
SECTION_PATTERNS = {
    ResumeSectionEnum.TECHNICAL_SKILLS.value: re.compile(
        r"^\s*(?:technical\s+skills|skills\s*(?:&|and)?\s*competencies|tech\s+stack|core\s+competencies|programming\s+languages|skills|technologies|tools)\s*[:\-]?\s*$",
        re.IGNORECASE,
    ),
    ResumeSectionEnum.EXPERIENCE.value: re.compile(
        r"^\s*(?:work\s+experience|professional\s+experience|experience|employment\s+history|work\s+history|internships?)\s*[:\-]?\s*$",
        re.IGNORECASE,
    ),
    ResumeSectionEnum.EDUCATION.value: re.compile(
        r"^\s*(?:education|academic\s+background|academics|qualifications|degrees?)\s*[:\-]?\s*$",
        re.IGNORECASE,
    ),
    ResumeSectionEnum.PROJECTS.value: re.compile(
        r"^\s*(?:projects|personal\s+projects|academic\s+projects|key\s+projects)\s*[:\-]?\s*$",
        re.IGNORECASE,
    ),
    ResumeSectionEnum.CERTIFICATIONS.value: re.compile(
        r"^\s*(?:certifications?|certificates?|licenses(?:\s*(?:&|and)\s*certifications)?|courses|credentials)\s*[:\-]?\s*$",
        re.IGNORECASE,
    ),
    ResumeSectionEnum.SUMMARY.value: re.compile(
        r"^\s*(?:professional\s+summary|summary|profile|about\s+me|objective|career\s+objective)\s*[:\-]?\s*$",
        re.IGNORECASE,
    ),
}
