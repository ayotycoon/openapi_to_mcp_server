import os
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Literal, Optional, Callable

import requests
from src.utils.file_helper import write_json, read_json
from src.utils.mylogger import mylogger

@dataclass
class SimpleTool:
    """
    A simple data class representing an MCP tool.
    
    Attributes:
        fn (Optional[Callable]): The callable function that implements the tool logic.
        name (Optional[str]): The unique name of the tool.
        description (Optional[str]): A description of what the tool does.
    """
    fn: Optional[Callable]
    name: Optional[str]
    description: Optional[str]

def generate_fn(
        http_method: str,
        url: str,
        config: Dict[str, Any],
        method_name:str,
        headers_structure: Dict[str, Any],
        params_structure: Dict[str, Any],
        body_structure: Dict[str, Any],
        response_structure: Dict[str, Any]):
    """
    Dynamically generates a Python function that makes an HTTP request based on the provided schema structures.
    
    This function constructs the code for a tool function (using templates), executes it in a local namespace,
    and returns the callable function. It handles parameter parsing, request body construction, and response
    deserialization.
    
    Args:
        http_method: The HTTP method (GET, POST, etc.).
        url: The target URL for the request.
        config: Configuration dictionary (e.g., content-type acceptance).
        method_name: The name of the function to be generated.
        headers_structure: Schema for request headers.
        params_structure: Schema for query/path parameters.
        body_structure: Schema for the request body.
        response_structure: Schema for the expected response.
        
    Returns:
        Callable: The dynamically generated function.
    """

    namespace = {"requests":requests, "Literal":Literal, "dataclass":dataclass, "Any":Any, "List":List, "mylogger":mylogger}

    params_args_str = gen_args(params_structure)
    headers_args_str = gen_args(headers_structure)
    request_body_args_str = gen_args(body_structure)

    # Merge properties for debug params
    debug_params_props = {}
    debug_params_props.update(headers_structure.get("properties", {}))
    debug_params_props.update(params_structure.get("properties", {}))
    debug_params_props.update(body_structure.get("properties", {}))
    
    debug_params = {"properties": debug_params_props, "required": []}

    debug_args = gen_dict(debug_params)

    request_body_dict_str = gen_dict(body_structure) or "None"
    headers_dict_str = gen_dict(headers_structure) or "None"

    response_body_class_str = gen_class("ResponseBody", response_structure)

    prepend = response_body_class_str or ""

    fn_args = []
    if params_args_str:
        fn_args.append(params_args_str)
    if request_body_args_str:
        fn_args.append(request_body_args_str)
    if headers_args_str:
        fn_args.append(headers_args_str)

    replaced_template = (read_json("src/templates/api_requests_generator.md", False)
                         .replace("#method_name",method_name)
                         .replace("#prepend", prepend)
                         .replace("#http_method", http_method.upper())
                         .replace("#url", url)
                         .replace("#args", ",".join(fn_args))
                         .replace("#json", request_body_dict_str)
                         .replace("#headers", headers_dict_str)
                         .replace("#debug_args", debug_args+".__str__()")
                         )

    if response_body_class_str:
        res_type = "ResponseBody"
        if response_structure.get("containing_type") == "array":
            res_type = "List[ResponseBody]"
        replaced_template = replaced_template.replace("#response_body", res_type)
    else:
        replaced_template = replaced_template.replace("#response_body", "Any")

    temp_headers = "from src.utils.mylogger import mylogger\nimport requests\nfrom typing import Literal, Any, Dict, Callable, List, Optional\nfrom dataclasses import dataclass\n"
    temp_footers = f"\n\nif __name__ == \"__main__\":\n    {method_name}()"
    debug_str = temp_headers+replaced_template+temp_footers
    # write in temp dir for debugging
    write_json(os.path.join("logs",f"{method_name}.py"), debug_str, False)
    exec(replaced_template, namespace)
    return namespace[method_name]

schema_type_dict = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "object": "dict",
    "array": "list"
}

def common_parser(
        arr:List[str],
        loop_func: Callable[[List[str], Dict[str, Any], str], None],
        end_func: Callable[[List[str]], str], 
        schema: Dict[str, Any]
):
    if not schema:
        return None
    props = schema.get("properties", {})
    required = schema.get("required", [])
    properties_items = props.values()
    if len(properties_items) == 0:
        return None

    for definition in properties_items:
        typ = definition.get("type")
        # Map JSON types → Python types
        python_type = schema_type_dict.get(typ, "Any")
        # Handle enums
        if definition.get("enum"):
            enum_vals = ", ".join([f'"{v}"' for v in definition.get("enum")])
            python_type = f"Literal[{enum_vals}]"

        # Optional fields
        if definition.get("original_key") not in required:
            python_type = f"{python_type}"

        loop_func(arr, definition, python_type)
    return end_func(arr)

def gen_args(schema: Dict[str, Any]):
    return common_parser(
        [],
        lambda lines, definition, python_type: lines.append(f" {definition.get('transformed_key')}: {python_type}=None"),
        lambda lines: ",".join(lines), schema)

def gen_class(class_name: str, schema: Dict[str, Any]):
    return common_parser(
        [f"@dataclass", f"class {class_name}:"],
        lambda lines, definition, python_type: lines.append(f"    {definition.get('original_key')}: {python_type}"),
        lambda lines: "\n".join(lines), schema)

def gen_dict(schema: Dict[str, Any]):
    return common_parser(
        ["{"],
        lambda lines, definition, python_type: lines.append(f"\"{definition.get('original_key')}\": {definition.get('transformed_key')},"),
        lambda lines: "".join(lines)+"}", schema)


class ToolsGenerator:
    """
    Generates MCP tools from an OpenAPI specification.
    
    This class handles fetching the OpenAPI spec, parsing it, processing schemas, 
    and generating corresponding Python functions (`SimpleTool` objects) that can be exposed by the MCP server.
    """
    spec: Dict[str, Any]
    cache_path: str
    components: Dict[str, Any]
    base_url: str

    def __init__(self, cache_path: str = None):
        """
        Initialize the ToolsGenerator.
        
        Args:
            cache_path: Path to the local file where the OpenAPI spec is cached. 
                        If provided, the spec is read from this file; otherwise it may be fetched.
        """
        self.cache_path = cache_path
        self.spec = read_json(cache_path)
        self.components = self.spec.get("components", {})
        servers = self.spec.get("servers", [])
        self.base_url = servers[0]["url"] if servers else "http://localhost"
        self.fetch_api_docs()
        pass

    def schema_processor(self, obj: Dict[str, Any] | None) -> Dict[str, Any]:
        """
        Recursively processes a JSON schema object to resolve references and simplify the structure.
        
        Args:
            obj: The raw JSON schema dictionary.
            
        Returns:
            Dict[str, Any]: A processed dictionary with resolved types and properties suitable for generation.
        """
        empty_schema = {"properties": {}, "required": []}
        if obj is None:
            return empty_schema
        
        type_ = obj.get("type")
        if type_ == "array":
            items = obj.get("items")
            x = self.schema_processor(items)
            x["containing_type"] = "array"
            return x

        ref = obj.get("$ref")
        if ref is None:
            # Inline schema or simple type
            properties = obj.get("properties")
            if not properties:
                return {"type": type_, "properties": {}, "required": []}

            model = {"type": type_, "required": obj.get("required", []), "properties": {}}
            for k, v in properties.items():
                prop = self.create_property_component(k, v)
                model["properties"][k] = prop
            return model

        paths = ref.split('/')[2:]
        if len(paths) < 2:
            return empty_schema

        if paths[0] == "schemas":
            schemas = self.components.get("schemas", {})
            schema_name = paths[1]
            if schema_name not in schemas:
                return empty_schema
            
            d = schemas[schema_name]
            
            model = {"type": d.get("type"), "required": d.get("required", []), "properties": {}}
            properties = d.get("properties", {})
            for k, v in properties.items():
                prop = self.create_property_component(k, v)
                model["properties"][k] = prop
            return model
            
        return empty_schema
    
    def create_property_component(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        prop = {}
        prop["type"] = value.get("type")
        prop["format"] = value.get("format")
        prop["enum"] = value.get("enum")
        prop["items"] = value.get("items")
        prop["default"] = value.get("default")
        prop["original_key"] = key
        prop["transformed_key"] = self.sanitize_variable_name(key)
        return prop

    def sanitize_variable_name(self, s: str):
        # Replace dashes with underscores
        s = s.replace('-', '_').replace('/', '_')
        # Convert camelCase to snake_case
        s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
        # Lowercase
        return s.lower()

    def openapi_to_tools(self):
        """
        Main entry point for converting the parsed OpenAPI spec into a list of SimpleTool objects.
        
        It iterates over paths and methods in the spec, extracts parameters, request bodies, and responses,
        and calls `generate_fn` to create the executable tool function for each operation.
        
        Returns:
            List[SimpleTool]: A list of generated tools ready to be registered with the MCP server.
        """
        tools: List[SimpleTool] = []
        paths = self.spec.get("paths", {})
        mylogger.info("[MCP] parsing tools")
        for path, methods in paths.items():
            needs_auth = "/auth" not in path
            for http_method, op in methods.items():

                # ----------------------------
                # Build JSON schema parameters
                # ----------------------------
                params_structure = {"properties": {}, "required": []}
                body_structure = {"properties": {}, "required": []}
                response_structure = {"properties": {}, "required": []}
                headers_structure = {"properties": {}, "required": []}
                config = {}

                # Path + query + header params
                parameters = op.get("parameters", [])
                for param in parameters:
                    param_name = param["name"]
                    transform_name = self.sanitize_variable_name(param_name)
                    path = path.replace(f"{{{param_name}}}", f"{{{transform_name}}}") 

                    schema_dict = param.get("schema", {}) 
                    
                    # Create property component
                    prop = self.create_property_component(param_name, schema_dict)
                    params_structure["properties"][param_name] = prop

                description = f"{http_method.upper()} {path}"
                operation_id = self.sanitize_variable_name(op.get("operationId") or f"{http_method}_{path}")

                # Request body JSON
                request_body = op.get("requestBody")
                if request_body:
                    content = request_body.get("content", {})
                    if "application/json" in content:
                        config["accepts-content-type"] =  "application/json"
                        body_schema = content["application/json"].get("schema", {})
                        body_structure = self.schema_processor(body_schema)

                responses = op.get("responses", {})
                if responses:
                    for code, response_detail in responses.items():
                        if code != "200":
                            continue
                        
                        content = response_detail.get("content")
                        if not content:
                            continue
                            
                        if "*/*" in content:
                            s = content["*/*"].get("schema", {})
                            response_structure = self.schema_processor(s)
                        elif "application/json" in content:
                            s = content["application/json"].get("schema", {})
                            response_structure = self.schema_processor(s)

                headers_structure["properties"]["tid"] = params_structure["properties"].get("tid") 
                
                if "tid" in params_structure["properties"]:
                     params_structure["properties"].pop("tid")

                if needs_auth:
                    headers_structure["properties"]["Authorization"] = {
                        "type": "string",
                        "original_key": "Authorization",
                        "transformed_key": "authorization"
                    }
                
                mylogger.info(f"[MCP] Creating tool {operation_id} - {description}")
                tools.append(
                    SimpleTool(
                    fn= generate_fn(
                        http_method=http_method,
                        url=self.base_url+path,
                        method_name=operation_id,
                        config=config,
                        headers_structure=headers_structure,
                        params_structure= params_structure,
                        body_structure= body_structure,
                        response_structure= response_structure,
                    ),
                    name = operation_id,
                    description = description,
            )
                )

        return tools

    def fetch_api_docs(self):

        if not self.cache_path:
            mylogger.info(f"[MCP] cache_path not found")
            return
        res = None
        try:
            response = requests.get(f"{self.base_url}/v3/api-docs")
            response.raise_for_status()  # Raise an exception for bad status codes
            res = response.text
        except Exception as e:
            mylogger.info(f"[MCP] Error fetching API docs: {e}")

        if not res:
            return
        write_json(self.cache_path, res, False)

if __name__ == "__main__":
    tools_ = ToolsGenerator("src/modules/src/modules/mcp/tools_generator/micro_services/olympus/openapi.json").openapi_to_tools()
    write_json("src/modules/test.json", [{"name": x.name, "description":x.description} for x in tools_])

