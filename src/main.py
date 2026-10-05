from contextlib import asynccontextmanager
from fastapi import FastAPI
from routes import base, data, nlp
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
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Failed to initialize database: {e}")
    
    yield
    
    if hasattr(app, 'db_engine'):
        app.db_engine.dispose()
    if hasattr(app, 'vectordb_client'):
        app.vectordb_client.disconnect()

app = FastAPI(lifespan=lifespan)

app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
