# Models Directory

## Overall Explanation
The `models` folder contains the data structures, enumerations, and constants used across the AI-powered resume project. By centralizing these definitions, the project avoids "magic strings" and ensures consistency when handling standard responses, resume sections, file types, taxonomy classifications, and experience parsing logic.

## File Details

### `__init__.py`
- **What it does**: Exposes the nested enumerations and constants directly from the `models` package for easier imports.
- **Component type**: Helper.
- **Where it is used**: Automatically invoked when importing from `models` throughout the application (e.g., `routes/nlp.py`, `controllers/ExperienceController.py`).

### `enums/__init__.py`
- **What it does**: Aggregates the various enumerations defined within the `enums` directory, passing them up to the parent package.
- **Component type**: Helper.
- **Where it is used**: Automatically invoked when referencing the `models.enums` module (e.g., in `controllers/ExtractionController.py`).

### `enums/ProcessingEnum.py`
- **`ProcessingEnum`** (Enum):
  - **What it does**: Defines the supported file extensions for resume processing (e.g., `.pdf` and `.docx`).
  - **Component type**: Main component.
  - **Where it is used**: Used in `src/controllers/ProcessController.py` to verify file extensions and route files to their respective parsers.

### `enums/ResponseEnums.py`
- **`ResponseSignal`** (Enum):
  - **What it does**: Defines standard response signal strings for application events (e.g., file validation, upload status, embedding status, vectordb operations).
  - **Component type**: Main component.
  - **Where it is used**: Used extensively in API routes to standardize responses, specifically in `src/routes/data.py` and `src/routes/nlp.py`.

### `enums/ResumeSectionEnum.py`
- **`ResumeSectionEnum`** (Enum):
  - **What it does**: Defines the canonical names for recognized resume sections (e.g., Technical Skills, Experience, Education).
  - **Component type**: Main component.
  - **Where it is used**: Used in `src/controllers/ProcessController.py` to identify current parsing sections and in `src/controllers/VectorDBController.py` to filter searches by resume section.
- **`SECTION_PATTERNS`** (Dictionary):
  - **What it does**: Maps each `ResumeSectionEnum` to a compiled regular expression used to detect section headers in resume text.
  - **Component type**: Main component.
  - **Where it is used**: Used in `src/controllers/ProcessController.py` to segment and structure the extracted resume text.

### `enums/TaxonomyDefaultEnums.py`
- **`DefaultTaxonomy`** (Dictionary):
  - **What it does**: Provides a comprehensive default taxonomy (keyword/skill lists) categorized by industry fields (e.g., software engineering, finance, healthcare, legal).
  - **Component type**: Main component.
  - **Where it is used**: Used in `src/controllers/ExtractionController.py` as a predefined taxonomy structure when classifying or extracting skills.

### `enums/ExperienceControllerEnums.py`
This file contains several constants and regex patterns tailored for calculating work experience. 
- **`MONTH_MAP`** (Dictionary): Maps month string abbreviations to their integer representations.
- **`SEASON_MAP`** (Dictionary): Maps seasons to start month integers (e.g., "spring" to 3).
- **`JD_EXPERIENCE_PATTERNS`** (List): Ordered list of regex patterns to extract required experience years from job descriptions.
- **`MONTH_YEAR_PATTERN`, `YEAR_ONLY_PATTERN`, `NUMERIC_DATE_PATTERN`, `SEASON_YEAR_PATTERN`, `SINGLE_SEASON_PATTERN`** (Regex): Patterns for parsing different date range formats from resume texts.
- **`RESUME_STATED_EXP_PATTERN`** (Regex): Regex pattern to capture explicit statements of experience years (e.g., "5+ years of experience") from a resume summary.
- **Component type**: Helper constants.
- **Where it is used**: Used throughout `src/controllers/ExperienceController.py` to parse dates, extract job description requirements, and calculate cumulative work experience from parsed resumes.
