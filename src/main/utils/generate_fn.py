import os
from dataclasses import dataclass
from typing import List, Dict, Any, Literal, Callable

import requests

from jinja2 import Template

from src.main.utils.dto import Property, MySchema
from src.main.utils.file_helper import write_to_file, read_file
from src.main.utils.mylogger import mylogger

api_requests_generator_template = read_file("src/main/templates/api_requests_generator.jinja2", False)


def common_parser(
        arr: List[str],
        loop_func: Callable[[List[str], Property, str], None],
        end_func: Callable[[List[str]], str],
        schema: MySchema
):
    """
    A higher-order function that iterates over the properties of a MySchema object
    and applies a provided function to each property to build a list of strings,
    which are then finalized by an ending function.

    Args:
        arr: The initial list of strings to build upon.
        loop_func: A callable that takes the string list, the current property,
                   and its mapped Python type as arguments and mutates the list.
        end_func: A callable that takes the final list of strings and returns
                  the finalized string representation.
        schema: The schema containing the properties to iterate over.

    Returns:
        Optional[str]: The finalized string or None if the schema or properties are empty.
    """
    if not schema:
        return None
    props: Dict[str, Property] = schema.properties
    required = schema.required
    properties_items = props.values()
    if len(properties_items) == 0:
        return None

    for definition in properties_items:
        if not definition:
            continue

        typ = definition.type
        # Map JSON types → Python types
        python_type = schema_type_dict.get(typ, "Any")
        # Handle enums
        if definition.enum:
            enum_vals = ", ".join([f'"{v}"' for v in definition.enum])
            python_type = f"Literal[{enum_vals}]"

        # Optional fields
        if definition.original_key not in required:
            python_type = f"{python_type}"

        loop_func(arr, definition, python_type)
    return end_func(arr)


def gen_args(schema: MySchema):
    """
    Generates a string of Python function arguments with type hints based on a schema.

    Args:
        schema: The schema describing the arguments.

    Returns:
        Optional[str]: A comma-separated string of function arguments, or None if empty.
    """
    return common_parser(
        [],
        lambda lines, definition, python_type: lines.append(f" {definition.transformed_key}: {python_type}=None"),
        lambda lines: ",".join(lines), schema)


def gen_class(class_name: str, schema: MySchema):
    """
    Generates a string representation of a Python dataclass definition based on a schema.

    Args:
        class_name: The name of the dataclass to generate.
        schema: The schema describing the properties of the class.

    Returns:
        Optional[str]: The string containing the mapped dataclass definition, or None if empty.
    """
    return common_parser(
        [f"@dataclass", f"class {class_name}:"],
        lambda lines, definition, python_type: lines.append(f"    {definition.original_key}: {python_type}"),
        lambda lines: "\n".join(lines), schema)


def gen_dict(schema: MySchema):
    """
    Generates a string representation of a Python dictionary based on a schema.
    Typically used for mapping original schema keys to sanitized variable names.

    Args:
        schema: The schema describing the dictionary's structure.

    Returns:
        Optional[str]: The string containing the dictionary definition, or None if empty.
    """
    return common_parser(
        ["{"],
        lambda lines, definition, python_type: lines.append(
            f"\"{definition.original_key}\": {definition.transformed_key},"),
        lambda lines: "".join(lines) + "}", schema)





def generate_fn(
        http_method: str,
        url: str,
        config: Dict[str, Any],
        method_name: str,
        headers_structure: MySchema,
        params_structure: MySchema,
        body_structure: MySchema,
        response_structures: List[MySchema]):
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
        response_structures: List of schemas for the expected responses.

    Returns:
        Callable: The dynamically generated function.
    """

    namespace = {"requests": requests, "Literal": Literal, "dataclass": dataclass, "Any": Any, "List": List,
                 "mylogger": mylogger}

    params_args_str = gen_args(params_structure)
    headers_args_str = gen_args(headers_structure)
    request_body_args_str = gen_args(body_structure)

    response_body_class_str = ""
    response_body_class_list = []
    for i in range(len(response_structures)):
        response_class_name = f"ResponseBody{i}"
        response_structure = response_structures[i]
        _ = gen_class(response_class_name, response_structure)
        if not _:
            continue
        response_body_class_str = response_body_class_str +"\n"+_
        if response_structure.containing_type == "array":
            response_body_class_list.append(f"List[{response_class_name}]")
        else:
            response_body_class_list.append(response_class_name)

    response_body_str = response_body_class_str or ""

    fn_args_string_list = []
    if params_args_str:
        fn_args_string_list.append(params_args_str)
    if request_body_args_str:
        fn_args_string_list.append(request_body_args_str)
    if headers_args_str:
        fn_args_string_list.append(headers_args_str)

    if len(response_body_class_list) != 0:
        res_type  = " |".join(response_body_class_list)
    else:
        res_type = "Any"

    template = Template(api_requests_generator_template)
    replaced_template = template.render(
        method_name=method_name,
        response_body_classes=response_body_str,
        http_method=http_method.upper(),
        url=url,
        args=",".join(fn_args_string_list),
        json=gen_dict(body_structure) or "None",
        headers=gen_dict(headers_structure) or "None",
        args_debug_dict=gen_dict(MySchema(properties={**headers_structure.properties,**params_structure.properties,**body_structure.properties}, required=[])),
        response_body_types=res_type + " | None"
    )

    # write in temp dir for debugging
    write_to_file(os.path.join("logs", f"{method_name}.py"), replaced_template, False)
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