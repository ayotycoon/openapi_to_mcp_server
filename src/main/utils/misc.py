import os
import re
from typing import Optional, Any, Dict, List
from src.main.utils.dto import Property, PropertyType, InputServer


def sanitize_variable_name( s: str):
    """
    Sanitizes a string to be a valid, snake_case Python variable name.
    Useful for converting OpenAPI path segments or camelCase keys into argument names.

    Args:
        s: The original string.

    Returns:
        str: The sanitized snake_case string.
    """
    # Replace dashes with underscores
    s = s.replace('-', '_').replace('/', '_')
    # Convert camelCase to snake_case
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    # Lowercase
    return s.lower()


def create_property_component(key: str,
                              value: Dict[str, Any],
                              property_type: Optional[PropertyType] = None) -> Property:
    """
    Constructs a Property dto object from a raw OpenAPI schema property dictionary.
    Handles the sanitation of the key for safe Python variable usage.

    Args:
        key: The original property name from the schema.
        value: The dictionary containing the property's OpenAPI definitions.
        property_type: Optional classification (e.g., PARAM, HEADER, BODY) to prefix the variable name to avoid conflicts.

    Returns:
        Property: A constructed Property object.
    """
    transformed_key = sanitize_variable_name(key)

    if property_type is not None:
        transformed_key = f"{property_type.value}_{transformed_key}"

    prop = Property(
        original_key=key,
        transformed_key=transformed_key,
        type=value.get("type"),
        format=value.get("format"),
        enum=value.get("enum"),
        items=value.get("items"),
        default=value.get("default")
    )
    return prop

def name_from_url(url):
    """
    Extracts a clean, safe string from a URL (typically the hostname) by replacing
    all non-alphanumeric characters with underscores.

    Args:
        url: The URL or domain string to clean.

    Returns:
        str: A sanitized string suitable for cache filenames or identifiers.
    """
    # This regex [^a-zA-Z0-9] matches anything that is NOT a letter or number
    # and replaces it with an underscore
    sanitized = re.sub(r'[^a-zA-Z0-9]', '_', url)

    # Optional: Clean up double underscores and trailing underscores
    return re.sub(r'_+', '_', sanitized).strip('_')

def get_servers():
    server_count = int(os.environ.get('SERVERS_COUNT', '1'))
    server_list: List[InputServer] = []
    for i in range(server_count):
        server_list.append(InputServer(openapi_url=os.environ.get(f'SERVERS{i}_OPENAPI_URL')))
    return server_list