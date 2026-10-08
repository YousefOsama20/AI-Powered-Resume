from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
import os
import shutil

from stores.db.database import get_db, engine
from models.sql_models import Base
from helpers.config import get_settings
from controllers.VectorDBController import VectorDBController, CANDIDATE_COLLECTION
from controllers.JDController import JD_COLLECTION

logger = logging.getLogger('uvicorn.error')

dev_router = APIRouter(
    prefix="/dev",
    tags=["api_v1", "Development (DANGER)"],
)

@dev_router.delete("/reset-everything")
async def reset_database(db: Session = Depends(get_db)):
    """Nuke everything: wipe ChromaDB, files, and PostgreSQL, then re-seed. | Target: Dev Only (No Auth)
    WARNING: DEVELOPMENT ONLY!
    This endpoint will completely wipe:
    1. All SQL Database Tables
    2. All ChromaDB Collections
    3. All Uploaded Physical Files
    """
    try:
        # 1. WIPE CHROMADB
        try:
            client = VectorDBController().chroma_client
            client.delete_collection(CANDIDATE_COLLECTION)
            client.delete_collection(JD_COLLECTION)
            logger.info("ChromaDB collections deleted.")
        except Exception as e:
            logger.warning(f"Error wiping ChromaDB (might already be empty): {e}")

        # 2. WIPE PHYSICAL FILES
        base_asset_path = os.path.join(os.getcwd(), "assets", "files")
        if os.path.exists(base_asset_path):
            try:
                shutil.rmtree(base_asset_path)
                logger.info(f"Deleted physical files at {base_asset_path}")
            except Exception as e:
                logger.warning(f"Error deleting physical files: {e}")

        # 3. WIPE SQL DATABASE
        # We use TRUNCATE CASCADE to empty all tables without dropping the schema
        # This preserves Alembic migrations while deleting all rows
        try:
            for table in reversed(Base.metadata.sorted_tables):
                # Skip the alembic_version table so migrations don't break
                if table.name != "alembic_version":
                    db.execute(text(f"TRUNCATE TABLE {table.name} CASCADE;"))
            db.commit()
            logger.info("PostgreSQL database truncated.")
        except Exception as e:
            db.rollback()
            logger.error(f"Error truncating SQL database: {e}")
            return JSONResponse(status_code=500, content={"message": f"Error wiping SQL: {e}"})

        # 4. RE-SEED TAXONOMY
        try:
            from scripts.seed_taxonomy import seed
            seed()
        except Exception as e:
            logger.warning(f"Could not re-seed taxonomy: {e}")

        return JSONResponse(content={"message": "System completely wiped and reset. Ready for clean testing!"})
        
    except Exception as e:
        logger.error(f"Fatal error in reset endpoint: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error."})
