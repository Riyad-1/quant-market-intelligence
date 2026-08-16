# Quant Market Intelligence

A trading and investing research/knowledge intelligence platform that transforms source materials (books, papers, interviews, research notes) into a searchable, evidence-backed trading knowledge base.

## Project Purpose

Quant Market Intelligence ingests, understands, organises, retrieves and analyses large amounts of trading and investing knowledge from:

- Trading books
- Investing books  
- Academic research papers
- Trader/investor interviews
- Strategy documents
- Research notes
- Historical market research
- Documented methodologies of successful traders/investors

The system transforms these materials into a **searchable, evidence-backed trading knowledge base** with full provenance tracking.

### Core Principle: Provenance

> Every piece of extracted trading knowledge must remain traceable to the original source that justified it.

Every extracted item retains provenance: document, author, publication, page, chapter, section, chunk, and exact source reference.

## Architecture

```
quant-market-intelligence/
├── app/
│   ├── api/              # FastAPI routes and schemas
│   ├── core/             # Configuration and logging
│   ├── db/               # Database models, repositories, session
│   ├── ingestion/        # Document parsing and chunking
│   ├── embeddings/       # Embedding provider abstraction
│   ├── retrieval/        # Search and retrieval
│   ├── llm/              # LLM provider abstraction
│   └── main.py           # Application entry point
├── tests/                # Test suite
├── migrations/           # Alembic database migrations
├── docker-compose.yml    # Docker services
└── pyproject.toml        # Project dependencies
```

## Technology Stack

- **Python**: 3.12+
- **Web Framework**: FastAPI
- **Database**: PostgreSQL with pgvector
- **ORM**: SQLAlchemy 2 (async)
- **Migrations**: Alembic
- **Validation**: Pydantic
- **Testing**: pytest, pytest-asyncio
- **Containerisation**: Docker Compose
- **Document Parsing**: PyMuPDF (behind abstraction)
- **Embeddings**: OpenAI (with provider abstraction for future alternatives)
- **LLM**: OpenAI (with provider abstraction for future alternatives)

## Local Development Setup

### Prerequisites

- Python 3.12 or higher
- Docker and Docker Compose (for database)
- pip or Poetry for dependency management

### 1. Clone and Install Dependencies

```bash
cd quant-market-intelligence
pip install -e .
```

Or with Poetry:

```bash
poetry install
```

### 2. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and set your values:

```env
# OpenAI API key (required for embeddings and LLM features)
OPENAI_API_KEY=your-api-key-here

# Database configuration (defaults work with Docker Compose)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/quant_intelligence
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=quant_intelligence
```

### 3. Start Database with Docker Compose

```bash
docker compose up -d postgres
```

Wait for PostgreSQL to be ready (about 10-15 seconds).

### 4. Run Database Migrations

```bash
alembic upgrade head
```

### 5. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

Interactive API docs at `http://localhost:8000/docs`.

### 6. Run Tests

```bash
pytest tests/ -v
```

## API Endpoints

### Health Check

```bash
GET /health
```

Returns application health status.

### Documents (Phase 2)

```bash
POST /documents          # Upload a PDF document
GET  /documents          # List all documents
GET  /documents/{id}     # Get document details
DELETE /documents/{id}   # Delete a document
GET  /documents/{id}/chunks  # List document chunks
```

### Search (Phase 3)

```bash
GET  /search?q=query     # Semantic search
POST /search             # Advanced search with filters
```

## Implementation Status

### Phase 1 — Project Foundation ✅

- [x] Python project setup with pyproject.toml
- [x] FastAPI application structure
- [x] PostgreSQL + pgvector configuration
- [x] SQLAlchemy 2 async ORM setup
- [x] Alembic migrations
- [x] Docker Compose configuration
- [x] Environment-based configuration
- [x] Health endpoint
- [x] Structured logging
- [x] pytest setup

### Phase 2 — Document Ingestion ✅

- [x] PDF parser abstraction
- [x] PyMuPDF implementation
- [x] Text normalisation
- [x] Configurable chunking with overlap
- [x] Deterministic chunk IDs
- [x] Document hash for deduplication
- [x] Document upload API
- [x] Duplicate ingestion protection

### Phase 3 — Embeddings ✅

- [x] Embedding provider abstraction
- [x] OpenAI embedding provider
- [x] Embedding service with batching
- [x] pgvector storage integration
- [x] Rate limit and error handling
- [x] Re-embedding support

### Future Phases (Not Yet Implemented)

- Phase 4: Retrieval (hybrid search, reranking)
- Phase 5: RAG Research (grounded Q&A)
- Phase 6: Concept Extraction
- Phase 7: Strategy Extraction
- Phase 8: Strategy Comparison
- Phase 9: Research Hypotheses

## Security Notes

- Never commit `.env` files with real credentials
- Set `OPENAI_API_KEY` via environment variables
- Uploaded documents are treated as untrusted input
- File uploads have size limits and type validation

## Roadmap

1. **Retrieval Enhancements**: Hybrid search, metadata filtering, reranking
2. **RAG Research**: Grounded question answering with citations
3. **Concept Extraction**: Identify and link trading concepts
4. **Strategy Extraction**: Extract structured strategy rules from sources
5. **Strategy Comparison**: Compare methodologies across traders
6. **Hypothesis Generation**: Generate testable quantitative hypotheses

## License

Private project.