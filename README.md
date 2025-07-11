# Weavite RAGFlow: Production-Grade RAG System

## Overview
Weavite RAGFlow is a robust Retrieval-Augmented Generation (RAG) pipeline for enterprise knowledge management. It leverages FastAPI, Weaviate (v4.x), Ollama/OpenAI for LLM and embeddings, and a knowledge base of DOCX-based Standard Operating Procedures (SOPs). The system supports advanced retrieval, agentic multi-hop reasoning, LLM-based reranking, automated evaluation, and user feedback collection.

---

## Features
- **DOCX SOP Ingestion**: Batch and real-time ingestion of DOCX files, chunked and indexed in Weaviate.
- **Hybrid Retrieval**: Vector + keyword search with synonym expansion and fallback logic.
- **Agentic RAG**: Multi-step reasoning, tool-calling (SEARCH, SUMMARIZE, FINAL_ANSWER, etc.), and context synthesis.
- **LLM Reranking**: LLM rates and reranks retrieved chunks for relevance.
- **Automated Evaluation**: RAGAS-based faithfulness, context relevance, and completeness metrics.
- **User Feedback**: Collects and stores feedback and evaluation logs (admin endpoints for review/download).
- **Frontend Ready**: API supports agentic queries, context/reasoning display, and feedback collection.

---

## Architecture
- **FastAPI**: REST API backend
- **Weaviate (v4.x)**: Vector database for chunked SOP storage and retrieval
- **Ollama/OpenAI**: LLM and embedding provider (configurable)
- **SQLite**: Feedback and evaluation log storage
- **Frontend**: (Optional) Static HTML/JS client for user interaction

---

## Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/BalakrishnaCE/weavite_ragflow.git
cd weavite_ragflow
```

### 2. Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Start Weaviate (Docker)
```bash
cd backend
# Edit docker-compose.yml if needed
sudo docker-compose up -d
```

### 4. Start Ollama (if using Ollama for embeddings/LLM)
```bash
ollama serve &
# Make sure the model (e.g., mxbai-embed-large, llama3) is available in Ollama
```

### 5. Set Environment Variables
Create a `.env` file in `backend/` (or set in your environment):
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OLLAMA_URL=http://localhost:11434
EMBED_MODEL=mxbai-embed-large
LLM_MODEL=llama3
WEAVIATE_URL=http://localhost:8080
```

---

## Ingestion

### Batch Ingestion (all DOCX files)
```bash
PYTHONPATH=backend python3 backend/app/ingestion/batch_ingest.py
```

### Real-Time Ingestion (watch for new/changed DOCX files)
```bash
PYTHONPATH=backend python3 backend/app/main.py
# Or run the watcher directly
PYTHONPATH=backend python3 backend/app/ingestion/watcher.py
```

### API Ingestion (upload via API)
POST `/api/ingest` with a DOCX file.

---

## Running the Backend

### Start FastAPI Server
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Access the API at: `http://localhost:8000`
- Static frontend (if present): `http://localhost:8000/static/`

---

## Key API Endpoints

- `POST /rag/query` — Standard RAG query (hybrid retrieval, reranking, answer, context, evaluation)
- `POST /rag/agentic_query` — Agentic/multi-hop RAG (stepwise reasoning, tool-calling, context synthesis)
- `POST /rag/feedback` — Submit user feedback (question, answer, context, rating, comments)
- `GET /rag/admin/feedback` — View feedback logs (admin)
- `GET /rag/admin/feedback/csv` — Download feedback as CSV
- `GET /rag/admin/evaluation` — View evaluation logs (admin)
- `GET /rag/admin/evaluation/csv` — Download evaluation as CSV
- `POST /rag/evaluate` — Run RAGAS evaluation on a Q/A/context triple
- `POST /api/ingest` — Ingest a DOCX file via API

See `backend/app/Docs/api_examples.md` for example usage (cURL, Python).

---

## Evaluation & Feedback
- **Automated**: RAGAS metrics (faithfulness, context relevance, completeness) are logged for each query.
- **Manual**: Users can submit feedback on answers, which is stored in SQLite and available via admin endpoints.

---

## Troubleshooting
- **Ollama not running**: Start with `ollama serve`.
- **Weaviate connection errors**: Ensure Docker container is running and accessible.
- **API key errors**: Set `OPENAI_API_KEY` in your environment or `.env` file.
- **Schema errors**: The backend auto-creates collections on startup.
- **Push protection**: Never commit secrets; use environment variables only.

---

## Contributing
- Fork, branch, and submit PRs for improvements or bugfixes.
- Please do not commit API keys or secrets.

---

## License
MIT License. See `LICENSE` file. 