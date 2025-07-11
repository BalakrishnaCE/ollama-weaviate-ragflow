import os

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
# LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:14b")  # To use Qwen3-14B, uncomment this line and comment the next line
LLM_MODEL = os.getenv("LLM_MODEL", "llama3")  # Default: llama3 (production baseline)
