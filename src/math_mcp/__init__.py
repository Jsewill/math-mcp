"""math-mcp — exact, arbitrary-precision, symbolic math over MCP."""

from . import limits, models
from .server import main, mcp

__all__ = ["limits", "main", "mcp", "models"]
__version__ = "0.2.1"
