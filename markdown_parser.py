from markdown_it import MarkdownIt


def parse_markdown(markdown: str) -> tuple[str, list[dict]]:
    md = MarkdownIt()
    tokens = md.parse(markdown)

    title = None
    chunks = []

    heading_stack = []
    current_content = []

    def flush_content():
        nonlocal current_content

        content = "\n".join(current_content).strip()

        if content:
            chunks.append(
                {
                    "heading_path": " > ".join(heading_stack),
                    "content": content,
                }
            )

        current_content = []

    i = 0

    while i < len(tokens):
        token = tokens[i]

        if token.type == "heading_open":
            flush_content()

            level = int(token.tag[1])

            # The heading text is in the next token.
            heading_token = tokens[i + 1]

            heading_text = heading_token.content.strip()

            # Remove headings at the same or deeper level.
            while len(heading_stack) >= level:
                heading_stack.pop()

            heading_stack.append(heading_text)

            if title is None and level == 1:
                title = heading_text

            i += 3
            continue

        if token.type == "inline":
            current_content.append(token.content)

        elif token.type == "fence":
            language = token.info.strip()

            if language:
                current_content.append(
                    f"```{language}\n{token.content}```"
                )
            else:
                current_content.append(
                    f"```\n{token.content}```"
                )

        elif token.type == "code_block":
            current_content.append(
                f"```\n{token.content}```"
            )

        i += 1

    flush_content()

    if title is None:
        title = "Untitled"

    return title, chunks
