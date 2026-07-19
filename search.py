import os

from dotenv import load_dotenv

from db import Database


load_dotenv()

DATABASE_PATH = os.environ["DATABASE_PATH"]


def main():
    db = Database(DATABASE_PATH)

    while True:
        query = input(
            "\nSearch (or 'exit'): "
        ).strip()

        if query.lower() == "exit":
            break

        if not query:
            continue

        results = db.search(
            query,
            limit=10,
        )

        if not results:
            print("No results.")
            continue

        for index, result in enumerate(
            results,
            start=1,
        ):
            print("\n" + "=" * 80)

            print(
                f"{index}. "
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
                result["content"][:1500]
            )


if __name__ == "__main__":
    main()
