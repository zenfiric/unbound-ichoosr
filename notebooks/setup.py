"""Notebook environment setup."""

import asyncio
import base64
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from IPython.display import display, update_display

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def load_ipython_extension(ipython):
    """
    Configure the IPython environment by:
    - adding the project directory to the system path
    - loading environment variables from a .env file
    - injecting the `load_binary_file` function into IPython's namespace.
    """
    project_dir = Path().resolve().parent
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))

    load_dotenv(project_dir / ".env", override=True)
    log.info("IPython environment configured successfully!")
