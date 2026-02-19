import os
from typing import List
from src.utils.mylogger import mylogger

mylogger.info("[MCP] starting server")
from mcp.server.fastmcp import FastMCP
from src.utils.openapi_processor import init

PORT = os.environ.get("PORT", 8000)
TRANSPORT = os.environ.get('mcp.transport', 'streamable-http')
SERVERS: List[str] = os.environ.get("SERVERS", "").split(",")

# Create an MCP server
mcp = FastMCP("iris", stateless_http=True)
init(mcp, servers=SERVERS)
if __name__ == "__main__":
    import uvicorn
    port = int(PORT)
    if TRANSPORT  == 'streamable-http':
        uvicorn.run(mcp.streamable_http_app(), host='0.0.0.0', port=port)
    elif TRANSPORT  == 'sse':
        uvicorn.run(mcp.sse_app(), host='0.0.0.0', port=port)
    else:
        mcp.run(transport='stdio')
