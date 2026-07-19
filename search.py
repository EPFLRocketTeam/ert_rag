from sentence_transformers import SentenceTransformer

from db import Database

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "data/rag.db",
)

MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "all-MiniLM-L6-v2",
)

def print_result(
    number: int,
    result: dict,
    result_type: str,
):
    print()
    print("=" * 80)
    print(
        f"{result_type} RESULT {number}"
    )
    print("=" * 80)

    if result_type == "SEMANTIC":
        print(
            f"Similarity: "
            f"{result['similarity']:.4f}"
        )

    elif result_type == "KEYWORD":
        print(
            f"BM25 score: "
            f"{result['score']:.4f}"
        )

    print(
        f"Title: "
        f"{result['title']}"
    )

    print(
        f"Section: "
        f"{result['heading_path']}"
    )

    print(
        f"Path: "
        f"{result['path']}"
    )

    print(
        f"URL: "
        f"{result['url']}"
    )

    print()

    print(
        result["content"]
    )


def main():
    print(
        "Loading embedding model..."
    )

    model = SentenceTransformer(
        MODEL_NAME
    )

    print(
        "Embedding model loaded."
    )

    db = Database(
        DATABASE_PATH
    )

    while True:
        try:
            query = input(
                "\nSearch (or 'exit'): "
            ).strip()

        except (
            EOFError,
            KeyboardInterrupt,
        ):
            print()
            break

        if query.lower() == "exit":
            break

        if not query:
            continue

        print()
        print(
            "Generating query embedding..."
        )

        query_embedding = model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        semantic_results = (
            db.semantic_search(
                query_embedding=query_embedding,
                limit=5,
            )
        )

        keyword_rows = db.search(
            query=query,
            limit=5,
        )

        keyword_results = [
            dict(row)
            for row in keyword_rows
        ]

        print()
        print(
            "\n"
            + "#" * 80
        )

        print(
            "SEMANTIC SEARCH RESULTS"
        )

        print(
            "#" * 80
        )

        if not semantic_results:
            print(
                "No semantic results found."
            )

        else:
            for index, result in enumerate(
                semantic_results,
                start=1,
            ):
                print_result(
                    number=index,
                    result=result,
                    result_type="SEMANTIC",
                )

        print()
        print(
            "\n"
            + "#" * 80
        )

        print(
            "KEYWORD SEARCH RESULTS"
        )

        print(
            "#" * 80
        )

        if not keyword_results:
            print(
                "No keyword results found."
            )

        else:
            for index, result in enumerate(
                keyword_results,
                start=1,
            ):
                print_result(
                    number=index,
                    result=result,
                    result_type="KEYWORD",
                )


if __name__ == "__main__":
    main()
