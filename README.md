# Odin AI

Odin AI is a comprehensive backend system designed to bridge AI agents (like Claude or Odin) with core business services (`olympus`, `hades`) through the Model Context Protocol (MCP) and standard APIs.

## Project Overview

The system consists of two main server components running within a unified environment:

-   **Iris (MCP Server)**: Exposes backend capabilities as "tools" for AI agents. It dynamically generates these tools from OpenAPI specifications.
-   **Janus (API Server)**: Provides standard RESTful endpoints for external integrations and webhooks.

## Getting Started

### Prerequisites

-   [uv](https://github.com/astral-sh/uv) (Python package manager) installed on your system.

### Installation

1.  **Sync dependencies and set up the virtual environment:**
    ```bash
    uv sync
    source .venv/bin/activate
    ```

## Usage

### Running the Application

To start the unified server (Janus + Iris) on port **8000**:

```bash
uv run server.py
```

You can also specify a custom port via environment variable:

```bash
PORT=8080 uv run server.py
```

This starts both services:
-   **Janus API**: `http://localhost:8000/` (Health check available at root)
-   **Iris MCP Server**: `http://localhost:8000/mcp/sse` (SSE transport)

### Inspecting MCP Server

To interactively debug the MCP server using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
npx @modelcontextprotocol/inspector http://localhost:8000/mcp/sse
```

## Modules

The project is organized into modular components:

-   **[Iris (MCP Server)](iris/README.md)**: Connects backend services (`olympus`, `hades`) to AI agents. It fetches OpenAPI docs and converts them into executable MCP tools.
-   **[Janus (API Server)](janus/README.md)**: Provides standard HTTP API endpoints, useful for webhooks or direct integrations.
-   **[Common](common/README.md)**: Contains shared utilities, logging configuration, and assets used across modules.

![System Architecture](common/assets/img.png)
*Connecting with Claude desktop for full LLM testing:*
![Claude Desktop Integration](common/assets/img_1.png)

## Dependencies

Key dependencies managed by `uv` (see `pyproject.toml`):

*   [mcp](https://pypi.org/project/mcp/): For implementing the Model Context Protocol.
*   [starlette](https://www.starlette.io/): High-performance ASGI framework or the main server.
*   [flask](https://flask.palletsprojects.com/): WSGI framework for Janus API.
*   [requests](https://pypi.org/project/requests/): For making HTTP requests to downstream services.
