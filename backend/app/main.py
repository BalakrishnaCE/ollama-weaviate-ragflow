from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.rag import router as rag_router
from app.api.ingest import router as ingest_router
from app.weaviate_client.client import get_client, create_schema
import os

app = FastAPI(title="Departmental AI Knowledge Graph Backend")

# Serve static files for the web UI
directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=directory), name="static")

@app.on_event("startup")
def startup_event():
    client = get_client()
    create_schema(client)

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Placeholder: include routers for ingestion, RAG, etc. in the future
app.include_router(rag_router, prefix="/rag")
app.include_router(ingest_router, prefix="/api")

if __name__ == "__main__":
    from ingestion.watcher import start_watcher
    from ingestion.docx_ingest import ingest_docx
    start_watcher(ingest_docx)
