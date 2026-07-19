import os

from dotenv import load_dotenv
from mistralai.client import Mistral
from sentence_transformers import SentenceTransformer

from db import Database


load_dotenv()


DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "data/rag.db",
)


EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "all-MiniLM-L6-v2",
)


MISTRAL_API_KEY = os.environ[
    "MISTRAL_API_KEY"
]


MISTRAL_MODEL = os.getenv(
    "MISTRAL_MODEL",
    "ministral-14b-2512",
)


SYSTEM_PROMPT = """
You are the EPFL Rocket Team wiki assistant.

Answer the user's question using only the provided wiki context.

Rules:
- Do not invent information.
- Do not use outside knowledge.
- If the answer cannot be found in the provided context, say that you could not find the answer in the wiki.
- Prefer specific information over generic information.
- Give a concise but useful answer.
- When relevant, mention the source title and section.
"""


def build_context(
    results: list[dict],
) -> str:
    sections = []

    for index, result in enumerate(
        results,
        start=1,
    ):
        sections.append(
            f"""
SOURCE {index}

Title:
{result["title"]}

Section:
{result["heading_path"]}

Path:
{result["path"]}

URL:
{result["url"]}

Content:
{result["content"]}
"""
        )

    return "\n".join(
        sections
    )


def combine_results(
    semantic_results: list[dict],
    keyword_results: list[dict],
) -> list[dict]:
    """
    Combine semantic and keyword search results
    using Reciprocal Rank Fusion (RRF).
    """

    scores = {}

    results_by_id = {}

    k = 60

    for rank, result in enumerate(
        semantic_results,
        start=1,
    ):
        result_id = result["id"]

        results_by_id[
            result_id
        ] = result

        scores[
            result_id
        ] = scores.get(
            result_id,
            0.0,
        ) + (
            1.0
            / (
                k
                + rank
            )
        )

    for rank, result in enumerate(
        keyword_results,
        start=1,
    ):
        result_id = result["id"]

        results_by_id[
            result_id
        ] = result

        scores[
            result_id
        ] = scores.get(
            result_id,
            0.0,
        ) + (
            1.0
            / (
                k
                + rank
            )
        )

    ranked_ids = sorted(
        scores,
        key=lambda result_id: scores[
            result_id
        ],
        reverse=True,
    )

    return [
        results_by_id[
            result_id
        ]
        for result_id in ranked_ids
    ]


def ask_mistral(
    client: Mistral,
    question: str,
    context: str,
) -> str:
    response = client.chat.complete(
        model=MISTRAL_MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"""
Wiki context:

{context}

User question:

{question}
""",
            },
        ],
    )

    return (
        response.choices[0]
        .message
        .content
    )


def main():
    print(
        "Loading embedding model..."
    )

    embedding_model = SentenceTransformer(
        EMBEDDING_MODEL
    )

    print(
        "Embedding model loaded."
    )

    print(
        "Connecting to database..."
    )

    db = Database(
        DATABASE_PATH
    )

    print(
        "Connecting to Mistral..."
    )

    client = Mistral(
        api_key=MISTRAL_API_KEY
    )

    print(
        "Ready."
    )

    while True:
        try:
            question = input(
                "\nQuestion (or 'exit'): "
            ).strip()

        except (
            EOFError,
            KeyboardInterrupt,
        ):
            print()
            break

        if question.lower() == "exit":
            break

        if not question:
            continue

        print()
        print(
            "Generating query embedding..."
        )

        query_embedding = (
            embedding_model.encode(
                question,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        )

        semantic_results = (
            db.semantic_search(
                query_embedding=query_embedding,
                limit=5,
            )
        )

        keyword_rows = db.search(
            query=question,
            limit=5,
        )

        keyword_results = [
            dict(row)
            for row in keyword_rows
        ]

        results = combine_results(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
        )

        results = results[
            :6
        ]

        if not results:
            print()
            print(
                "No relevant wiki content found."
            )

            continue

        context = build_context(
            results
        )

        print()
        print(
            "Asking Mistral..."
        )

        answer = ask_mistral(
            client=client,
            question=question,
            context=context,
        )

        print()
        print(
            "=" * 80
        )

        print(
            "ANSWER"
        )

        print(
            "=" * 80
        )

        print()
        print(
            answer
        )

        print()
        print(
            "-" * 80
        )

        print(
            "SOURCES"
        )

        print(
            "-" * 80
        )

        printed_urls = set()

        for result in results:
            url = result["url"]

            if url in printed_urls:
                continue

            printed_urls.add(
                url
            )

            print(
                f"- {result['title']}"
            )

            print(
                f"  {url}"
            )


if __name__ == "__main__":
    main()
