import sys
import os
import tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from fastapi.testclient import TestClient
from app.main import app
import pytest
from docx import Document

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_ingest(monkeypatch):
    # Mock the actual ingestion logic to avoid real DOCX/Weaviate/Ollama calls
    monkeypatch.setattr("app.ingestion.docx_ingest.ingest_docx", lambda x: None)
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        doc = Document()
        doc.add_paragraph("Test content")
        doc.save(tmp.name)
        tmp.seek(0)
        files = {"file": ("test.docx", tmp.read(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    response = client.post("/api/ingest", files=files)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    os.unlink(tmp.name)

def test_rag_query(monkeypatch):
    # Mock embedding and LLM completion
    monkeypatch.setattr("app.ollama.client.get_embedding", lambda x: [0.1]*384)
    monkeypatch.setattr("app.ollama.client.get_llm_completion", lambda x: "Mocked answer")
    # Mock Weaviate client
    class DummyQuery:
        def with_near_vector(self, *a, **kw): return self
        def with_limit(self, *a, **kw): return self
        def with_where(self, *a, **kw): return self
        def do(self):
            return {"data": {"Get": {"Section": [{"title": "Sec1", "content": "Some content", "sop": "SOP1"}]}}}
    class DummyClient:
        def __init__(self):
            self.query = self
        def get(self, *a, **kw): return DummyQuery()
    monkeypatch.setattr("app.weaviate_client.client.get_client", lambda: DummyClient())
    req = {"question": "What is SOP1?"}
    response = client.post("/rag/query", json=req)
    assert response.status_code == 200
    assert "answer" in response.json()
    assert response.json()["answer"] == "Mocked answer" 