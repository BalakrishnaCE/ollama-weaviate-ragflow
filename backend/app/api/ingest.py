from fastapi import APIRouter, UploadFile, File
from app.ingestion.docx_ingest import ingest_docx
import tempfile
from app.weaviate_client.client import get_client

router = APIRouter()

@router.post("/ingest")
def ingest_docx_api(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name
    ingest_docx(tmp_path)
    return {"status": "success", "filename": file.filename} 