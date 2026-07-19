from markdown_it import MarkdownIt


def parse_markdown(markdown: str) -> dict:
    """
    Parse a Markdown document into semantic chunks.

    Returns:
        {
            "title": str,
            "chunks": [
                {
                    "heading_path": str,
                    "content": str,
                }
            ],
        }
    """

    md = MarkdownIt()

    tokens = md.parse(markdown)

    title = None
    chunks = []

    heading_stack = []
    current_content = []

    def flush_content():
        nonlocal current_content

        content = "\n".join(
            current_content
        ).strip()

        if content:
            chunks.append(
                {
                    "heading_path": " > ".join(
                        heading_stack
                    ),
                    "content": content,
                }
            )

        current_content = []

    i = 0

    while i < len(tokens):
        token = tokens[i]

        if token.type == "heading_open":
            flush_content()

            level = int(
                token.tag[1:]
            )

            heading_text = ""

            if (
                i + 1 < len(tokens)
                and tokens[i + 1].type == "inline"
            ):
                heading_text = (
                    tokens[i + 1]
                    .content
                    .strip()
                )

            while len(heading_stack) >= level:
                heading_stack.pop()

            heading_stack.append(
                heading_text
            )

            if (
                title is None
                and level == 1
            ):
                title = heading_text

            i += 3

            continue

        if token.type == "inline":
            if token.content.strip():
                current_content.append(
                    token.content.strip()
                )

        elif token.type == "fence":
            language = token.info.strip()

            if language:
                current_content.append(
                    f"```{language}\n"
                    f"{token.content}"
                    f"```"
                )
            else:
                current_content.append(
                    f"```\n"
                    f"{token.content}"
                    f"```"
                )

        elif token.type == "code_block":
            current_content.append(
                f"```\n"
                f"{token.content}"
                f"```"
            )

        i += 1

    flush_content()

    if title is None:
        title = "Untitled"

    return {
        "title": title,
        "chunks": chunks,
    }
