import os

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from db import Database


load_dotenv()


DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "data/rag.db",
)

MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "all-MiniLM-L6-v2",
)


print("Loading embedding model...")

model = SentenceTransformer(
    MODEL_NAME
)

print("Embedding model loaded.")


db = Database(
    DATABASE_PATH
)


app = FastAPI(
    title="EPFL Rocket Team RAG API",
)


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


class SearchResult(BaseModel):
    similarity: float
    id: int
    path: str
    title: str
    heading_path: str
    content: str
    url: str


@app.get("/")
def root():
    return {
        "name": "EPFL Rocket Team RAG API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


@app.post("/search")
def search(
    request: SearchRequest,
):
    print(
        f"Search request: {request.query}"
    )

    query_embedding = model.encode(
        request.query,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    results = db.semantic_search(
        query_embedding=query_embedding,
        limit=request.limit,
    )

    return {
        "query": request.query,
        "results": results,
    }

@app.get("/search")
def search_get(query: str):
    query_embedding = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    results = db.semantic_search(
        query_embedding=query_embedding,
        limit=5,
    )

    return {
        "query": query,
        "results": results,
    }
