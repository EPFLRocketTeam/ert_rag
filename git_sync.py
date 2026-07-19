import subprocess
from pathlib import Path


def run_git(repo_path: str, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo_path, *args],
        check=True,
        capture_output=True,
        text=True,
    )

    return result.stdout.strip()


def clone_or_pull(repo_url: str, repo_path: str):
    path = Path(repo_path)

    if not (path / ".git").exists():
        path.parent.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            [
                "git",
                "clone",
                repo_url,
                repo_path,
            ],
            check=True,
        )

        return

    # Fetch first.
    run_git(repo_path, "fetch", "--all")

    # Determine current branch.
    branch = run_git(
        repo_path,
        "rev-parse",
        "--abbrev-ref",
        "HEAD",
    )

    # Pull fast-forward only.
    subprocess.run(
        [
            "git",
            "-C",
            repo_path,
            "pull",
            "--ff-only",
            "origin",
            branch,
        ],
        check=True,
    )


def get_current_commit(repo_path: str) -> str:
    return run_git(
        repo_path,
        "rev-parse",
        "HEAD",
    )


def get_changed_files(
    repo_path: str,
    old_commit: str | None,
    new_commit: str,
):
    if old_commit is None:
        # First ingestion: all Markdown files.
        output = run_git(
            repo_path,
            "ls-files",
            "*.md",
            "*.markdown",
        )

        return [
            ("A", path)
            for path in output.splitlines()
            if path.strip()
        ]

    output = run_git(
        repo_path,
        "diff",
        "--name-status",
        old_commit,
        new_commit,
        "--",
        "*.md",
        "*.markdown",
    )

    changed_files = []

    for line in output.splitlines():
        if not line.strip():
            continue

        parts = line.split("\t")

        status = parts[0]

        # Normal:
        #
        # M       file.md
        # A       file.md
        # D       file.md
        #
        if status in {"A", "M", "D"}:
            changed_files.append(
                (
                    status,
                    parts[1],
                )
            )

        # Rename:
        #
        # R100 old.md new.md
        #
        elif status.startswith("R"):
            changed_files.append(
                ("D", parts[1])
            )

            changed_files.append(
                ("A", parts[2])
            )

    return changed_files
