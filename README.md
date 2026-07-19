# EPFL Rocket Team AI Knowledge Assistant

An AI-powered knowledge assistant for the EPFL Rocket Team.

The goal is to allow members to ask questions in natural language and receive answers based on the team's existing documentation, procedures, technical reports, tutorials, and other knowledge stored in Wiki.js.

The system is designed for a team of approximately 250 members and is built around the existing Wiki.js documentation rather than requiring the team to maintain a separate AI-specific knowledge base.

---

## For everyone

### What does this project do?

The EPFL Rocket Team has a large amount of documentation spread across many technical and management areas.

Instead of manually searching through hundreds of Wiki.js pages, a team member should eventually be able to ask a question such as:

> What is our biggest rocket?

or:

> How do I access the team's servers?

The system will search the team's existing documentation, find the most relevant information, and provide it to an AI model that can formulate an answer.

The original documentation remains the source of truth.

The AI assistant is intended to make the information easier to find, not to replace the Wiki.js documentation.

---

## How it works

The current system works approximately like this:

```text
┌────────────────────┐
│      Wiki.js       │
│  Team documentation│
└─────────┬──────────┘
          │
          │ Git repository
          ▼
┌────────────────────┐
│   Local Git clone  │
│    Markdown files  │
└─────────┬──────────┘
          │
          │ Ingestion
          ▼
┌────────────────────┐
│     Chunking       │
│ Split documents    │
│ into smaller parts │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│      SQLite        │
│ Documents + chunks │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│      SQLite        │
│       FTS5         │
│  Full-text search  │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│   Search results   │
└────────────────────┘
```

The future system will extend this with semantic search and an AI model:

```text
User question
      │
      ▼
┌────────────────────┐
│   Search system    │
└─────────┬──────────┘
          │
          ├──────────────────────┐
          ▼                      ▼
┌────────────────┐      ┌────────────────┐
│ Keyword search │      │ Semantic search│
│     FTS5        │      │   Embeddings   │
└────────┬───────┘      └────────┬───────┘
         │                       │
         └───────────┬───────────┘
                     ▼
             Relevant documents
                     │
                     ▼
              AI language model
                     │
                     ▼
                  Answer
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
5. Stores the chunks in the database.
6. Associates each chunk with its original document and URL.

The system is designed to support incremental updates.

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
Re-index that document
```

There is no need to reprocess the entire Wiki.js documentation every time one page changes.

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

---

## SQLite

SQLite is currently used as the local database.

The database stores:

### Documents

Information about original Markdown files.

### Chunks

The smaller pieces created during ingestion.

### Full-text search index

An SQLite FTS5 index is used to search the text efficiently.

The database can be rebuilt from the Git repository if necessary.

This means the database itself is derived data rather than the primary source of truth.

---

## Full-text search

The current implementation uses SQLite FTS5.

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

This allows users and future AI components to trace results back to the original documentation.

---

# Planned semantic search

Keyword search has an important limitation.

A user might ask:

> What is our biggest rocket?

The documentation may contain information about:

* Hyperion
* Firehorn
* Weisshorn
* Nordend
* rocket dimensions
* rocket mass

without ever containing the exact phrase:

```text
biggest rocket
```

Semantic search addresses this problem.

Instead of only looking for matching words, the system converts text into numerical representations called embeddings.

Conceptually:

```text
"What is our biggest rocket?"
              │
              ▼
       Question embedding
              │
              ▼
Compare with document embeddings
              │
              ▼
Find semantically similar content
```

The planned system will combine:

```text
Keyword search
      +
Semantic search
      │
      ▼
Hybrid retrieval
```

This should provide better results than either method alone.

---

# Planned AI question answering

The eventual question-answering system will work approximately like this:

```text
User asks a question
        │
        ▼
Search the knowledge base
        │
        ▼
Retrieve relevant chunks
        │
        ▼
Send relevant context to an LLM
        │
        ▼
Generate an answer
        │
        ▼
Show sources
```

The AI model should answer based on retrieved documentation rather than relying only on its internal knowledge.

The original Wiki.js pages should remain available as sources.

---

# Current status

## Completed

* [x] Clone Wiki.js documentation repository
* [x] Read Markdown documentation
* [x] Process hundreds of Markdown documents
* [x] Split documents into chunks
* [x] Store document metadata
* [x] Store chunk metadata
* [x] Store source URLs
* [x] Use SQLite as the database
* [x] Implement SQLite FTS5 full-text search
* [x] Search the documentation from the command line
* [x] Preserve the original document paths
* [x] Support incremental document ingestion

## Next

* [ ] Add semantic embeddings
* [ ] Implement vector similarity search
* [ ] Implement hybrid keyword + semantic search
* [ ] Improve retrieval ranking
* [ ] Add a question-answering API
* [ ] Add an LLM backend
* [ ] Return citations and source links
* [ ] Build a web chat interface
* [ ] Add authentication
* [ ] Automate Wiki.js Git updates
* [ ] Add monitoring and logging

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

These are ideas for future development and are not necessarily part of the current architecture.

---

# Development

## Requirements

* Python 3
* `uv`
* Git

The project uses `uv` for Python environment and dependency management.

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

Run search:

```bash
uv run python search.py
```

Example:

```text
Search (or 'exit'): it team
```

---

# Updating the knowledge base

The planned update workflow is:

```text
1. Pull changes from the Wiki.js Git repository
2. Detect changed Markdown files
3. Re-index changed files
4. Remove deleted documents
5. Update the search index
```

This can eventually be run automatically using a cron job or system service.

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
 Update index
```

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

A distributed vector database may become useful later, but is not necessary just because the project is an AI project.

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

This project is currently in the early development phase.

The initial ingestion and full-text search pipeline is operational.

The next major milestone is hybrid retrieval combining keyword search with semantic embeddings.
