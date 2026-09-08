"""Agentline MCP server.

Exposes Agentline (phone numbers, SMS, voice, email) as Model Context Protocol
tools so AI agents in Claude Desktop, Cursor, Zed, Windsurf, etc. can provision
numbers, capture 2FA codes, place voice calls, and send email — directly.
"""

from __future__ import annotations

__version__ = "0.2.0"

__all__ = ["__version__"]
