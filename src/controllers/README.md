# Controllers Directory

The `controllers` directory is a central part of the application's architecture. It contains the core business logic, handling data processing, database interactions, machine learning operations (such as embeddings and skill extraction), and file management. These controllers act as intermediaries between the API routes (in the `routes` folder) and the underlying data/models, ensuring modularity and separation of concerns.

## Files and Functions

### `BaseController.py`
Provides base functionality and shared settings for other controllers.
*   **`__init__`**: (Sub-function) Initializes application settings and sets up base directory paths.
*   **`generate_random_string`**: (Sub-function) Generates a random alphanumeric string of a given length. Used in `DataController.py` to create unique file paths.

### `DataController.py`
Handles operations related to data files and uploads.
*   **`__init__`**: (Sub-function) Initializes the controller.
*   **`validate_uploaded_file`**: (Main function) Validates the uploaded file's type and size. Used in `routes/data.py` during file upload.
*   **`generate_unique_filepath`**: (Main function) Generates a unique and secure file path for saving uploaded files. Used in `routes/data.py`.
*   **`get_clean_file_name`**: (Sub-function) Cleans and normalizes the original filename. Used internally by `generate_unique_filepath`.

### `EmbeddingController.py`
Manages the generation of text embeddings using NLP models.
*   **`__init__`**: (Sub-function) Initializes the controller.
*   **`_ensure_model_loaded`**: (Sub-function) Ensures the embedding model is loaded into memory to prevent redundant loading. Used internally.
*   **`model`**: (Sub-function) Property that returns the loaded `SentenceTransformer` model. Used internally.
*   **`embed_text`**: (Main function) Generates a vector embedding for a single text string. Available for external use.
*   **`embed_texts`**: (Main function) Generates embeddings for a list of text strings. Used in `routes/nlp.py` before indexing into the vector database.

### `ExperienceController.py`
Extracts and analyzes candidate experience from text.
*   **`__init__`**: (Sub-function) Initializes the controller.
*   **`extract_required_experience`**: (Main function) Extracts the required years of experience from a job description. Used in `MatchController.py`.
*   **`_parse_month`**: (Sub-function) Parses string representations of months into integers. Used internally by `_parse_date_ranges`.
*   **`_parse_date_ranges`**: (Sub-function) Identifies and extracts date ranges from text using regex. Used internally by `extract_candidate_experience`.
*   **`_merge_overlapping_ranges`**: (Sub-function) Merges overlapping date ranges to accurately calculate total experience time. Used internally by `extract_candidate_experience`.
*   **`_calculate_total_years`**: (Sub-function) Calculates total years of experience from a list of date ranges. Used internally by `extract_candidate_experience`.
*   **`extract_candidate_experience`**: (Main function) Analyzes a candidate's text to extract their total years of experience. Used in `routes/nlp.py` and `MatchController.py`.
*   **`calculate_experience_score`**: (Main function) Computes a matching score by comparing candidate experience with required experience. Used in `MatchController.py`.

### `ExtractionController.py`
Handles NLP-based extraction of skills based on a defined taxonomy.
*   **`__init__`**: (Sub-function) Initializes the controller.
*   **`_ensure_model_loaded`**: (Sub-function) Ensures the Spacy NLP model is loaded. Used internally.
*   **`_load_taxonomy`**: (Sub-function) Loads the skills taxonomy from a JSON file. Used internally.
*   **`_flatten_taxonomy`**: (Sub-function) Flattens the hierarchical taxonomy into a single list of skills. Used internally.
*   **`_build_matcher`**: (Sub-function) Builds a Spacy `PhraseMatcher` with the given list of skills. Used internally.
*   **`_init_matcher`**: (Sub-function) Initializes the overall matcher setup. Used internally.
*   **`get_all_skills`**: (Main function) Returns a flat list of all skills in the taxonomy.
*   **`get_skills_by_track`**: (Main function) Returns a list of skills filtered by a specific career track.
*   **`get_track_names`**: (Main function) Returns a list of all available career track names.
*   **`extract_skills`**: (Main function) Extracts matched skills from text, with an optional filter list. Used in `routes/nlp.py` and `MatchController.py`.

### `JDController.py`
Manages persistent storage of Job Descriptions natively in a dedicated ChromaDB collection (`jds`).
*   **`__init__`**: (Sub-function) Initializes the controller and connects to VectorDB.
*   **`store_jd`**: (Main function) Stores a Job Description entirely in ChromaDB as a single document (text, embeddings, skills metadata).
*   **`get_jd`**: (Main function) Retrieves a stored Job Description and its metadata from ChromaDB.
*   **`list_jds`**: (Main function) Returns a list of all stored JD names with their skills and experience.
*   **`delete_jd`**: (Main function) Deletes a JD from ChromaDB.

### `LLMExtractionController.py`
Handles LLM-powered extraction of skills and metadata, acting as a smarter alternative to the taxonomy-based `ExtractionController`.
*   **`__init__`**: (Sub-function) Initializes the LLM provider.
*   **`extract_skills_from_jd`**: (Main function) Uses an LLM to dynamically extract required skills from a job description text.
*   **`extract_skills_from_cv`**: (Main function) Uses an LLM to dynamically extract candidate skills from resume chunks.

### `MatchController.py`
Orchestrates the matching of candidate resumes against job descriptions.
*   **`__init__`**: (Sub-function) Initializes dependencies, including VectorDB, Extraction, and Experience controllers.
*   **`match_candidates`**: (Main function) Compares a job description against candidates in the vector database and ranks them based on semantic similarity, skill matching, and experience. Used in `routes/nlp.py`.

### `ProcessController.py`
Responsible for reading, cleaning, and chunking text from files (PDF/DOCX).
*   **`__init__`**: (Sub-function) Initializes the controller with a specific project ID.
*   **`get_file_extension`**: (Sub-function) Determines the file extension of a given file ID. Used internally by `get_file_loader`.
*   **`get_file_loader`**: (Sub-function) Selects the appropriate file loader (PDF or DOCX). Used internally by `get_file_content`.
*   **`get_file_content`**: (Main function) Extracts the raw content from a file. Used in `routes/data.py` and `routes/nlp.py`.
*   **`clean_text`**: (Sub-function) Cleans up raw text, removing artifacts and excess whitespace. Used internally.
*   **`match_section_header`**: (Sub-function) Identifies standard resume section headers (e.g., Education, Experience). Used internally by `segment_text_into_sections`.
*   **`segment_text_into_sections`**: (Main function) Segments raw text into structured dictionaries based on matched headers. Used internally by `process_file_content`.
*   **`process_file_content`**: (Main function) Processes raw file content, segments it, and chunks it into smaller pieces for indexing. Used in `routes/data.py` and `routes/nlp.py`.

### `ProjectController.py`
Manages project directories and workspace paths.
*   **`__init__`**: (Sub-function) Initializes the controller.
*   **`get_project_path`**: (Main function) Retrieves the absolute path for a specific project directory. Used in `routes/data.py`, `ProcessController.py`, and `DataController.py`.

### `VectorDBController.py`
Handles all interactions with ChromaDB for storing and retrieving vector embeddings.
*   **`__init__`**: (Sub-function) Initializes the controller.
*   **`_get_collection`**: (Sub-function) Retrieves a specific ChromaDB collection. Used internally.
*   **`index_chunks`**: (Main function) Inserts document chunks and their embeddings into the vector database. Used in `routes/nlp.py`.
*   **`search`**: (Main function) Performs a semantic similarity search using a query embedding. Used in `MatchController.py`.
*   **`delete_by_file`**: (Main function) Removes all indexed chunks associated with a specific file. Used in `routes/nlp.py`.
*   **`delete_by_project`**: (Main function) Removes all indexed chunks associated with a specific project. Used in `routes/nlp.py`.
*   **`get_collection_count`**: (Main function) Returns the total number of items in a collection. Used in `routes/nlp.py`.

### `loaderController.py`
Provides standalone helper functions for loading different file types.
*   **`load_pdf`**: (Main function) Extracts text content from PDF files. Used in `ProcessController.py`.
*   **`load_docx`**: (Main function) Extracts text content from DOCX files. Used in `ProcessController.py`.

### `__init__.py`
*   Exports all controller classes to simplify importing them across the application (e.g., `from controllers import DataController`).
