# Integration & Troubleshooting Guide: RAG Pipeline, Weaviate, and Ollama

## 1. Project Structure & Key Components
- **FastAPI** backend for API endpoints.
- **Weaviate** as the vector database (v4.x Python client).
- **Ollama** for local LLM and embedding generation.
- **Ingestion pipeline** for DOCX files, extracting department/SOP/sections, generating embeddings, and storing in Weaviate.
- **RAG endpoint** for semantic search and answer synthesis.

---

## 2. Critical Integration Requirements & Gotchas

### A. Weaviate Integration
- **Client Version:**
  - Use the **v4.x Python client** for compatibility with the latest Weaviate server.
  - The API is different from v3.x and the REST API—pay close attention to method signatures and argument names.
- **Schema Definition:**
  - Use the correct `data_type` values (`"text"`, `"number[]"`, `"date"`, etc.).
  - For the Python client, use the `DataType` enum if available, or the correct string.
  - **Do not use lists** for `data_type` (e.g., use `"text"`, not `["text"]`).
- **Schema Creation:**
  - Always ensure the schema is created **before** any data insertion or query.
  - Use a FastAPI startup event to call `create_schema()` at app launch.
- **Vectorizer:**
  - If using external embeddings (Ollama), set `vectorizer: none` in the schema.
  - All vector searches must use `.near_vector(...)` (not `.near_text`).
- **Query API:**
  - Use `.near_vector(embedding, ...)` (not `vector=...` or `near_text`).
  - Use `return_properties` for custom fields, not `return_metadata`.
- **Date Fields:**
  - Weaviate expects RFC3339 date strings for `date` properties.
  - Omit the `date` property if you don’t have a valid value.

### B. Ollama Integration
- **Ollama Version:**
  - Must be **v0.1.31+** for embedding support.
- **Model Availability:**
  - Pull an embedding model (`mxbai-embed-large`, `all-minilm`, etc.) before use.
  - The model name in your code must match what’s available in `ollama list`.
- **Embedding Endpoint:**
  - Use `/api/embed` with payload:
    ```json
    { "model": "mxbai-embed-large", "input": "your text" }
    ```
  - The response will have either `"embedding"` or `"embeddings"` (list).
- **Error Handling:**
  - If the input is empty, Ollama returns an empty list—**skip embedding generation for empty strings**.

### C. Ingestion Pipeline
- **DOCX Extraction:**
  - Extract department, SOP title, and sections.
  - For each section, only generate embeddings and insert into Weaviate if the content is non-empty.
- **Upsert Logic:**
  - When upserting departments/SOPs, use vector search to check for existence.
  - Only insert if not already present.

### D. Testing & Mocking
- **Test Coverage:**
  - Tests should mock external dependencies (Ollama, Weaviate) where possible for speed and reliability.
- **Common Test Failures:**
  - Failing to start Ollama or Weaviate, or using the wrong endpoint/model, will cause connection or 404 errors.
  - Inserting invalid data (e.g., empty date, empty content) will cause 422 or index errors.

---

## 3. Common Pitfalls & How They Were Solved

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` for local imports | Run Uvicorn from the correct directory, or set `PYTHONPATH` |
| Weaviate schema errors (`data_type`, `name`/`class`) | Use correct field names and types for the Python client |
| Vector search errors (`near_vector` argument) | Use positional argument for embedding, not `vector=` |
| 404 from Ollama | Use `/api/embed` and ensure the model is pulled and available |
| 422 from Weaviate on date | Only include `date` if valid RFC3339 string |
| IndexError on embedding | Skip embedding for empty content |
| Tests failing due to missing services | Start Ollama/Weaviate, or mock in tests |

---

## 4. Best Practices for Future Development
- **Always check the latest API docs** for Weaviate and Ollama—APIs change!
- **Validate all external service endpoints** and model names before running the app.
- **Add logging** for schema creation, ingestion, and embedding calls for easier debugging.
- **Handle all edge cases** (empty content, missing dates, etc.) gracefully.
- **Mock external dependencies in tests** to avoid flakiness and speed up CI.

---

## 5. Integration Checklist
- [x] Weaviate v4.x running and accessible
- [x] Ollama running with embedding model pulled
- [x] FastAPI backend with correct import paths
- [x] Schema created at startup
- [x] All vector search and insertions use correct API
- [x] Embedding client uses `/api/embed` and available model
- [x] Tests pass with all services running

---

## 6. References
- [Ollama Embedding Models Blog](https://ollama.com/blog/embedding-models)
- [Weaviate Python Client Docs](https://weaviate.io/developers/weaviate/client-libraries/python)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) 