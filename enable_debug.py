"""Enable debug logging for troubleshooting."""

import logging

# Set debug level for igent logger
logging.getLogger("igent").setLevel(logging.DEBUG)

# Also set for autogen if needed
logging.getLogger("autogen").setLevel(logging.INFO)

# Configure handler to show debug messages
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# Add handler if not already added
logger = logging.getLogger("igent")
if not logger.handlers:
    logger.addHandler(handler)

print("✅ Debug logging enabled for 'igent' logger")
