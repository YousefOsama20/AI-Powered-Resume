from contextlib import asynccontextmanager
from fastapi import FastAPI
from routes import base, data, nlp, auth, ats, profile, dev
from stores.llm.LLMProviderFactory import LLMProviderFactory
from helpers.config import get_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    llm_provider_factory = LLMProviderFactory(settings)

    # generation client
    app.generation_client = llm_provider_factory.create(provider=settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)
    
    # Initialize Database Tables
    try:
        from stores.db.database import engine
        from models.sql_models import Base
        # Base.metadata.create_all(bind=engine) # Now managed by Alembic
    except Exception as e:
        print(f"Failed to initialize database: {e}")
    
    yield
    
    if hasattr(app, 'db_engine'):
        app.db_engine.dispose()
    if hasattr(app, 'vectordb_client'):
        app.vectordb_client.disconnect()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)
app.include_router(auth.auth_router)
app.include_router(ats.ats_router)
app.include_router(profile.profile_router)
app.include_router(dev.dev_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
