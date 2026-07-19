import os

from dotenv import load_dotenv
from mistralai.client import Mistral
from sentence_transformers import SentenceTransformer

from db import Database
from mcp.server.mcpserver import MCPServer


load_dotenv()


DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "data/rag.db",
)


MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "all-MiniLM-L6-v2",
)


MISTRAL_API_KEY = os.getenv(
    "MISTRAL_API_KEY"
)


MISTRAL_MODEL = os.getenv(
    "MISTRAL_MODEL",
    "ministral-14b-2512",
)


if not MISTRAL_API_KEY:
    raise RuntimeError(
        "MISTRAL_API_KEY is not configured"
    )


print(
    "Loading embedding model...",
    file=__import__("sys").stderr,
)


embedding_model = SentenceTransformer(
    MODEL_NAME
)


print(
    "Embedding model loaded.",
    file=__import__("sys").stderr,
)


db = Database(
    DATABASE_PATH
)


mistral_client = Mistral(
    api_key=MISTRAL_API_KEY
)


mcp = MCPServer(
    name="EPFL Rocket Team Knowledge Base",
)


@mcp.tool()
def search_knowledge_base(
    query: str,
    limit: int = 5,
) -> list[dict]:
    """
    Search the EPFL Rocket Team knowledge base.

    Use this tool to find relevant information in the
    team's internal documentation, technical documents,
    tutorials, procedures, and organizational pages.

    Args:
        query:
            The natural-language question or search query.

        limit:
            Maximum number of results to return.
            Defaults to 5.
    """

    if not query.strip():
        return []

    limit = max(
        1,
        min(
            limit,
            20,
        ),
    )


    query_embedding = embedding_model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )


    semantic_results = db.semantic_search(
        query_embedding=query_embedding,
        limit=limit,
    )


    keyword_rows = db.search(
        query=query,
        limit=limit,
    )


    keyword_results = [
        dict(row)
        for row in keyword_rows
    ]


    results = []


    for result in semantic_results:
        results.append(
            {
                "type": "semantic",
                "similarity": result["similarity"],
                "title": result["title"],
                "section": result["heading_path"],
                "path": result["path"],
                "url": result["url"],
                "content": result["content"],
            }
        )


    for result in keyword_results:
        results.append(
            {
                "type": "keyword",
                "score": result["score"],
                "title": result["title"],
                "section": result["heading_path"],
                "path": result["path"],
                "url": result["url"],
                "content": result["content"],
            }
        )


    return results


@mcp.tool()
def answer_question(
    question: str,
    limit: int = 8,
) -> str:
    """
    Answer a question about the EPFL Rocket Team
    using information retrieved from the knowledge base.

    This tool searches the documentation and then
    uses the Mistral language model to generate an answer.

    Args:
        question:
            The user's natural-language question.

        limit:
            Number of knowledge-base results to provide
            to the language model.
    """

    if not question.strip():
        return (
            "Please provide a question."
        )


    search_results = search_knowledge_base(
        query=question,
        limit=limit,
    )


    if not search_results:
        return (
            "I could not find relevant information "
            "in the EPFL Rocket Team knowledge base."
        )


    context_parts = []


    for index, result in enumerate(
        search_results,
        start=1,
    ):
        context_parts.append(
            f"""
SOURCE {index}

Title:
{result["title"]}

Section:
{result["section"]}

Path:
{result["path"]}

URL:
{result["url"]}

Content:
{result["content"]}
"""
        )


    context = "\n".join(
        context_parts
    )


    prompt = f"""
You are an assistant for the EPFL Rocket Team.

Answer the user's question using the provided
knowledge-base sources.

Rules:

1. Use the sources as your primary source of truth.
2. Do not invent information.
3. If the sources do not contain enough information,
   say that clearly.
4. Give a concise but useful answer.
5. Include relevant source URLs at the end.
6. If the sources disagree, mention the disagreement.

USER QUESTION:

{question}


KNOWLEDGE-BASE SOURCES:

{context}
"""


    response = mistral_client.chat.complete(
        model=MISTRAL_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )


    return response.choices[0].message.content


if __name__ == "__main__":
    mcp.run()
    print(
        "Starting ERT RAG MCP server...",
        file=sys.stderr,
        flush=True,
    )

    print(
        "Transport: stdio",
        file=sys.stderr,
        flush=True,
    )

    print(
        "Status: running and waiting for MCP client connection",
        file=sys.stderr,
        flush=True,
    )

