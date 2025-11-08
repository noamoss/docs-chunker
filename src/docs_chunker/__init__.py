import logging
import os

__all__ = ["__version__"]

__version__ = "0.1.0"

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Default: only warnings and errors
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Allow debug logging via environment variable
if os.getenv("DOCS_CHUNKER_DEBUG"):
    logging.getLogger("docs_chunker").setLevel(logging.DEBUG)
