from enum import Enum


class ResponseSignal(Enum):

    # ── File signals ──────────────────────────────────────────────────────────
    FILE_VALIDATED_SUCCESS = "file_validate_successfully"
    FILE_TYPE_NOT_SUPPORTED = "file_type_not_supported"
    FILE_SIZE_EXCEEDED = "file_size_exceeded"
    FILE_UPLOAD_SUCCESS = "file_upload_success"
    FILE_UPLOAD_FAILED = "file_upload_failed"

    # ── Processing signals ────────────────────────────────────────────────────
    PROCESSING_SUCCESS = "processing_success"
    PROCESSING_FAILED = "processing_failed"
    NO_FILES_ERROR = "not_found_files"
    FILE_ID_ERROR = "no_file_found_with_this_id"

    # ── Embedding signals ─────────────────────────────────────────────────────
    EMBEDDING_SUCCESS = "embedding_success"
    EMBEDDING_FAILED = "embedding_failed"

    # ── VectorDB signals ──────────────────────────────────────────────────────
    VECTORDB_INDEX_SUCCESS = "vectordb_index_success"
    VECTORDB_INDEX_FAILED = "vectordb_index_failed"
    VECTORDB_SEARCH_SUCCESS = "vectordb_search_success"
    VECTORDB_SEARCH_FAILED = "vectordb_search_failed"
    VECTORDB_DELETE_SUCCESS = "vectordb_delete_success"
    VECTORDB_DELETE_FAILED = "vectordb_delete_failed"
