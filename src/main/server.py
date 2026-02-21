import os

from src.main.utils.misc import get_servers
from src.main.utils.mylogger import mylogger
from src.main.utils.openapi_to_tools import initializer

mylogger.info("Starting server")
from mcp.server.fastmcp import FastMCP

PORT = os.environ.get("PORT", 8000)
TRANSPORT = os.environ.get('mcp.transport', 'streamable-http')
URL_MATCH_FOR_NON_AUTH: str|None = os.environ.get("URL_MATCH_FOR_NON_AUTH")


servers = get_servers()
if  len(servers) == 0:
    raise  "SERVERS environment variable not found"




# Create an MCP server
mcp = FastMCP("iris", stateless_http=True)
initializer(mcp, servers=servers, url_match_for_non_auth=URL_MATCH_FOR_NON_AUTH)

def start_server():
    import uvicorn
    port = int(PORT)
    if TRANSPORT  == 'streamable-http':
        uvicorn.run(mcp.streamable_http_app(), host='0.0.0.0', port=port)
    elif TRANSPORT  == 'sse':
        uvicorn.run(mcp.sse_app(), host='0.0.0.0', port=port)
    else:
        mcp.run(transport='stdio')


if __name__ == "__main__":
    start_server()