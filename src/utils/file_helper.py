import json
import logging
import os
from typing import Any, Dict

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))

def read_json(path: str, is_json: bool = True) -> Dict[str, Any] | str:

    absolute_path = os.path.join(project_root, path)
    logging.debug(f"opening, {absolute_path}")
    with open(absolute_path, "r", encoding="utf-8") as f:
        if is_json:
            return json.load(f)
        else:
            return f.read()



def write_json(path: str, data: Any, is_json: bool = True) -> None:
    absolute_path = os.path.join(project_root, path)
    logging.debug(f"writing, {absolute_path}")
    with open(absolute_path, "w", encoding="utf-8") as f:
        if is_json:
            json.dump(data, f, indent=4)
        else:
            f.write(data)

