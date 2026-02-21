import json
import os
from typing import Any, Dict

from src.main.utils.dir import project_root
from src.main.utils.mylogger import mylogger


def read_file(path: str, is_json: bool) -> Dict[str, Any] | str:
    """
    Reads a file from the file system, resolving its path relative to the project root.

    Args:
        path: The relative path to the file from the project root.
        is_json: If True, parses and returns the file contents as a JSON dictionary.
                 If False, returns the raw string content.

    Returns:
        Dict[str, Any] | str: The parsed JSON dictionary or raw file contents.
    """

    absolute_path = os.path.join(project_root, path)
    mylogger.debug(f"opening, {absolute_path}")
    with open(absolute_path, "r", encoding="utf-8") as f:
        if is_json:
            return json.load(f)
        else:
            return f.read()



def write_to_file(path: str, data: Any, is_json: bool ) -> None:
    """
    Writes data to a file on the file system, resolving its path relative to the project root.

    Args:
        path: The relative path to the file from the project root.
        data: The data to write.
        is_json: If True, writes the data as formatted JSON.
                 If False, writes the string data directly.
    """
    absolute_path = os.path.join(project_root, path)
    mylogger.debug(f"writing, {absolute_path}")
    with open(absolute_path, "w", encoding="utf-8") as f:
        if is_json:
            json.dump(data, f, indent=4)
        else:
            f.write(data)

