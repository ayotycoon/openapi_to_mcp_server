import os
import re
from typing import List

import requests
import json
from src.utils.ToolsGenerator import ToolsGenerator
from src.utils.mylogger import mylogger
from urllib.parse import urlparse


def name_from_url(url):
    # This regex [^a-zA-Z0-9] matches anything that is NOT a letter or number
    # and replaces it with an underscore
    sanitized = re.sub(r'[^a-zA-Z0-9]', '_', url)

    # Optional: Clean up double underscores and trailing underscores
    return re.sub(r'_+', '_', sanitized).strip('_')

proper_format = "name|openapi_url|host"

"""
servers list of str in format {proper_format}
"""
def init(mcp, servers: List[str]):
    """
    Initializes MCP tools by fetching OpenAPI specifications and registering them as tools.

    Iterates through a list of service names, retrieves their OpenAPI specs (either from a URL
    configured in environment variables or a local cache), creates tool definitions,
    and registers them with the MCP server key.

    Args:
        mcp: The FastMCP server instance.
        servers:
    """

    for server in servers:
        split = server.split("|")
        if len(split) >= 2 or len(split) == 0:
            mylogger.error("invalid server format")
            return
        if len(split) == 1:
            openapi_url = split[0]
            host  = urlparse(openapi_url).hostname
            name  = name_from_url(host)
            mylogger.warning(f"Each server should have 3 in the format {proper_format}, only url found. host  will be assumed to {host}")
        else:
            host = split[0]
            openapi_url = split[1]
            name = name_from_url(host)
        # Define path to save openapi.json
        output_dir = os.path.join("logs")
        output_file = os.path.join(output_dir, name + "_openapi.json")

        try:
            # 1. Fetch OpenAPI spec from the configured URL
            mylogger.info(f"Fetching OpenAPI spec from {openapi_url}")
            response = requests.get(openapi_url)
            response.raise_for_status()

            openapi_data = response.json()

            with open(output_file, 'w') as f:
                json.dump(openapi_data, f, indent=2)

            mylogger.info(f"OpenAPI spec saved to {output_file}")

        except requests.exceptions.RequestException as e:
            mylogger.error(f"Failed to fetch OpenAPI spec from {openapi_url}: {e}")
            if os.path.exists(output_file):
                 mylogger.warning(f"Using cached OpenAPI spec from {output_file}")
            else:
                 mylogger.error(f"No cached OpenAPI spec found at {output_file}. Skipping {name}.")
                 continue
        except Exception as e:
            mylogger.error(f"Error processing {name} OpenAPI: {e}")
            continue

        try:
            # Generate tools
            tools = ToolsGenerator(output_file).openapi_to_tools()

            # Register tools with mcp
            for tool in tools:
                if tool.fn:
                    mcp.tool(name=tool.name, description=tool.description)(tool.fn)
                else:
                    mylogger.warning(f"Tool {tool.name} has no function, skipping registration.")

            mylogger.info(f"Registered {len(tools)} tools from {name} OpenAPI spec")
        except Exception as e:
             mylogger.error(f"Error generating tools for {name}: {e}")

