import os
from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict, Callable
from enum import Enum


class PropertyType(Enum):
    """
    Enum representing the origin or location of a property in an HTTP request.
    """
    BODY = 'body'
    PARAM = 'param'
    HEADER = 'header'
    UNKNOWN = ''

@dataclass
class Property:
    """
    Data class representing a single property/parameter from an OpenAPI schema.

    Attributes:
        original_key: The original name of the property as defined in the OpenAPI spec.
        transformed_key: A sanitized, Python-safe variable name for the property, potentially prefixed by its PropertyType.
        type: The JSON schema type of the property (e.g., 'string', 'integer').
        format: The JSON schema format string (e.g., 'date-time', 'email').
        enum: A list of allowed values if the property is an enum.
        items: The schema dict for items if this property is an array.
        default: The default value of the property, if any.
    """
    original_key: str
    transformed_key: str
    type: Optional[str] = None
    format: Optional[str] = None
    enum: Optional[List[Any]] = None
    items: Optional[dict] = None
    default: Optional[Any] = None





@dataclass
class MySchema:
    """
    Data class representing a simplified JSON schema for a request component or response body.

    Attributes:
        properties: A dictionary mapping original property names to Property objects.
        required: A list of property names that are required by the schema.
        containing_type: The higher-level type (e.g., 'array' if this schema describes array items).
        type: The base JSON schema type (e.g., 'object', 'array').
    """
    # Use default_factory for mutable types (dict, list)
    properties: Dict[str, Property] = field(default_factory=dict)
    required: List[Any] = field(default_factory=list)

    # Simple immutable types (str, int) can stay as they are
    containing_type: Optional[str] = ''
    type: Optional[str] = ''


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


@dataclass
class InputServer:
    openapi_url: str