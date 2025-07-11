import os
from pathlib import Path
from docx import Document
from app.weaviate_client.client import get_client
from app.ollama.client import get_embedding, get_llm_completion
import openai
import time

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# --- LLM chunking helper ---
def llm_semantic_chunk(text, sop_title):
    """Use LLM to split text into semantic, self-contained chunks."""
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
        prompt = (
            f"Split the following SOP section into semantically meaningful, self-contained chunks (ideally 200-500 words each). "
            f"Return a numbered list, each item being a chunk.\n\nSOP Title: {sop_title}\n\nText:\n{text}\n"
        )
        try:
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2048,
            )
            answer = response.choices[0].message["content"]
            # Parse numbered list
            chunks = []
            for line in answer.split("\n"):
                if line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.")):
                    chunk = line.split(".", 1)[-1].strip()
                    if chunk:
                        chunks.append(chunk)
            if chunks:
                return chunks
        except Exception as e:
            print(f"[LLM Chunking] OpenAI error: {e}")
    # Fallback: split by paragraphs
    return [p.strip() for p in text.split("\n") if p.strip()]

# --- Metadata helper ---
def generate_summary(chunk, sop_title):
    if OPENAI_API_KEY:
        prompt = f"Summarize this SOP chunk in 1-2 sentences.\nSOP: {sop_title}\nChunk:\n{chunk}"
        try:
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=128,
            )
            return response.choices[0].message["content"].strip()
        except Exception as e:
            print(f"[LLM Summary] OpenAI error: {e}")
    return chunk[:200] + ("..." if len(chunk) > 200 else "")

# --- Main ingestion logic ---
def ingest_docx_semantic(docx_path):
    print(f"[Semantic Ingest] Processing: {docx_path}")
    doc = Document(docx_path)
    sop_title = Path(docx_path).stem
    # Extract department from path (e.g., .../BDM/filename.docx)
    department = Path(docx_path).parent.name
    tags = department  # Use department as tag (string)
    # Concatenate all paragraphs for LLM chunking
    full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    chunks = llm_semantic_chunk(full_text, sop_title)
    client = get_client()
    section_collection = client.collections.get("Section")
    for idx, chunk in enumerate(chunks):
        summary = generate_summary(chunk, sop_title)
        embedding = get_embedding(chunk)
        obj = {
            "title": sop_title,
            "section": f"Chunk {idx+1}",
            "content": chunk,
            "summary": summary,
            "sop": sop_title,
            "embedding": embedding,
            "department": department,
            "tags": tags  # as a string
        }
        # Force tags to string before insert
        obj["tags"] = ",".join(obj["tags"]) if isinstance(obj["tags"], list) else str(obj["tags"])
        print(f"[DEBUG] Inserting object: {obj} (tags type: {type(obj['tags'])})")
        try:
            section_collection.data.insert(obj)
            print(f"[Semantic Ingest] Stored chunk {idx+1}: {summary[:80]}")
            time.sleep(0.5)  # avoid rate limits
        except Exception as e:
            print(f"[ERROR] Failed to insert object: {obj}\nException: {e}")
            break  # Stop further processing on error

# --- Batch ingest ---
def batch_ingest(directory):
    docx_files = list(Path(directory).glob('*.docx'))
    print(f"[Semantic Ingest] Found {len(docx_files)} DOCX files in {directory}")
    for docx_path in docx_files:
        try:
            ingest_docx_semantic(str(docx_path))
        except Exception as e:
            print(f"[Semantic Ingest] Error processing {docx_path}: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if Path(arg).is_file():
                ingest_docx_semantic(arg)
            elif Path(arg).is_dir():
                batch_ingest(arg)
    else:
        batch_ingest("../Docs/BDM/") 