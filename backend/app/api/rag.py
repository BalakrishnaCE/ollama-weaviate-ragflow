from fastapi import APIRouter, Query, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.weaviate_client.client import get_client
from app.ollama.client import get_embedding, get_llm_completion
from weaviate.collections.classes.filters import Filter
import re
from collections import Counter
try:
    from ragas import evaluate
    from ragas.metrics import faithfulness, context_relevance, answer_relevance, answer_correctness, answer_completeness
except ImportError:
    evaluate = None
import sqlite3
from datetime import datetime
from fastapi.responses import StreamingResponse, JSONResponse
import csv
import io
from rapidfuzz import process as fuzz_process

SEARCH_SYNONYMS = {
    "expansion": ["expand", "growth", "client expansion", "expansion process", "process of expansion"],
    "downsizing": ["downsize", "reduce", "client downsizing", "downsizing process", "process of downsizing"],
    "closure": ["close", "account closure", "client closure", "closure process"],
    # Add more as needed
}

def expand_keywords(query):
    words = set(query.lower().split())
    expansions = set([query])
    for word in words:
        if word in SEARCH_SYNONYMS:
            expansions.update(SEARCH_SYNONYMS[word])
    return list(expansions)

router = APIRouter()

class QueryRequest(BaseModel):
    question: str
    user_id: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None
    top_k: int = 10
    department: Optional[str] = None
    sop: Optional[str] = None

# --- Feedback DB setup ---
FEEDBACK_DB = "rag_feedback.db"
def init_feedback_db():
    conn = sqlite3.connect(FEEDBACK_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        question TEXT,
        answer TEXT,
        context TEXT,
        rating INTEGER,
        comments TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS evaluation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        question TEXT,
        answer TEXT,
        context TEXT,
        faithfulness REAL,
        context_relevance REAL,
        completeness REAL
    )''')
    conn.commit()
    conn.close()
init_feedback_db()

class FeedbackRequest(BaseModel):
    question: str
    answer: str
    context: List[str]
    rating: int  # 1=bad, 2=neutral, 3=good
    comments: Optional[str] = None

@router.post("/feedback")
async def rag_feedback(payload: FeedbackRequest):
    conn = sqlite3.connect(FEEDBACK_DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO feedback (timestamp, question, answer, context, rating, comments) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), payload.question, payload.answer, "\n".join(payload.context), payload.rating, payload.comments)
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

# --- Modify /query to run evaluation and log ---
@router.post("/query")
async def rag_query(query: QueryRequest):
    client = get_client()
    user_ctx = get_user_context(query.user_id, query.profile)
    try:
        section_collection = client.collections.get("Section")
        print(f"[RAG] Running hybrid search for: {query.question}")
        filter_expr = None
        if query.department:
            filter_expr = Filter.by_property("department").equal(query.department)
        if query.sop:
            sop_filter = Filter.by_property("sop").equal(query.sop)
            filter_expr = filter_expr & sop_filter if filter_expr else sop_filter

        # 1. True hybrid search (alpha=0.5)
        query_vector = get_embedding(query.question)
        results = section_collection.query.hybrid(
            query=query.question,
            vector=query_vector,
            alpha=0.5,
            limit=query.top_k,
            filters=filter_expr,
            return_properties=["title", "content", "section", "summary", "sop", "tags", "embedding", "department"]
        )
        candidates = [
            {
                "title": obj.properties.get("title"),
                "content": obj.properties.get("content"),
                "section": obj.properties.get("section"),
                "summary": obj.properties.get("summary"),
                "sop": obj.properties.get("sop"),
                "tags": obj.properties.get("tags"),
                "embedding": obj.properties.get("embedding"),
                "score": getattr(obj.metadata, "score", None) if obj.metadata else None
            }
            for obj in results.objects
        ]
        candidates = filter_by_access(candidates, user_ctx)
        # 2. Fallback: If no good results, try pure keyword search
        if not candidates:
            results = section_collection.query.hybrid(
                query=query.question,
                vector=None,
                alpha=0.0,
                limit=query.top_k,
                filters=filter_expr,
                return_properties=["title", "content", "section", "summary", "sop", "tags", "embedding", "department"]
            )
            candidates = [
                {
                    "title": obj.properties.get("title"),
                    "content": obj.properties.get("content"),
                    "section": obj.properties.get("section"),
                    "summary": obj.properties.get("summary"),
                    "sop": obj.properties.get("sop"),
                    "tags": obj.properties.get("tags"),
                    "embedding": obj.properties.get("embedding"),
                    "score": getattr(obj.metadata, "score", None) if obj.metadata else None
                }
                for obj in results.objects
            ]
            candidates = filter_by_access(candidates, user_ctx)
        # 3. Fallback: If still no results, expand query with synonyms and merge
        if not candidates:
            expanded_queries = expand_keywords(query.question)
            seen = set()
            all_candidates = []
            for q in expanded_queries:
                results = section_collection.query.hybrid(
                    query=q,
                    vector=get_embedding(q),
                    alpha=0.5,
                    limit=query.top_k,
                    filters=filter_expr,
                    return_properties=["title", "content", "section", "summary", "sop", "tags", "embedding", "department"]
                )
                for obj in results.objects:
                    key = (obj.properties.get("title"), obj.properties.get("content"))
                    if key not in seen:
                        seen.add(key)
                        all_candidates.append({
                            "title": obj.properties.get("title"),
                            "content": obj.properties.get("content"),
                            "section": obj.properties.get("section"),
                            "summary": obj.properties.get("summary"),
                            "sop": obj.properties.get("sop"),
                            "tags": obj.properties.get("tags"),
                            "embedding": obj.properties.get("embedding"),
                            "score": getattr(obj.metadata, "score", None) if obj.metadata else None
                        })
            candidates = filter_by_access(all_candidates, user_ctx)

        print(f"[RAG] Hybrid search returned {len(candidates)} candidates after access control.")
        print("[DEBUG] Top 3 retrieved chunks after access control:")
        for i, c in enumerate(candidates[:3]):
            print(f"[{i+1}] title: {c.get('title')}, content: {c.get('content')}")

        # LLM-based reranking: rate each chunk for relevance
        def llm_rerank(query_text, chunks):
            scored = []
            for c in chunks:
                prompt = (
                    f"Rate the relevance of the following chunk to the user question on a scale of 1 (not relevant) to 5 (highly relevant).\n"
                    f"Question: {query_text}\nChunk: {c['content']}\nRelevance (1-5):"
                )
                try:
                    score_str = get_llm_completion(prompt)
                    score = int(re.search(r"[1-5]", score_str).group())
                except Exception:
                    score = 1
                scored.append((score, c))
            scored.sort(reverse=True, key=lambda x: x[0])
            return [c for score, c in scored]

        reranked = llm_rerank(query.question, candidates)
        print(f"[RAG] Reranked top 5 chunks:")
        for i, c in enumerate(reranked[:5]):
            print(f"[RAG] [RERANKED] {i+1}. {c['title']} | {c['content'][:120] if c['content'] else ''}")

        # Use more top chunks for context (increase to 8)
        context_chunks = reranked[:8]
        context = "\n\n".join(f"[{c['title']}] {c['content']}" for c in context_chunks if c['content'])
        first_chunk = context_chunks[0]["content"] if context_chunks and context_chunks[0].get("content") else ""
        print(f"[RAG] Final context sent to LLM (first 500 chars):\n{context[:500]}")
        prompt = (
            "Based on the provided context below, answer the question as thoroughly, comprehensively, and in as much detail as possible. "
            "Use the FIRST context chunk as your primary source. Reproduce its structure, details, and stepwise instructions in full. Then, supplement with any additional relevant information from the remaining context. Do not omit important steps or details. "
            "Format your answer in clean, readable HTML with <ul>, <ol>, <li>, <b>, <h3>, and <p> tags as appropriate. Use bullet points, bold for headings, and preserve stepwise structure. Do NOT repeat the context verbatim.\n"
            "If the answer is not in the context, say 'Not found in knowledge base.'\n"
            f"Context:\n{context}\n\nQuestion: {query.question}\nAnswer:"
        )
        llm_answer = get_llm_completion(prompt, max_tokens=2048)
        print("[RAG] LLM raw output:", llm_answer)
        # Add direct context answer for frontend
        direct_context_answer = context

        # Add context summary
        summary_prompt = (
            f"Summarize the following context in detail for the user.\nContext:\n{context}"
        )
        context_summary = get_llm_completion(summary_prompt, max_tokens=512)

        # --- Automated evaluation with RAGAS ---
        eval_metrics = None
        if evaluate is not None:
            eval_data = [{
                "question": query.question,
                "answer": llm_answer,
                "contexts": [c["content"] for c in context_chunks if c["content"]]
            }]
            try:
                results = evaluate(
                    eval_data,
                    metrics=[faithfulness, context_relevance, answer_completeness]
                )
                eval_metrics = {
                    "faithfulness": results[0]["faithfulness"],
                    "context_relevance": results[0]["context_relevance"],
                    "completeness": results[0]["answer_completeness"]
                }
                # Store in DB
                conn = sqlite3.connect(FEEDBACK_DB)
                c = conn.cursor()
                c.execute(
                    "INSERT INTO evaluation (timestamp, question, answer, context, faithfulness, context_relevance, completeness) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (datetime.utcnow().isoformat(), query.question, llm_answer, "\n".join([c["content"] for c in context_chunks if c["content"]]), eval_metrics["faithfulness"], eval_metrics["context_relevance"], eval_metrics["completeness"])
                )
                conn.commit()
                conn.close()
            except Exception as e:
                eval_metrics = {"error": str(e)}
        # Only include title/content in response context
        response_context = [{"title": c["title"], "content": c["content"]} for c in context_chunks]
        return {"answer": llm_answer, "context_summary": context_summary, "matches": response_context, "evaluation": eval_metrics, "direct_context_answer": direct_context_answer}
    except Exception as e:
        return {"error": str(e)}

class AgenticQueryRequest(BaseModel):
    question: str
    user_id: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None
    top_k: int = 10
    max_steps: int = 5

# --- Simple user context store (in-memory for demo) ---
USER_PROFILES = {}

def get_user_context(user_id, profile):
    if user_id:
        if user_id in USER_PROFILES:
            ctx = USER_PROFILES[user_id].copy()
            if profile:
                ctx.update(profile)
            return ctx
        else:
            USER_PROFILES[user_id] = profile or {}
            return USER_PROFILES[user_id]
    return profile or {}

# --- Access control utility ---
def filter_by_access(chunks, user_ctx):
    user_roles = set()
    if user_ctx:
        if isinstance(user_ctx.get("role"), list):
            user_roles.update([r.lower() for r in user_ctx["role"]])
        elif user_ctx.get("role"):
            user_roles.add(user_ctx["role"].lower())
    filtered = []
    for c in chunks:
        tags = c.get("tags")
        # Patch: treat None or empty tags as public
        if not tags:
            filtered.append(c)
            continue
        if isinstance(tags, str):
            tags = [t.strip().lower() for t in tags.split(",") if t.strip()]
        elif isinstance(tags, list):
            tags = [str(t).lower() for t in tags]
        else:
            tags = []
        # If tags is now empty, treat as public
        if not tags or user_roles.intersection(tags):
            filtered.append(c)
    return filtered

# --- Agentic/Multi-hop RAG endpoint (with access control and more tools) ---
@router.post("/agentic_query")
async def agentic_query(payload: AgenticQueryRequest):
    user_ctx = get_user_context(payload.user_id, payload.profile)
    question = payload.question
    top_k = payload.top_k
    max_steps = payload.max_steps
    steps = []
    context_chunks = []
    answer = None
    last_context_chunks = []
    for step in range(max_steps):
        # Build agent prompt with user question, context, and tool instructions
        agent_prompt = (
            "You are an expert assistant with access to a knowledge base of Standard Operating Procedures (SOPs). "
            "Your job is to answer user questions by searching, synthesizing, and summarizing information from the SOPs. "
            "You can use the following tools: SEARCH (to find relevant SOP content), SUMMARIZE (to synthesize an answer), FINAL_ANSWER (to provide the final answer), LIST_SOPS (to list available SOPs), and GET_SOP_SECTION (to fetch a specific SOP section). "
            "Always ground your answers in the provided SOP context. If the answer is not directly in the context, combine related information, reason step by step, and suggest best practices or next steps. "
            "Do NOT just echo the search or say 'I could not find an answer.' "
            "Be concise, assertive, and use bullet points or stepwise instructions when possible.\n"
            f"Question: {question}\n"
            "You can issue actions in the following format:\n"
            "SEARCH: <query>\nSUMMARIZE: <text>\nLIST_SOPS: <filter>\nGET_SOP_SECTION: <sop>, <section>\nFINAL_ANSWER: <answer>\n"
            "If you need to look up information, use SEARCH. Use LIST_SOPS to see available SOPs. Use GET_SOP_SECTION to fetch a specific SOP section. When ready, use FINAL_ANSWER.\n"
            f"First, SEARCH: {question}"
        )
        if step > 0 and last_context_chunks:
            # For SUMMARIZE or FINAL_ANSWER, include context
            context_str = "\n\n".join(f"[{c['title']}] {c['content']}" for c in last_context_chunks if c.get('content'))
            agent_prompt += f"\n\nHere are the most relevant SOP sections I found:\n{context_str}\n"
        llm_out = get_llm_completion(agent_prompt)
        print(f"[AGENTIC] Step {step+1} LLM output:\n{llm_out}")
        # Parse action
        if llm_out.strip().startswith("SEARCH:"):
            search_query = llm_out.strip()[7:].strip()
            expanded_queries = expand_keywords(search_query)
            client = get_client()
            section_collection = client.collections.get("Section")
            all_candidates = []
            seen = set()
            for q in expanded_queries:
                hybrid_result = section_collection.query.hybrid(
                    query=q,
                    vector=get_embedding(q),
                    limit=top_k,
                    return_properties=["title", "content", "section", "summary", "sop", "tags", "embedding"]
                )
                for obj in hybrid_result.objects:
                    key = (obj.properties.get("title"), obj.properties.get("content"))
                    if key not in seen:
                        seen.add(key)
                        all_candidates.append({
                            "title": obj.properties.get("title"),
                            "content": obj.properties.get("content"),
                            "section": obj.properties.get("section"),
                            "summary": obj.properties.get("summary"),
                            "sop": obj.properties.get("sop"),
                            "tags": obj.properties.get("tags"),
                            "embedding": obj.properties.get("embedding"),
                            "score": getattr(obj.metadata, "score", None) if obj.metadata else None
                        })
            # --- Access control: filter by user_ctx ---
            candidates = filter_by_access(all_candidates, user_ctx)
            last_context_chunks = candidates[:top_k]
            context_chunks = last_context_chunks
            steps.append({"action": "SEARCH", "input": search_query, "result": context_chunks})
        elif llm_out.strip().startswith("SUMMARIZE:"):
            text = llm_out.strip()[10:].strip()
            # Always include context in the summary prompt
            context_str = "\n\n".join(f"[{c['title']}] {c['content']}" for c in last_context_chunks if c.get('content'))
            summary_prompt = f"Based on the following context, summarize for the user (context: {user_ctx}):\n{context_str}\n\n{text}"
            summary = get_llm_completion(summary_prompt)
            steps.append({"action": "SUMMARIZE", "input": text, "result": summary})
        elif llm_out.strip().startswith("LIST_SOPS:"):
            filter_str = llm_out.strip()[10:].strip()
            client = get_client()
            section_collection = client.collections.get("Section")
            # List unique SOPs, optionally filter by tag
            query = {
                "limit": 100,
                "return_properties": ["sop", "tags"]
            }
            sops = set()
            for obj in section_collection.query.hybrid(query=filter_str, vector=None, limit=100, return_properties=["sop", "tags"]).objects:
                tags = obj.properties.get("tags") or []
                if isinstance(tags, str):
                    tags = [t.strip().lower() for t in tags.split(",") if t.strip()]
                else:
                    tags = [t.lower() for t in tags]
                # Access control
                if not tags or (user_ctx and user_ctx.get("role") and user_ctx["role"].lower() in tags):
                    sops.add(obj.properties.get("sop"))
            steps.append({"action": "LIST_SOPS", "input": filter_str, "result": list(sops)})
        elif llm_out.strip().startswith("GET_SOP_SECTION:"):
            args = llm_out.strip()[16:].strip().split(",")
            sop = args[0].strip() if len(args) > 0 else None
            section = args[1].strip() if len(args) > 1 else None
            client = get_client()
            section_collection = client.collections.get("Section")
            # Query for the specific SOP and section
            filter_query = f"sop == '{sop}' and section == '{section}'"
            result = section_collection.query.hybrid(query=section, vector=get_embedding(section), limit=3, return_properties=["title", "content", "section", "summary", "sop", "tags"])
            candidates = []
            for obj in result.objects:
                candidates.append({
                    "title": obj.properties.get("title"),
                    "content": obj.properties.get("content"),
                    "section": obj.properties.get("section"),
                    "summary": obj.properties.get("summary"),
                    "sop": obj.properties.get("sop"),
                    "tags": obj.properties.get("tags")
                })
            candidates = filter_by_access(candidates, user_ctx)
            steps.append({"action": "GET_SOP_SECTION", "input": f"{sop}, {section}", "result": candidates})
        elif llm_out.strip().startswith("FINAL_ANSWER:"):
            # Always include context in the final answer prompt
            context_str = "\n\n".join(f"[{c['title']}] {c['content']}" for c in last_context_chunks if c.get('content'))
            final_prompt = f"Based on the following context, answer the user's question as thoroughly and in as much detail as possible.\n{context_str}\n\nQuestion: {question}\nAnswer:"
            answer = get_llm_completion(final_prompt, max_tokens=2048)
            steps.append({"action": "FINAL_ANSWER", "input": question, "result": answer})
            break
        else:
            # Fallback: treat as answer, include context
            context_str = "\n\n".join(f"[{c['title']}] {c['content']}" for c in last_context_chunks if c.get('content'))
            final_prompt = f"Based on the following context, answer the user's question as accurately and concisely as possible.\n{context_str}\n\nQuestion: {question}\nAnswer:"
            answer = get_llm_completion(final_prompt)
            steps.append({"action": "FINAL_ANSWER", "input": question, "result": answer})
            break

    # After agent loop, extract the final answer and summarize reasoning
    final_answer = None
    for step in reversed(steps):
        if step['action'] == 'FINAL_ANSWER' and step['result']:
            final_answer = step['result']
            break
    if not final_answer:
        # Fallback: use last SUMMARIZE step
        for step in reversed(steps):
            if step['action'] == 'SUMMARIZE' and step['result']:
                final_answer = step['result']
                break
    if not final_answer:
        final_answer = None

    # Add a more detailed LLM-generated summary of the agent's reasoning
    reasoning_text = '\n'.join(f"Step {i+1}: {s['action']} - {str(s['result'])[:200]}" for i, s in enumerate(steps))
    summary_prompt = (
        f"Summarize the following agent reasoning steps in detail for the user.\nSteps:\n{reasoning_text}"
    )
    reasoning_summary = get_llm_completion(summary_prompt, max_tokens=512)

    # Backend fallback: always return a non-null, user-friendly answer
    if not final_answer or not str(final_answer).strip():
        if reasoning_summary and str(reasoning_summary).strip():
            final_answer = reasoning_summary
        elif steps and steps[0].get('result'):
            # Fallback to the first step's result (usually a summary or context chunk)
            chunk = steps[0]['result']
            if isinstance(chunk, dict) and chunk.get('content'):
                final_answer = chunk['content']
            elif isinstance(chunk, str):
                final_answer = chunk
            else:
                final_answer = "No answer found, but see reasoning steps for details."
        else:
            final_answer = "No answer found, but see reasoning steps for details."

    return {
        "answer": final_answer,
        "reasoning_summary": reasoning_summary,
        "steps": steps
    }

@router.get("/debug/sections")
async def list_sections(sop: Optional[str] = None):
    """List all section titles and first 200 chars of content for a given SOP (or all if not specified)."""
    client = get_client()
    section_collection = client.collections.get("Section")
    filters = None
    if sop:
        filters = Filter.by_property("sop").equal(sop)
    results = section_collection.query.fetch_objects(
        limit=200,
        filters=filters,
        return_properties=["title", "content", "sop"]
    )
    out = []
    for obj in results.objects:
        title = obj.properties.get("title")
        content = obj.properties.get("content")
        sop_title = obj.properties.get("sop")
        out.append({
            "sop": sop_title,
            "title": title,
            "content": content[:200] if content else ""
        })
    return {"sections": out}

def extract_keywords(text):
    stopwords = {"the", "is", "in", "at", "which", "on", "for", "a", "an", "to", "of", "and", "i", "what", "should", "with", "as", "by", "from", "this", "that", "it", "be", "or", "are", "was", "were", "but", "if", "so", "do", "does", "did", "can", "could", "would", "will", "shall", "may", "might", "must", "not", "have", "has", "had", "you", "your", "about", "into", "than", "then", "them", "they", "their", "there", "here", "how", "when", "where", "who", "whom", "why"}
    words = re.findall(r'\w+', text.lower())
    return [w for w in words if w not in stopwords and len(w) > 2]

class EvaluationRequest(BaseModel):
    question: str
    answer: str
    context_chunks: List[str]

@router.post("/evaluate")
async def rag_evaluate(payload: EvaluationRequest):
    if evaluate is None:
        return {"error": "RAGAS is not installed. Please run 'pip install ragas'"}
    # Prepare RAGAS input
    question = payload.question
    answer = payload.answer
    context = payload.context_chunks
    # RAGAS expects a list of dicts
    data = [{
        "question": question,
        "answer": answer,
        "contexts": context
    }]
    # Evaluate
    results = evaluate(
        data,
        metrics=[faithfulness, context_relevance, answer_completeness]
    )
    return {
        "faithfulness": results[0]["faithfulness"],
        "context_relevance": results[0]["context_relevance"],
        "completeness": results[0]["answer_completeness"]
    }

# --- Admin endpoints for feedback/evaluation logs ---
@router.get("/admin/feedback")
def get_feedback():
    conn = sqlite3.connect(FEEDBACK_DB)
    c = conn.cursor()
    c.execute("SELECT id, timestamp, question, answer, context, rating, comments FROM feedback ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    keys = ["id", "timestamp", "question", "answer", "context", "rating", "comments"]
    return JSONResponse([{k: row[i] for i, k in enumerate(keys)} for row in rows])

@router.get("/admin/evaluation")
def get_evaluation():
    conn = sqlite3.connect(FEEDBACK_DB)
    c = conn.cursor()
    c.execute("SELECT id, timestamp, question, answer, context, faithfulness, context_relevance, completeness FROM evaluation ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    keys = ["id", "timestamp", "question", "answer", "context", "faithfulness", "context_relevance", "completeness"]
    return JSONResponse([{k: row[i] for i, k in enumerate(keys)} for row in rows])

@router.get("/admin/feedback/csv")
def download_feedback_csv():
    conn = sqlite3.connect(FEEDBACK_DB)
    c = conn.cursor()
    c.execute("SELECT id, timestamp, question, answer, context, rating, comments FROM feedback ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "timestamp", "question", "answer", "context", "rating", "comments"])
    writer.writerows(rows)
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=feedback.csv"})

@router.get("/admin/evaluation/csv")
def download_evaluation_csv():
    conn = sqlite3.connect(FEEDBACK_DB)
    c = conn.cursor()
    c.execute("SELECT id, timestamp, question, answer, context, faithfulness, context_relevance, completeness FROM evaluation ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "timestamp", "question", "answer", "context", "faithfulness", "context_relevance", "completeness"])
    writer.writerows(rows)
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=evaluation.csv"}) 