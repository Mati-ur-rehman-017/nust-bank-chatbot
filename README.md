# NUST Bank Assist

LLM-based customer service assistant for NUST Bank using RAG (Retrieval-Augmented Generation) with Phi-3 Mini, ChromaDB vector store, and strict safety guardrails.

## Quick Start (Docker)

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Build and run the stack
docker compose up --build -d

# 3. Ingest documents into vector store
docker compose exec backend python scripts/ingest_data.py

# 4. Verify health
curl http://localhost:8000/api/health
```

## Architecture

| Component | Technology |
|-----------|------------|
| Backend | Python + FastAPI |
| Vector DB | ChromaDB (persistent) |
| LLM | Phi-3 Mini 3.8B (via Ollama) |
| Embeddings | all-MiniLM-L6-v2 (384 dims) |
| Frontend | React + Vite + TypeScript (Phase 6) |

## Project Structure

```
llm/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # FastAPI endpoints
│   │   ├── data/            # Vector store, preprocessing
│   │   ├── services/        # Embedding, LLM, retrieval
│   │   └── config.py        # Environment configuration
│   └── scripts/
│       └── ingest_data.py   # Document ingestion script
├── rag_data/                # Source documents (JSON, XLSX)
├── data/
│   └── chroma_store/        # ChromaDB persistent storage
├── docker-compose.yml
└── .env.example
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | LLM model name | `phi3:mini` |
| `CHROMA_PATH` | ChromaDB storage path | `./data/chroma_store` |
| `EMBEDDING_MODEL` | Sentence transformer model | `all-MiniLM-L6-v2` |
| `API_HOST` | Backend host | `0.0.0.0` |
| `API_PORT` | Backend port | `8000` |
| `MAX_INPUT_LENGTH` | Max query length | `4000` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | `60` |

## Data Ingestion

Place documents in `rag_data/` directory (supports JSON, CSV, XLSX, PDF, plain text), then run:

```bash
docker compose exec backend python scripts/ingest_data.py
```

The script will:
1. Load documents from `rag_data/`
2. Chunk text into smaller segments
3. Generate embeddings using all-MiniLM-L6-v2
4. Store vectors in ChromaDB

## Testing Vector Search

```bash
docker compose exec backend python -c "
from app.config import settings
from app.services.embedding import EmbeddingService
from app.data.vectorstore import VectorStore

store = VectorStore(str(settings.chroma_path))
print(f'Documents indexed: {store.count()}')

emb = EmbeddingService(model_name=settings.embedding_model)
results = store.search(emb.embed('What are fund transfer limits?'), top_k=3)
for r in results:
    print(f'[{r.score:.3f}] {r.text[:80]}...')
"
```

## Local Development (without Docker)

For local development, use Python 3.12 via pyenv:

```bash
# Setup Python environment
pyenv install 3.12.2
pyenv virtualenv 3.12.2 nust-bank
pyenv local nust-bank

# Install dependencies
pip install -r backend/requirements.txt

# Run backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```


## Notes

- All configuration is centralized in `app.config.Settings`
- Embedding model is cached in a Docker volume to avoid re-downloads