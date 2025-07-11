# Product Requirements Document (PRD)

## Project: Departmental AI Knowledge Graph Backend

### 1. Purpose
Build a backend system that ingests department-wise SOPs and documents, constructs a knowledge graph, and provides a multi-layered RAG (Retrieval-Augmented Generation) pipeline for AI-powered applications (Q&A, LMS, analytics, etc.).

### 2. Goals
- Enable real-time, automated ingestion of SOPs and documents from a shared folder structure.
- Build a knowledge graph linking departments, SOPs, and sections for rich context and analytics.
- Provide a robust, multi-layered RAG pipeline for highly relevant, department-specific answers.
- Expose a modular, extensible API for use by various frontend applications.

### 3. Features
- **Real-time File Watcher:** Monitors `Docs/` for new/changed/deleted files and triggers ingestion.
- **Multi-format Ingestion:** Start with DOCX, extensible to PDF, Excel, etc.
- **Metadata Extraction:** Department (from folder), SOP title, section headers, and (if available) version/date.
- **Knowledge Graph:** Nodes for departments, SOPs, sections; edges for relationships (belongs_to, references).
- **Vector Store:** Store section embeddings in Weaviate for semantic search.
- **Multi-layered RAG:**
  - Filter by department/section (metadata/graph)
  - Vector search for relevant sections
  - Graph expansion for referenced context
  - LLM answer synthesis (Ollama)
- **API Endpoints:**
  - Ingest new documents (manual/auto)
  - Query by department/SOP/section
  - RAG answer endpoint
  - (Future) Knowledge graph analytics
- **Extensibility:** Modular for new formats, models, and app integrations.

### 4. Architecture
- **Backend:** FastAPI (Python)
- **Vector Store/Graph:** Weaviate (local, on-premises)
- **LLM/Embeddings:** Ollama (local, with support for future models)
- **File Watcher:** Watchdog (Python)

### 5. Requirements
- **Functional:**
  - Ingest DOCX files from `Docs/<Department>/`
  - Extract department, SOP title, section headers
  - Chunk by section for embedding
  - Store embeddings and metadata in Weaviate
  - Build and update knowledge graph
  - Expose API for ingestion, querying, and RAG answers
  - Real-time updates on file changes
- **Non-Functional:**
  - Modular, extensible codebase
  - Secure API (future)
  - Scalable to new formats and departments

### 6. User Stories
- As an admin, I want new SOPs to be auto-ingested so the knowledge base is always up to date.
- As a user, I want to ask questions filtered by department and get accurate, context-rich answers.
- As a developer, I want to extend the backend for new document types and AI models easily.

### 7. Out of Scope (for v1)
- User authentication/authorization
- Frontend applications (handled separately)
- Analytics endpoints (future)

### 8. Milestones
1. Project setup, Weaviate & Ollama integration
2. DOCX ingestion, section chunking, embedding
3. Knowledge graph schema & population
4. Multi-layered RAG pipeline
5. API endpoints
6. Real-time file watcher
7. Testing & documentation 