# Departmental AI Knowledge Graph Backend

## Overview
This backend provides a real-time, multi-layered Retrieval-Augmented Generation (RAG) pipeline and knowledge graph for department-wise SOPs and documents. It is designed to power AI applications (Q&A, LMS, analytics, etc.) by enabling context-aware, department-specific answers using local vector search (Weaviate) and LLMs (Ollama).

## Features
- **Real-time ingestion**: Watches the `Docs/` folder for new/changed files and auto-ingests them.
- **Multi-format support**: Modular ingestion pipeline (starts with DOCX, extensible to PDF, Excel, etc.).
- **Knowledge graph**: Departments, SOPs, and sections as nodes; relationships for context and analytics.
- **Multi-layered RAG**: Filters by department/section, vector search, graph expansion, and LLM answer synthesis.
- **API-first**: FastAPI backend with endpoints for ingestion, querying, and RAG answers.
- **Extensible**: Designed for future apps (LMS, Q&A, analytics) and new document types/models.

## Architecture
```mermaid
graph TD
  A[Docs/ Folder] -- File Watcher --> B[Ingestion Pipeline]
  B -- Parse/Chunk/Embed --> C[Weaviate (Vector + Graph)]
  C -- Vector Search & Graph Query --> D[RAG Pipeline]
  D -- Context --> E[Ollama LLM]
  E -- Answer --> F[Backend API]
  F -- Serve --> G[Frontend Apps (LMS, Q&A, etc.)]
```

## Folder Structure
```
backend/
  app/
    api/                # FastAPI endpoints
    ingestion/          # File watcher, parsers, chunkers
    rag/                # RAG pipeline logic
    weaviate/           # Weaviate client, schema, graph utils
    ollama/             # Ollama client integration
    models/             # Pydantic models, schemas
    config.py
    main.py             # FastAPI entrypoint
  tests/
  requirements.txt
  README.md
```

## Setup Instructions
1. **Install dependencies**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Start Weaviate**
   - [Install Weaviate locally](https://weaviate.io/developers/weaviate/installation/docker-compose) (Docker recommended)
   - Configure Weaviate connection in `app/config.py`
3. **Start Ollama**
   - [Install Ollama](https://ollama.com/download)
   - Start your preferred embedding and LLM models (e.g., `ollama run nomic-embed-text`, `ollama run llama3`)
4. **Run the backend**
   ```bash
   uvicorn app.main:app --reload
   ```

## Usage
- **Ingestion**: Place or update files in `Docs/` (auto-detected and ingested)
- **API**: Use endpoints to query by department, SOP, or ask questions (see API docs at `/docs` when running)

## Extending
- Add new parsers in `app/ingestion/`
- Add new models or RAG strategies in `app/rag/`
- Add new endpoints in `app/api/`

## License
MIT
