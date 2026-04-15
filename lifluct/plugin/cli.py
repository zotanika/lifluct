"""CLI for installing and running the LIFLUCT MCP server."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _plugin_dir() -> Path:
    """Locate the plugin directory shipped with the package."""
    # When installed via pip, plugin/ is at the package root
    # When developing, it's at the repo root
    candidates = [
        Path(__file__).parent.parent.parent / "plugin",  # dev: lifluct/plugin/cli.py -> ../../plugin
        Path(__file__).parent / "plugin_data",             # installed: bundled data
    ]
    for c in candidates:
        if c.is_dir() and (c / ".claude-plugin").is_dir():
            return c
    return candidates[0]  # fallback


def install_claude_code() -> None:
    """Print instructions for Claude Code plugin installation."""
    plugin_dir = _plugin_dir()
    print("LIFLUCT AI Assistant Plugin")
    print(f"Plugin directory: {plugin_dir}")
    print()
    print("To install in Claude Code:")
    print("  claude plugin install lifluct")
    print()
    print("Or manually add to your Claude Code settings:")
    print(f'  "lifluct": {{"command": "{plugin_dir}/scripts/bootstrap-mcp.sh"}}')


def install_gemini() -> None:
    """Print MCP config for Gemini CLI."""
    config_path = _plugin_dir() / "ai" / "adapters" / "gemini_cli" / "mcp_config.json"
    if config_path.exists():
        print("Add this to your Gemini CLI MCP configuration:")
        print(config_path.read_text())
    else:
        print(f"Gemini config not found at {config_path}")


def install_codex() -> None:
    """Print MCP config for Codex."""
    config_path = _plugin_dir() / "ai" / "adapters" / "codex" / "mcp_config.json"
    if config_path.exists():
        print("Add this to your Codex MCP configuration:")
        print(config_path.read_text())
    else:
        print(f"Codex config not found at {config_path}")


def serve() -> None:
    """Run the MCP server."""
    server_path = _plugin_dir() / "mcp" / "server" / "server.py"
    if not server_path.exists():
        print(f"Server not found at {server_path}", file=sys.stderr)
        sys.exit(1)
    # Add server directory to path and run
    sys.path.insert(0, str(server_path.parent))
    from server import main as server_main
    server_main()


def build_parser(subparsers) -> None:
    """Register as a subcommand of ``lifluct``."""
    mcp_parser = subparsers.add_parser(
        "mcp", help="LIFLUCT MCP server -- AI-assisted liquidity policy experiments"
    )
    sub = mcp_parser.add_subparsers(dest="mcp_command")

    install_parser = sub.add_parser("install", help="Show installation instructions for a platform")
    install_group = install_parser.add_mutually_exclusive_group(required=True)
    install_group.add_argument("--claude-code", action="store_true", help="Claude Code plugin")
    install_group.add_argument("--gemini", action="store_true", help="Gemini CLI extension")
    install_group.add_argument("--codex", action="store_true", help="Codex skill")

    sub.add_parser("serve", help="Run the MCP server directly")

    mcp_parser.set_defaults(func=_run_mcp)


def _run_mcp(args) -> None:
    if getattr(args, "mcp_command", None) == "install":
        if args.claude_code:
            install_claude_code()
        elif args.gemini:
            install_gemini()
        elif args.codex:
            install_codex()
    elif getattr(args, "mcp_command", None) == "serve":
        serve()
    else:
        # No sub-subcommand given; print help for mcp
        import sys
        print("usage: lifluct mcp {install,serve} ...", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Standalone entry point for backward compatibility."""
    parser = argparse.ArgumentParser(
        description="LIFLUCT MCP server -- AI-assisted liquidity policy experiments"
    )
    sub = parser.add_subparsers(dest="command")

    install_parser = sub.add_parser("install", help="Show installation instructions for a platform")
    install_group = install_parser.add_mutually_exclusive_group(required=True)
    install_group.add_argument("--claude-code", action="store_true", help="Claude Code plugin")
    install_group.add_argument("--gemini", action="store_true", help="Gemini CLI extension")
    install_group.add_argument("--codex", action="store_true", help="Codex skill")

    sub.add_parser("serve", help="Run the MCP server directly")

    args = parser.parse_args()
    if args.command == "install":
        if args.claude_code:
            install_claude_code()
        elif args.gemini:
            install_gemini()
        elif args.codex:
            install_codex()
    elif args.command == "serve":
        serve()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
