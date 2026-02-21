
import json
import os
from typing import Dict, Any
from typing import List
from urllib.parse import urlparse

import requests

from src.main.utils.dto import MySchema, PropertyType, SimpleTool, InputServer
from src.main.utils.file_helper import read_file
from src.main.utils.generate_fn import generate_fn
from src.main.utils.misc import create_property_component, sanitize_variable_name
from src.main.utils.misc import name_from_url
from src.main.utils.mylogger import mylogger


def schema_processor( components: dict[Any, Any], obj: Dict[str, Any] | None) -> MySchema | None:
    """
    Recursively processes a JSON schema object to resolve references and simplify the structure.

    Args:
        obj: The raw JSON schema dictionary.

    Returns:
        MySchema | None: A processed dictionary with resolved types and properties suitable for generation.
    """

    if obj is None:
        return None

    type_ = obj.get("type")
    if type_ == "array":
        items = obj.get("items")
        x = schema_processor(components, items)
        if not x:
            return None
        x.containing_type = "array"
        return x

    ref = obj.get("$ref")
    if ref is None:
        # Inline schema or simple type
        properties = obj.get("properties")
        if not properties:
            return None

        return MySchema(
            properties={
                k: create_property_component(k, v, PropertyType.UNKNOWN) for k, v in properties.items()},
            required=obj.get("required", []),
            type=type_)


    paths = ref.split('/')[2:]
    if len(paths) < 2:
        return None

    if paths[0] == "schemas":
        schemas = components.get("schemas", {})
        schema_name = paths[1]
        if schema_name not in schemas:
            mylogger.error(f"Schema not found in components for {schema_name}")
            return None

        nested_json_schema = schemas[schema_name]
        return MySchema(
            properties={
                k: create_property_component(k, v, PropertyType.BODY) for k, v in nested_json_schema.get("properties", {}).items()},
            required=nested_json_schema.get("required", []),
            type=nested_json_schema.get("type"))

    return None


def openapi_each_host_processor(openapi_file_path: str, host: str, url_match_for_non_auth: str|None):
    """
    Main entry point for converting the parsed OpenAPI spec into a list of SimpleTool objects.

    It iterates over paths and methods in the spec, extracts parameters, request bodies, and responses,
    and calls `generate_fn` to create the executable tool function for each operation.

    Args:
        openapi_file_path: Path to the local file where the OpenAPI spec is cached.
                    If provided, the spec is read from this file; otherwise it may be fetched.
        host: The hostname of the server.

    Returns:
        List[SimpleTool]: A list of generated tools ready to be registered with the MCP server.
    """
    spec = read_file(openapi_file_path, True)
    components = spec.get("components", {})
    servers = spec.get("servers", [])
    is_global_auth = "bearer" == components.get("securitySchemes", {}).get("bearerAuth", {}).get("scheme", "")
    if len(servers) > 1:
        mylogger.info(f"Multiple servers of len {len(servers)} found - {', '.join(x['url'] for x in servers)} | choosing the first")

    if servers[0]["url"].startswith("http"):
        base_url = servers[0]["url"]
    else:
        base_url = host + servers[0]["url"]

    tools: List[SimpleTool] = []
    paths = spec.get("paths", {})
    mylogger.info("Parsing tools")
    for path, methods in paths.items():
        for http_method, op in methods.items():


            # ----------------------------
            # Build JSON schema parameters
            # ----------------------------
            params_structure = MySchema(properties={}, required=[])
            body_structure = MySchema(properties={}, required=[])
            response_structures: List[MySchema] = []
            headers_structure = MySchema(properties={}, required=[])
            config = {}

            # Path + query + header params
            parameters = op.get("parameters", [])
            for param in parameters:
                param_or_header_properties = params_structure.properties
                is_header = False
                if param["in"] == "header":
                    param_or_header_properties = headers_structure.properties
                    is_header = True
                original_param_name = param["name"]
                schema_dict = param.get("schema", {})

                # Create property component
                prop = create_property_component(original_param_name, schema_dict, PropertyType.HEADER if is_header else PropertyType.PARAM)

                # Prepend param name to prevent variable conflicts with body
                prepended_param_name = prop.transformed_key
                path = path.replace(f"{{{original_param_name}}}", f"{{{prepended_param_name}}}")
                param_or_header_properties[original_param_name] = prop

            description = f"{http_method.upper()} {path}"
            operation_id = sanitize_variable_name(op.get("operationId") or f"{http_method}_{path}")

            # Request body JSON
            request_body = op.get("requestBody")
            if request_body:
                content = request_body.get("content", {})
                if "application/json" in content:
                    config["accepts-content-type"] = "application/json"
                    body_schema = content["application/json"].get("schema", {})
                    _ = schema_processor(components,body_schema)
                    if  _:
                        body_structure = _

            responses = op.get("responses", {})
            if responses:
                for code, response_detail in responses.items():
                    content = response_detail.get("content")
                    if not content:
                        continue

                    for response_sample in content.values():
                        s = response_sample.get("schema", {})
                        response_structure = schema_processor(components, s)
                        if response_structure:
                            response_structures.append(response_structure)

            if is_global_auth and (True if url_match_for_non_auth is  None else url_match_for_non_auth not in path):
                headers_structure.properties["Authorization"] = create_property_component('authorization', {
                    "type": "string",
                    "original_key": "Authorization",
                }, PropertyType.HEADER)

            fn = generate_fn(
                http_method=http_method,
                url=base_url + path,
                method_name=operation_id,
                config=config,
                headers_structure=headers_structure,
                params_structure=params_structure,
                body_structure=body_structure,
                response_structures=response_structures,
            )

            mylogger.info(f"Tool created | {operation_id} - {description}")
            tools.append(
                SimpleTool(
                    fn=fn,
                    name=operation_id,
                    description=description,
                )
            )

    return tools

def initializer(mcp, servers: List[InputServer], url_match_for_non_auth: str|None):
    """
    Initializes MCP tools by fetching OpenAPI specifications and registering them as tools.

    Iterates through a list of service names, retrieves their OpenAPI specs (either from a URL
    configured in environment variables or a local cache), creates tool definitions,
    and registers them with the MCP server key.

    Args:
        mcp: The FastMCP server instance.
        servers: A list of server URLs to fetch OpenAPI specs from.
    """

    for server in servers:
        openapi_url = server.openapi_url
        host  = urlparse(openapi_url).hostname
        name  = name_from_url(host)

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

        mylogger.info(f"Generating tools")
        # Generate tools
        tools = openapi_each_host_processor(output_file, host, url_match_for_non_auth)

        # Register tools with mcp
        for tool in tools:
            if tool.fn:
                mcp.tool(name=tool.name, description=tool.description)(tool.fn)
            else:
                mylogger.warning(f"Tool {tool.name} has no function, skipping registration.")

        mylogger.info(f"Registered {len(tools)} tools from {name} OpenAPI spec")
