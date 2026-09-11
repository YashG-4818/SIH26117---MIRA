"""
core — the engine room of the Sovereign AI Workbench.

Import order matters exactly once: netguard must be installed before anything
opens a socket. app.py does that on line one. Everything else can be imported
in any order.
"""

__all__ = [
    "audit", "netguard", "llm", "chunker", "extract", "kb",
    "sandbox", "outputs", "tools", "agent",
]
