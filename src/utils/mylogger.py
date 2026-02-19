import logging
import os
from src.utils.file_helper import project_root


log_file_path = os.path.join(project_root, os.path.join("logs", "server.log"))
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path, mode="a"),
        logging.StreamHandler()
    ]
)

mylogger = logging