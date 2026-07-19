import hashlib
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from db import Database
from markdown_parser import parse_markdown


load_dotenv()


REPOSITORY_PATH = Path(
    os.getenv(
        "REPOSITORY_PATH",
        "data/wiki",
    )
)

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "data/rag.db",
)

REPOSITORY_URL = os.getenv(
    "REPOSITORY_URL",
    "git@github.com:EPFLRocketTeam/ert_wiki.git",
)

WIKI_BASE_URL = os.getenv(
    "WIKI_BASE_URL",
    "https://rocket-team.epfl.ch",
)

MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "all-MiniLM-L6-v2",
)


def run_git(
    *arguments: str,
) -> str:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPOSITORY_PATH),
            *arguments,
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    return result.stdout.strip()


def synchronize_repository():
    if not REPOSITORY_PATH.exists():
        print(
            "Cloning Git repository..."
        )

        REPOSITORY_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        subprocess.run(
            [
                "git",
                "clone",
                REPOSITORY_URL,
                str(REPOSITORY_PATH),
            ],
            check=True,
        )

    else:
        print(
            "Synchronizing Git repository..."
        )

        subprocess.run(
            [
                "git",
                "-C",
                str(REPOSITORY_PATH),
                "pull",
                "--ff-only",
            ],
            check=True,
        )


def get_file_hash(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open(
        "rb"
    ) as file:
        while True:
            chunk = file.read(
                1024 * 1024
            )

            if not chunk:
                break

            hasher.update(
                chunk
            )

    return hasher.hexdigest()


def build_wiki_url(
    path: Path,
) -> str:
    relative_path = path.relative_to(
        REPOSITORY_PATH
    )

    relative_path_without_extension = (
        relative_path.with_suffix("")
    )

    return (
        f"{WIKI_BASE_URL}/"
        f"{relative_path_without_extension}"
    )


def process_file(
    db: Database,
    model: SentenceTransformer,
    path: Path,
    commit_hash: str,
):
    relative_path = path.relative_to(
        REPOSITORY_PATH
    )

    relative_path_string = str(
        relative_path
    )

    print(
        f"A: {relative_path_string}"
    )

    markdown = path.read_text(
        encoding="utf-8"
    )

    document = parse_markdown(
        markdown
    )

    chunks = document["chunks"]

    if not chunks:
        print(
            f"Skipping empty document: "
            f"{relative_path_string}"
        )

        return

    texts = [
        chunk["content"]
        for chunk in chunks
    ]

    print(
        f"Generating embeddings for "
        f"{len(texts)} chunks..."
    )

    embeddings = model.encode(
        texts,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    content_hash = get_file_hash(
        path
    )

    db.insert_document(
        path=relative_path_string,
        content_hash=content_hash,
        title=document["title"],
        url=build_wiki_url(path),
        git_commit=commit_hash,
        chunks=chunks,
        embeddings=embeddings,
    )

    print(
        f"Indexed {relative_path_string}: "
        f"{len(chunks)} chunks"
    )


def get_changed_files(
    previous_commit: str | None,
    current_commit: str,
) -> list[str]:
    if previous_commit is None:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(REPOSITORY_PATH),
                "ls-files",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        return [
            path
            for path in result.stdout.splitlines()
            if path.endswith(
                ".md"
            )
        ]

    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPOSITORY_PATH),
            "diff",
            "--name-only",
            previous_commit,
            current_commit,
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    return [
        path
        for path in result.stdout.splitlines()
        if path.endswith(
            ".md"
        )
    ]


def main():
    synchronize_repository()

    db = Database(
        DATABASE_PATH
    )

    print(
        "Loading embedding model..."
    )

    model = SentenceTransformer(
        MODEL_NAME
    )

    print(
        "Embedding model loaded."
    )

    previous_commit = (
        db.get_indexed_commit(
            str(REPOSITORY_PATH)
        )
    )

    current_commit = run_git(
        "rev-parse",
        "HEAD",
    )

    print(
        f"Previous indexed commit: "
        f"{previous_commit}"
    )

    print(
        f"Current repository commit: "
        f"{current_commit}"
    )

    if previous_commit == current_commit:
        print(
            "Repository has not changed."
        )

        return

    changed_files = get_changed_files(
        previous_commit,
        current_commit,
    )

    print(
        f"Found {len(changed_files)} "
        f"changed files."
    )

    for file_path in changed_files:
        absolute_path = (
            REPOSITORY_PATH
            / file_path
        )

        if not absolute_path.exists():
            print(
                f"Deleting removed document: "
                f"{file_path}"
            )

            db.delete_document(
                file_path
            )

            continue

        process_file(
            db=db,
            model=model,
            path=absolute_path,
            commit_hash=current_commit,
        )

    db.set_indexed_commit(
        repository=str(
            REPOSITORY_PATH
        ),
        commit_hash=current_commit,
    )

    print(
        "Ingestion complete. "
        f"Indexed commit {current_commit}"
    )


if __name__ == "__main__":
    main()
