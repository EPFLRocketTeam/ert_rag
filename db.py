import sqlite3
from pathlib import Path
from typing import Optional


class Database:
    def __init__(self, database_path: str):
        Path(database_path).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.connection = sqlite3.connect(
            database_path
        )

        self.connection.row_factory = sqlite3.Row

        self.connection.execute(
            "PRAGMA journal_mode=WAL"
        )

        self.initialize()

    def initialize(self):
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS ingestion_state (
                repository TEXT PRIMARY KEY,
                commit_hash TEXT NOT NULL,
                indexed_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS documents (
                path TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                title TEXT,
                url TEXT,
                git_commit TEXT NOT NULL,
                indexed_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                path TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,

                title TEXT,
                heading_path TEXT NOT NULL,
                content TEXT NOT NULL,

                FOREIGN KEY(path)
                    REFERENCES documents(path)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_path
                ON chunks(path);

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
            USING fts5(
                title,
                heading_path,
                content,
                content='chunks',
                content_rowid='id'
            );

            CREATE TRIGGER IF NOT EXISTS chunks_ai
            AFTER INSERT ON chunks
            BEGIN
                INSERT INTO chunks_fts(
                    rowid,
                    title,
                    heading_path,
                    content
                )
                VALUES (
                    new.id,
                    new.title,
                    new.heading_path,
                    new.content
                );
            END;

            CREATE TRIGGER IF NOT EXISTS chunks_ad
            AFTER DELETE ON chunks
            BEGIN
                INSERT INTO chunks_fts(
                    chunks_fts,
                    rowid,
                    title,
                    heading_path,
                    content
                )
                VALUES (
                    'delete',
                    old.id,
                    old.title,
                    old.heading_path,
                    old.content
                );
            END;

            CREATE TRIGGER IF NOT EXISTS chunks_au
            AFTER UPDATE ON chunks
            BEGIN
                INSERT INTO chunks_fts(
                    chunks_fts,
                    rowid,
                    title,
                    heading_path,
                    content
                )
                VALUES (
                    'delete',
                    old.id,
                    old.title,
                    old.heading_path,
                    old.content
                );

                INSERT INTO chunks_fts(
                    rowid,
                    title,
                    heading_path,
                    content
                )
                VALUES (
                    new.id,
                    new.title,
                    new.heading_path,
                    new.content
                );
            END;
            """
        )

        self.connection.commit()

    def get_indexed_commit(
        self,
        repository: str,
    ) -> Optional[str]:
        row = self.connection.execute(
            """
            SELECT commit_hash
            FROM ingestion_state
            WHERE repository = ?
            """,
            (
                repository,
            ),
        ).fetchone()

        if row is None:
            return None

        return row["commit_hash"]

    def set_indexed_commit(
        self,
        repository: str,
        commit_hash: str,
    ):
        self.connection.execute(
            """
            INSERT INTO ingestion_state(
                repository,
                commit_hash
            )
            VALUES (?, ?)

            ON CONFLICT(repository)
            DO UPDATE SET
                commit_hash = excluded.commit_hash,
                indexed_at = CURRENT_TIMESTAMP
            """,
            (
                repository,
                commit_hash,
            ),
        )

        self.connection.commit()

    def get_document(
        self,
        path: str,
    ):
        return self.connection.execute(
            """
            SELECT *
            FROM documents
            WHERE path = ?
            """,
            (
                path,
            ),
        ).fetchone()

    def delete_document(
        self,
        path: str,
    ):
        self.connection.execute(
            """
            DELETE FROM chunks
            WHERE path = ?
            """,
            (
                path,
            ),
        )

        self.connection.execute(
            """
            DELETE FROM documents
            WHERE path = ?
            """,
            (
                path,
            ),
        )

        self.connection.commit()

    def insert_document(
        self,
        path: str,
        content_hash: str,
        title: str,
        url: str,
        git_commit: str,
        chunks: list[dict],
    ):
        self.delete_document(path)

        self.connection.execute(
            """
            INSERT INTO documents(
                path,
                content_hash,
                title,
                url,
                git_commit
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                path,
                content_hash,
                title,
                url,
                git_commit,
            ),
        )

        for index, chunk in enumerate(chunks):
            self.connection.execute(
                """
                INSERT INTO chunks(
                    path,
                    chunk_index,
                    title,
                    heading_path,
                    content
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    path,
                    index,
                    title,
                    chunk["heading_path"],
                    chunk["content"],
                ),
            )

        self.connection.commit()

    def search(
        self,
        query: str,
        limit: int = 10,
    ):
        stop_words = {
            "a",
            "about",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "can",
            "do",
            "for",
            "from",
            "how",
            "i",
            "in",
            "is",
            "of",
            "on",
            "or",
            "our",
            "that",
            "the",
            "this",
            "to",
            "when",
            "where",
            "which",
            "who",
            "why",
            "with",
            "we",
            "what",
            "you",
            "your",
        }

        words = query.lower().split()

        safe_words = []

        for word in words:
            cleaned = "".join(
                character
                for character in word
                if character.isalnum()
                or character in "_-"
            )

            if cleaned:
                safe_words.append(
                    cleaned
                )

        if not safe_words:
            return []

        phrase = " ".join(
            safe_words
        )

        meaningful_words = [
            word
            for word in safe_words
            if word not in stop_words
        ]

        query_parts = []

        # Exact phrase match.
        if len(safe_words) > 1:
            query_parts.append(
                f'"{phrase}"'
            )

        # Individual meaningful terms.
        for word in meaningful_words:
            query_parts.append(
                f'"{word}"'
            )

        if not query_parts:
            return []

        safe_query = " OR ".join(
            query_parts
        )

        return self.connection.execute(
            """
            SELECT
                chunks.id,
                chunks.path,
                chunks.title,
                chunks.heading_path,
                chunks.content,
                documents.url,

                bm25(
                    chunks_fts,
                    10.0,
                    5.0,
                    1.0
                ) AS score

            FROM chunks_fts

            JOIN chunks
                ON chunks.id = chunks_fts.rowid

            JOIN documents
                ON documents.path = chunks.path

            WHERE chunks_fts MATCH ?

            ORDER BY score

            LIMIT ?
            """,
            (
                safe_query,
                limit,
            ),
        ).fetchall()
