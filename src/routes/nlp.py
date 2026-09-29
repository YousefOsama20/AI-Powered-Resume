from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
import logging

from controllers import ProcessController, EmbeddingController, VectorDBController, MatchController, ExtractionController, ExperienceController
from models import ResponseSignal
from .schemes.nlp import NLPIndexRequest, NLPMatchRequest

logger = logging.getLogger('uvicorn.error')

nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1", "nlp"],
)


@nlp_router.post("/index/{project_id}")
async def index_file(project_id: str, request: NLPIndexRequest):
    """
    Parse a file, embed its chunks, and store them in the Vector DB.
    """
    try:
        # 1. Parse and chunk the file
        process_controller = ProcessController(project_id=project_id)
        file_content = process_controller.get_file_content(file_id=request.file_id)
        
        if not file_content:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"signal": ResponseSignal.NO_FILES_ERROR.value}
            )

        chunks = process_controller.process_file_content(
            file_content=file_content,
            file_id=request.file_id,
            chunk_size=request.chunk_size,
            overlap_size=request.overlap_size
        )

        if not chunks:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.PROCESSING_FAILED.value}
            )

        # 2. Generate embeddings, extract skills, and extract experience
        embedding_controller = EmbeddingController()
        extraction_controller = ExtractionController()
        experience_controller = ExperienceController()
        
        texts_to_embed = []
        for chunk in chunks:
            texts_to_embed.append(chunk.page_content)
            skills = extraction_controller.extract_skills(chunk.page_content)
            chunk.metadata["skills"] = ",".join(skills)

            # Extract years of experience from Experience-section chunks
            if chunk.metadata.get("section") == "Experience":
                exp_years = experience_controller.extract_candidate_experience(chunk.page_content)
                chunk.metadata["experience_years"] = exp_years
            else:
                chunk.metadata["experience_years"] = 0.0
            
        embeddings = embedding_controller.embed_texts(texts_to_embed)

        if not embeddings or len(embeddings) != len(chunks):
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"signal": ResponseSignal.EMBEDDING_FAILED.value}
            )

        # 3. Store in VectorDB
        vectordb_controller = VectorDBController()
        success = vectordb_controller.index_chunks(
            chunks=chunks,
            embeddings=embeddings,
            collection_name=request.collection_name
        )

        if not success:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"signal": ResponseSignal.VECTORDB_INDEX_FAILED.value}
            )

        return JSONResponse(
            content={
                "signal": ResponseSignal.VECTORDB_INDEX_SUCCESS.value,
                "project_id": project_id,
                "file_id": request.file_id,
                "indexed_chunks": len(chunks),
                "collection": request.collection_name or vectordb_controller.default_collection,
                "total_in_collection": vectordb_controller.get_collection_count(request.collection_name)
            }
        )

    except Exception as e:
        logger.error(f"Error in indexing endpoint: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": ResponseSignal.VECTORDB_INDEX_FAILED.value}
        )


@nlp_router.post("/match/{project_id}")
async def match_resumes(project_id: str, request: NLPMatchRequest):
    """
    Match Job Description against all indexed candidates in a project using 
    Hybrid ATS Scoring Engine (60% Semantic / 40% Keyword).
    """
    try:
        if not request.job_description or not request.job_description.strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal":ResponseSignal.EMPTY_JOB_DESCRIPTION.value}
            )

        match_controller = MatchController()
        results = match_controller.match_candidates(
            job_description=request.job_description,
            project_id=project_id,
            top_k=request.top_k
        )

        return JSONResponse(
            content={
                "signal": ResponseSignal.MATCH_SUCCESS.value,
                "project_id": project_id,
                "results": results
            }
        )

    except Exception as e:
        logger.error(f"Error in match endpoint: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": ResponseSignal.MATCH_FAILED.value}
        )


@nlp_router.delete("/{project_id}/file/{file_id}")
async def delete_file_index(project_id: str, file_id: str):
    """
    Delete indexed chunks for a specific file in a project.
    """
    try:
        vectordb_controller = VectorDBController()
        success = vectordb_controller.delete_by_file(
            project_id=project_id,
            file_id=file_id
        )

        if not success:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"signal": ResponseSignal.VECTORDB_DELETE_FAILED.value}
            )

        return JSONResponse(
            content={
                "signal": ResponseSignal.VECTORDB_DELETE_SUCCESS.value,
                "project_id": project_id,
                "file_id": file_id
            }
        )
    except Exception as e:
        logger.error(f"Error deleting file from VectorDB: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": ResponseSignal.VECTORDB_DELETE_FAILED.value}
        )


@nlp_router.delete("/{project_id}")
async def delete_project_index(project_id: str):
    """
    Delete all indexed chunks for an entire project.
    """
    try:
        vectordb_controller = VectorDBController()
        success = vectordb_controller.delete_by_project(project_id=project_id)

        if not success:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"signal": ResponseSignal.VECTORDB_DELETE_FAILED.value}
            )

        return JSONResponse(
            content={
                "signal": ResponseSignal.VECTORDB_DELETE_SUCCESS.value,
                "project_id": project_id
            }
        )
    except Exception as e:
        logger.error(f"Error deleting project from VectorDB: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": ResponseSignal.VECTORDB_DELETE_FAILED.value}
        )
