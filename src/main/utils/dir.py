"""
Global directory configuration constants for the project.
This module sets up paths relative to the current file to easily locate the project root.
"""

import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..','..'))
