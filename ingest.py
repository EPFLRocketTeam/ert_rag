import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv

from db import Database
from git_sync import (
    clone_or_pull,
    get_changed_files,
    get_current_commit,
)
from markdown_parser import parse_markdown


load_dotenv()


REPO_URL = os.environ["WIKI_REPO_URL"]
REPO_PATH = os.environ["WIKI_REPO_PATH"]
DATABASE_PATH = os.environ["DATABASE_PATH"]
WIKI_BASE_URL = os.environ["WIKI_BASE_URL"].rstrip("/")


def sha256(content: str) -> str:
    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def create_page_url(path: str) -> str:
    """
    Converts a Git path like:

        avionics/flight-computer.md

    into:

        https://wiki.example.com/avionics/flight-computer
    """

    path_without_extension = os.path.splitext(path)[0]

    return (
        f"{WIKI_BASE_URL}/"
        f"{path_without_extension}"
    )


def process_file(
    db: Database,
    repo_path: str,
    relative_path: str,
    commit_hash: str,
):
    file_path = Path(repo_path) / relative_path

    if not file_path.exists():
        print(f"File does not exist: {relative_path}")
        return

    markdown = file_path.read_text(
        encoding="utf-8"
    )

    content_hash = sha256(markdown)

    existing = db.get_document(relative_path)

    # Avoid reprocessing if content did not actually change.
    if (
        existing
        and existing["content_hash"] == content_hash
    ):
        print(
            f"Skipping unchanged file: "
            f"{relative_path}"
        )

        return

    title, chunks = parse_markdown(markdown)

    if not chunks:
        print(
            f"Skipping empty file: "
            f"{relative_path}"
        )

        return

    url = create_page_url(relative_path)

    db.insert_document(
        path=relative_path,
        content_hash=content_hash,
        title=title,
        url=url,
        git_commit=commit_hash,
        chunks=chunks,
    )

    print(
        f"Indexed {relative_path}: "
        f"{len(chunks)} chunks"
    )


def main():
    print("Synchronizing Git repository...")

    clone_or_pull(
        REPO_URL,
        REPO_PATH,
    )

    current_commit = get_current_commit(
        REPO_PATH
    )

    db = Database(DATABASE_PATH)

    old_commit = db.get_indexed_commit(
        REPO_URL
    )

    print(f"Previous indexed commit: {old_commit}")
    print(f"Current repository commit: {current_commit}")

    if old_commit == current_commit:
        print("No new commits.")
        return

    changed_files = get_changed_files(
        REPO_PATH,
        old_commit,
        current_commit,
    )

    print(
        f"Found {len(changed_files)} changed files."
    )

    for status, relative_path in changed_files:
        print(
            f"{status}: {relative_path}"
        )

        if status == "D":
            db.delete_document(
                relative_path
            )

            print(
                f"Deleted from index: "
                f"{relative_path}"
            )

        elif status in {"A", "M"}:
            process_file(
                db,
                REPO_PATH,
                relative_path,
                current_commit,
            )

    # Only update the commit AFTER everything succeeded.
    db.set_indexed_commit(
        REPO_URL,
        current_commit,
    )

    print(
        f"Ingestion complete. "
        f"Indexed commit {current_commit}"
    )


if __name__ == "__main__":
    main()
