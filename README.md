# EPFL Rocket Team AI Knowledge Assistant

An AI-powered knowledge assistant for the EPFL Rocket Team.

The goal is to allow members to ask questions in natural language and receive answers based on the team's existing documentation, procedures, technical reports, tutorials, and other knowledge stored in Wiki.js.

The system is designed for a team of approximately 250 members and is built around the existing Wiki.js documentation rather than requiring the team to maintain a separate AI-specific knowledge base.

---

## For everyone

### What does this project do?

The EPFL Rocket Team has a large amount of documentation spread across many technical and management areas.

Instead of manually searching through hundreds of Wiki.js pages, a team member can ask a question such as:

> What is our biggest rocket?

or:

> How do I access the team's servers?

The system searches the team's existing documentation and finds the most relevant information.

The current system provides semantic search through a REST API. The next step is to pass the retrieved documentation to a large language model to generate complete answers.

The original documentation remains the source of truth.

The AI assistant is intended to make information easier to find, not to replace the Wiki.js documentation.

---

## Current architecture

```text
                         ┌──────────────────────┐
                         │       Wiki.js        │
                         │  Team documentation  │
                         └──────────┬───────────┘
                                    │
                                    │ Git repository
                                    ▼
                         ┌──────────────────────┐
                         │    Local Git clone   │
                         │    Markdown files    │
                         └──────────┬───────────┘
                                    │
                                    │ Ingestion
                                    ▼
                         ┌──────────────────────┐
                         │      Chunking        │
                         │  Split documents     │
                         │  into smaller parts  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       SQLite         │
                         │ Documents + chunks   │
                         └──────────┬───────────┘
                                    │
                      ┌─────────────┴─────────────┐
                      ▼                           ▼
             ┌────────────────┐          ┌────────────────┐
             │  SQLite FTS5   │          │   Embeddings   │
             │ Keyword search │          │ Semantic search│
             └────────┬───────┘          └────────┬───────┘
                      │                           │
                      └─────────────┬─────────────┘
                                    ▼
                         ┌──────────────────────┐
                         │   Search results     │
                         │  Relevant chunks     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      FastAPI         │
                         │      REST API        │
                         └──────────┬───────────┘
                                    │
                                    ▼
                    https://rag.epfl-rocket-team.ch
```

The planned question-answering layer will extend this architecture:

```text
User question
      │
      ▼
┌────────────────────┐
│     FastAPI API    │
└─────────┬──────────┘
          │
          ▼
┌────────────────────────────┐
│       Hybrid retrieval     │
│                            │
│  Keyword search + semantic │
│       search + reranking   │
└─────────────┬──────────────┘
              │
              ▼
       Relevant chunks
              │
              ▼
        Mistral API
              │
              ▼
           Answer
              │
              ▼
      Sources and citations
```

---

# Technical architecture

## Source of truth: Wiki.js

The team's Wiki.js installation contains the original documentation.

The Wiki.js content is also available as a Git repository containing Markdown files.

This project uses the Git repository as its local source of documentation.

This has several advantages:

* The original Wiki.js documentation remains unchanged.
* The AI system can be updated automatically.
* Git provides a history of document changes.
* The ingestion system can process only changed files.
* The entire knowledge base can be rebuilt from the source repository.

The Wiki.js repository is cloned locally and periodically updated using Git.

---

## Markdown documents

The documentation is stored primarily as Markdown files.

Examples include:

```text
management/2025_management/2025_M_IT.md
icarus/avionics/2025_I_AV_SW_MAXON_SUM.md
tutorials/beginners_guide.md
competition/firehorn/...
```

The directory structure itself contains useful information about the documentation.

For example:

```text
icarus/
└── avionics/
    └── software/
        └── Drivers/
            └── 2025_I_AV_SW_DRIVERS_GNSS.md
```

The path can help identify the context of a document.

---

## Ingestion

The ingestion process reads Markdown files from the local Wiki.js Git repository.

For every document, the system:

1. Reads the Markdown file.
2. Extracts the document title.
3. Identifies headings.
4. Splits the document into smaller chunks.
5. Generates an embedding for each chunk.
6. Stores the chunks in the database.
7. Associates each chunk with its original document and URL.

The system supports incremental updates.

When a Wiki.js document changes:

```text
Wiki.js
   │
   ▼
Git commit
   │
   ▼
git pull
   │
   ▼
Changed Markdown file
   │
   ▼
Re-index changed document
   │
   ▼
Update database
```

There is no need to reprocess the entire Wiki.js documentation every time one page changes.

The ingestion system tracks the previously indexed Git commit and detects changed files.

---

## Chunking

Large documents are split into smaller pieces called chunks.

For example:

```text
Document
│
├── Introduction
│
├── Hardware
│
├── Software
│
├── Testing
│
└── Results
```

can become:

```text
Chunk 1: Introduction
Chunk 2: Hardware
Chunk 3: Software
Chunk 4: Testing
Chunk 5: Results
```

The goal is to make each chunk small enough to retrieve efficiently while retaining enough context to be useful.

Each chunk stores metadata such as:

* Document path
* Document title
* Heading path
* Original URL
* Content
* Embedding

---

## SQLite

SQLite is currently used as the local database.

The database stores:

### Documents

Information about original Markdown files.

### Chunks

The smaller pieces created during ingestion.

### Embeddings

Numerical vector representations of chunks used for semantic similarity search.

### Full-text search index

An SQLite FTS5 index is used to search the text efficiently.

The database can be rebuilt from the Git repository if necessary.

This means the database itself is derived data rather than the primary source of truth.

---

# Search

## Keyword search

The system uses SQLite FTS5 for full-text search.

For example, a query such as:

```text
it team
```

can retrieve relevant documentation containing those terms.

The search results include:

* Title
* Section
* File path
* Wiki.js URL
* Relevant content

---

## Semantic search

The system also uses embeddings to find conceptually similar documentation.

Instead of only looking for matching words, the system converts text into numerical representations called embeddings.

Conceptually:

```text
"What is our biggest rocket?"
              │
              ▼
       Query embedding
              │
              ▼
   Compare with chunk embeddings
              │
              ▼
    Find semantically similar
           content
```

The current embedding model is configured through the `EMBEDDING_MODEL` environment variable.

The default model is:

```text
all-MiniLM-L6-v2
```

The embedding model is used both during ingestion and when generating query embeddings.

Embeddings are normalized, allowing cosine similarity to be used for ranking.

---

## Hybrid retrieval

The system currently exposes both retrieval mechanisms:

```text
              User query
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
   Keyword search     Semantic search
      FTS5              Embeddings
        │                   │
        └─────────┬─────────┘
                  ▼
          Search results
```

The current API endpoint returns semantic search results.

The keyword search functionality is also implemented in the database layer and can be combined with semantic results in a future retrieval-ranking stage.

A future hybrid retrieval system will combine both methods:

```text
Keyword search
      +
Semantic search
      │
      ▼
Result fusion / reranking
      │
      ▼
Best relevant chunks
```

This should provide better results than either method alone.

---

# REST API

The search system is exposed through a FastAPI REST API.

The production API is available at:

```text
https://rag.epfl-rocket-team.ch
```

## Root endpoint

```http
GET /
```

Example response:

```json
{
  "name": "EPFL Rocket Team RAG API",
  "status": "running"
}
```

---

## Health endpoint

```http
GET /health
```

Example response:

```json
{
  "status": "ok"
}
```

---

## Semantic search endpoint

```http
POST /search
```

Request:

```json
{
  "query": "How do I access the servers?",
  "limit": 5
}
```

Example using `curl`:

```bash
curl -X POST \
  "https://rag.epfl-rocket-team.ch/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I access the servers?",
    "limit": 5
  }'
```

The API returns relevant documentation chunks together with their similarity scores and source URLs.

Example:

```json
{
  "query": "How do I access the servers?",
  "results": [
    {
      "similarity": 0.4461,
      "id": 21359,
      "path": "competition/firehorn/ground-segment/control-station/2024_C_GS_GSC_DJF.md",
      "title": "Introduction",
      "heading_path": "Software Design > Software Components Design > Aspects of Each Component > Server",
      "content": "...",
      "url": "https://rocket-team.epfl.ch/..."
    }
  ]
}
```

FastAPI automatically generates interactive API documentation at:

```text
/docs
```

---

# Planned AI question answering

The next major layer is a question-answering endpoint.

The planned flow is:

```text
User asks a question
        │
        ▼
   Generate query
     embedding
        │
        ▼
 Search knowledge base
        │
        ▼
 Retrieve relevant chunks
        │
        ▼
 Build context
        │
        ▼
 Send context to Mistral API
        │
        ▼
 Generate answer
        │
        ▼
 Return answer + sources
```

The planned API will look approximately like:

```http
POST /ask
```

Request:

```json
{
  "query": "How do I access the servers?"
}
```

Response:

```json
{
  "query": "How do I access the servers?",
  "answer": "According to the documentation...",
  "sources": [
    {
      "title": "How to Flash Boards",
      "url": "https://rocket-team.epfl.ch/..."
    }
  ]
}
```

The LLM will receive retrieved documentation as context and should answer based primarily on that context rather than relying only on its internal knowledge.

The planned LLM backend is the Mistral API, using a Ministral model such as:

```text
ministral-14b-2512
```

The API key is stored in environment variables and is not committed to the repository.

---

# Current status

## Completed

* [x] Clone Wiki.js documentation repository
* [x] Read Markdown documentation
* [x] Process thousands of Markdown files
* [x] Split documents into chunks
* [x] Store document metadata
* [x] Store chunk metadata
* [x] Store source URLs
* [x] Use SQLite as the database
* [x] Implement SQLite FTS5 full-text search
* [x] Search the documentation from the command line
* [x] Preserve original document paths
* [x] Support incremental document ingestion
* [x] Generate embeddings for document chunks
* [x] Generate query embeddings
* [x] Implement semantic similarity search
* [x] Expose semantic search through FastAPI
* [x] Add health-check endpoint
* [x] Deploy the API behind `rag.epfl-rocket-team.ch`
* [x] Generate automatic OpenAPI documentation

## Next

* [ ] Implement hybrid keyword + semantic retrieval
* [ ] Improve retrieval ranking
* [ ] Add result reranking
* [ ] Add `/ask` question-answering endpoint
* [ ] Add Mistral LLM backend
* [ ] Return generated answers with citations
* [ ] Build a web chat interface
* [ ] Add authentication
* [ ] Automate Wiki.js Git updates
* [ ] Add monitoring and logging
* [ ] Add retrieval-quality evaluation

## Future ideas

Potential future improvements include:

* Automatic document classification
* Automatic metadata extraction
* Automatic tagging
* Knowledge graphs
* Search analytics
* User feedback on answers
* Retrieval quality evaluation
* Local LLM support
* Browser-based LLM support
* Model comparison and evaluation
* MCP server integration
* Integration with Flowise or other AI orchestration systems

These are ideas for future development and are not necessarily part of the current architecture.

---

# Development

## Requirements

* Python 3.12+
* `uv`
* Git

The project uses `uv` for Python environment and dependency management.

---

## Environment variables

Configuration is provided through environment variables.

Example:

```env
DATABASE_PATH=data/rag.db
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

The Mistral API key is kept outside the repository:

```env
MISTRAL_API_KEY=...
```

Environment files containing secrets must not be committed to Git.

---

## Running the project

Install dependencies:

```bash
uv sync
```

Run ingestion:

```bash
uv run python ingest.py
```

Run command-line search:

```bash
uv run python search.py
```

Run the API locally:

```bash
uv run uvicorn api:app \
  --host 0.0.0.0 \
  --port 8000
```

The API will then be available locally at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

---

# Updating the knowledge base

The update workflow is:

```text
1. Pull changes from the Wiki.js Git repository
2. Detect changed Markdown files
3. Generate embeddings for changed files
4. Re-index changed files
5. Remove deleted documents
6. Update the search index
```

The ingestion system tracks the previously indexed Git commit.

For example:

```text
Every 10 minutes
        │
        ▼
     git pull
        │
        ▼
  Detect changes
        │
        ▼
 Generate embeddings
        │
        ▼
    Update index
```

This can eventually be automated using a cron job, system service, container restart workflow, or scheduled deployment.

---

# Design principles

## Wiki.js remains the source of truth

The AI system should not become a second independent documentation system.

The original Wiki.js documentation remains authoritative.

---

## Prefer simple systems

The project should use the simplest architecture that solves the problem.

New technologies should only be added when they provide a clear benefit.

For example:

```text
SQLite
```

is currently sufficient for the first version.

A distributed vector database may become useful later, but is not necessary simply because the project is an AI project.

---

## Keep sources traceable

Every answer should eventually be traceable to the original Wiki.js documentation.

A user should be able to ask:

> Where did this answer come from?

and receive a link to the relevant source page.

---

## Support future generations

The EPFL Rocket Team changes members every year.

The system should therefore be:

* Easy to understand
* Easy to deploy
* Easy to maintain
* Easy to rebuild
* Well documented

A future IT team should be able to understand and operate the project without relying on the original developers.

---

# Project status

This project has progressed from an initial ingestion prototype into a working semantic search service.

The current system:

```text
Wiki.js Git repository
        │
        ▼
Incremental ingestion
        │
        ▼
Markdown chunking
        │
        ▼
Embedding generation
        │
        ▼
SQLite database
        │
        ▼
Semantic search
        │
        ▼
FastAPI REST API
        │
        ▼
rag.epfl-rocket-team.ch
```

The next major milestone is to combine the retrieval system with a Mistral language model to provide complete answers grounded in the EPFL Rocket Team's documentation.

The long-term goal is to make the team's existing knowledge significantly easier to discover while keeping the original Wiki.js documentation as the authoritative source.
