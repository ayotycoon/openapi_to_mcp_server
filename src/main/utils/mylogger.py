"""
Global logging configuration for the project.
Sets up a configured logger instance that writes to both a file and standard output,
respecting the LOG_LEVEL environment variable.
"""

import logging
import os

from src.main.utils.dir import project_root

ENV_LOG_LEVEL = os.environ.get("LOG_LEVEL")

log_file_path = os.path.join(project_root, os.path.join("logs", "server.log"))
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
level = logging.INFO
if ENV_LOG_LEVEL == 'DEBUG':
    level = logging.DEBUG
elif ENV_LOG_LEVEL == 'WARNING':
    level = logging.WARNING
elif ENV_LOG_LEVEL == 'ERROR':
    level = logging.ERROR
elif ENV_LOG_LEVEL == 'CRITICAL':
    level = logging.CRITICAL
logging.basicConfig(
    level=level,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path, mode="a"),
        logging.StreamHandler()
    ]
)

mylogger = logging