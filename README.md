# Iris

Iris is a Model Context Protocol (MCP) server that dynamically converts OpenAPI specifications into executable MCP tools. This allows AI agents (like Claude or Gemini) to interact with any REST API that provides an OpenAPI definition.

## Features

-   **OpenAPI to MCP**: Automatically fetches OpenAPI documentation from specified URLs and converts endpoints into MCP tools.
-   **Multiple Services**: Support for connecting multiple OpenAPI services simultaneously.
-   **Flexible Transport**: Supports HTTP (Streamable), SSE, and Stdio transports.

## Getting Started

### Prerequisites

-   [uv](https://github.com/astral-sh/uv) (Python package manager) installed on your system.

### Installation

1.  **Sync dependencies:**
    ```bash
    uv sync
    ```

## Usage

### Running the Server

The server requires the `SERVERS_COUNT` and corresponding `SERVERS{i}_OPENAPI_URL` environment variables to be set to point to one or more OpenAPI JSON definitions.

#### Quick Start (Dev Mode)

To run with a sample Petstore API (defined in `pyproject.toml`):

```bash
uv run dev
```

#### Manual Execution

You can specify your own OpenAPI schemas:

```bash
SERVERS_COUNT=1 SERVERS0_OPENAPI_URL=https://petstore3.swagger.io/api/v3/openapi.json uv run server.py
```

#### Configuration

You can configure the server using environment variables:

-   `SERVERS_COUNT`: (Required) The number of OpenAPI servers you want to connect to (e.g., `2`).
-   `SERVERS{i}_OPENAPI_URL`: (Required) The URL to the OpenAPI JSON definition for index `i`, starting from `0` (e.g., `SERVERS0_OPENAPI_URL=https://api.example.com/openapi.json`).
-   `URL_MATCH_FOR_NON_AUTH`: (Optional) A path segment (e.g., `/auth`) that should bypass global authentication headers if applicable.
-   `PORT`: Port to run the server on (default: `8000`).
-   `mcp.transport`: Transport mode. Options: `streamable-http` (default), `sse`, `stdio`.

### Inspecting Tools

You can use the MCP Inspector to test the tools.

Using the convenience script:
```bash
uv run inspector-streamable-http
```

Or manually:
```bash
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

## Project Structure

-   `server.py`: Entry point for the MCP server.
-   `src/`: Source code including OpenAPI processing logic.
-   `pyproject.toml`: Project dependencies and scripts.
