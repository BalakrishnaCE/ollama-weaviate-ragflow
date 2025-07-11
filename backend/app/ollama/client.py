import os
import requests
import json

OLLAMA_URL = "http://localhost:11434"  # Default Ollama API URL
EMBED_MODEL = "mxbai-embed-large"  # Change if needed
LLM_MODEL = "llama3"  # Change if needed

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

try:
    import openai
except ImportError:
    openai = None


def get_embedding(text):
    url = f"{OLLAMA_URL}/api/embed"
    payload = {"model": EMBED_MODEL, "input": text}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    data = response.json()
    # Ollama may return either 'embedding' or 'embeddings' (list of embeddings)
    if "embedding" in data:
        return data["embedding"]
    elif "embeddings" in data:
        # embeddings is a list of embeddings, one per input
        return data["embeddings"][0]
    else:
        raise ValueError(f"No embedding found in Ollama response: {data}")

def get_llm_completion(prompt, system_prompt=None, max_tokens=512):
    if OPENAI_API_KEY and openai is not None:
        openai.api_key = OPENAI_API_KEY
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({"role": "system", "content": "You are a helpful assistant for answering questions from company SOPs."})
        messages.append({"role": "user", "content": prompt})
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.2,
        )
        result = response.choices[0].message["content"].strip()
        print("[OpenAI] Raw LLM output:", result)
        return result
    # Fallback to Ollama
    url = f"{OLLAMA_URL}/api/generate"
    payload = {"model": LLM_MODEL, "prompt": prompt}
    if system_prompt:
        payload["system"] = system_prompt
    if max_tokens:
        payload["options"] = {"num_predict": max_tokens}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    # Handle streaming JSON lines
    lines = response.text.strip().splitlines()
    answer_parts = []
    for line in lines:
        try:
            obj = json.loads(line)
            if "response" in obj:
                answer_parts.append(obj["response"])
        except Exception:
            continue
    result = "".join(answer_parts).strip()
    print("[Ollama] Raw LLM output:", result)
    return result 