from mcp.server import MCPServer

mcp = MCPServer("ERT RAG")

@mcp.tool()
def search_knowledge_base(query: str) -> str:
    """Search the EPFL Rocket Team knowledge base."""
    return f"Searching for: {query}"
