"""Generic MCP client: connect MCP servers and reach their tools on demand."""

from __future__ import annotations

from airaider.tools.mcp.agent_tools import call_mcp, describe_mcp, list_mcps
from airaider.tools.mcp.client import (
    ConnectedMcpServer,
    attach_mcp_requests,
    connect_mcp_servers,
)
from airaider.tools.mcp.config import (
    BearerAuth,
    McpAuth,
    McpConnectionConfig,
)
from airaider.tools.mcp.failures import FailureInfo, HttpStatusRecorder, classify
from airaider.tools.mcp.loader import load_user_mcp_configs
from airaider.tools.mcp.naming import namespaced_tool_name
from airaider.tools.mcp.registry import (
    CALL_MCP_TOOL,
    DESCRIBE_MCP_TOOL,
    MCP_DISPATCH_TOOLS,
    MCP_REGISTRY_CONTEXT_KEY,
    McpCallInfo,
    McpConnectionEntry,
    McpConnectionRequest,
    McpConnectionStatus,
    McpConnectionSummary,
    McpRegistry,
    resolve_mcp_call,
)
from airaider.tools.mcp.session import McpConnectionUnavailableError, SupervisedMcpSession


__all__ = [
    "CALL_MCP_TOOL",
    "DESCRIBE_MCP_TOOL",
    "MCP_DISPATCH_TOOLS",
    "MCP_REGISTRY_CONTEXT_KEY",
    "BearerAuth",
    "ConnectedMcpServer",
    "FailureInfo",
    "HttpStatusRecorder",
    "McpAuth",
    "McpCallInfo",
    "McpConnectionConfig",
    "McpConnectionEntry",
    "McpConnectionRequest",
    "McpConnectionStatus",
    "McpConnectionSummary",
    "McpConnectionUnavailableError",
    "McpRegistry",
    "SupervisedMcpSession",
    "attach_mcp_requests",
    "call_mcp",
    "classify",
    "connect_mcp_servers",
    "describe_mcp",
    "list_mcps",
    "load_user_mcp_configs",
    "namespaced_tool_name",
    "resolve_mcp_call",
]
