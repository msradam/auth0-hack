"""
Amanat CLI - Rich terminal interface for the data governance agent.

Usage:
    uv run python -m amanat              # Interactive mode (demo data)
    uv run python -m amanat -q "scan"    # Single query mode
    uv run python -m amanat --live       # Real Auth0 (requires tenant)
"""

import argparse
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from amanat.agent import AmanatAgent
from amanat.auth import Auth0TokenVault
from amanat.tools.scanner import execute_tool

console = Console()


BANNER = r"""
  █████╗ ███╗   ███╗ █████╗ ███╗   ██╗ █████╗ ████████╗
 ██╔══██╗████╗ ████║██╔══██╗████╗  ██║██╔══██╗╚══██╔══╝
 ███████║██╔████╔██║███████║██╔██╗ ██║███████║   ██║
 ██╔══██║██║╚██╔╝██║██╔══██║██║╚██╗██║██╔══██║   ██║
 ██║  ██║██║ ╚═╝ ██║██║  ██║██║ ╚████║██║  ██║   ██║
 ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝
"""


def show_banner():
    console.print(Text(BANNER, style="bold blue"))
    console.print(
        Panel(
            "[bold]Safe Hands for Humanitarian Data[/bold]\n"
            "Privacy-first data governance agent\n"
            "Powered by IBM Granite 4 Micro (local) + Auth0 Token Vault",
            border_style="blue",
            padding=(1, 2),
        )
    )
    console.print()


def show_consent(vault: Auth0TokenVault):
    """Display consent summary - what services the user has authorized."""
    summary = vault.get_consent_summary()
    if not summary["authenticated"]:
        console.print("[red]Not authenticated[/red]")
        return

    table = Table(title="Authorized Connections", border_style="blue")
    table.add_column("Service", style="cyan")
    table.add_column("Scope", style="dim")
    table.add_column("Status", style="green")

    for svc in summary["connected_services"]:
        status_style = "green" if svc["status"] == "connected" else "red"
        table.add_row(
            svc["service"],
            svc["scope"],
            Text(svc["status"], style=status_style),
        )

    console.print(
        Panel(
            f"[bold]{summary['user']}[/bold] ({summary['email']})\n"
            f"Organisation: {summary['org']}",
            title="Authenticated User",
            border_style="green",
        )
    )
    console.print(table)
    console.print()


def show_privacy_notice():
    """Show the privacy guarantee."""
    console.print(
        Panel(
            "[bold green]Privacy Guarantee[/bold green]\n\n"
            "All data analysis runs locally on IBM Granite 4 Micro.\n"
            "No beneficiary data leaves this machine.\n"
            "Auth0 Token Vault handles only identity tokens, not your data.\n"
            "The model is Apache 2.0, ISO 42001 certified, cryptographically signed.",
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()


def run_interactive(agent: AmanatAgent, vault: Auth0TokenVault):
    """Interactive REPL mode."""
    show_banner()

    # Authenticate
    with console.status("[bold blue]Authenticating via Auth0...[/bold blue]"):
        session = vault.login()
    show_consent(vault)
    show_privacy_notice()

    console.print("[bold]Ready.[/bold] Ask Amanat to audit your data, or type a question.\n")
    console.print("[dim]Examples:[/dim]")
    console.print("  [cyan]Scan all files for sensitive data[/cyan]")
    console.print("  [cyan]Check which files are shared publicly[/cyan]")
    console.print("  [cyan]Search Slack for beneficiary names[/cyan]")
    console.print("  [cyan]Are we GDPR compliant for how we handle case files?[/cyan]")
    console.print("  [dim]/quit to exit[/dim]\n")

    while True:
        try:
            query = console.input("[bold blue]amanat>[/bold blue] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not query:
            continue
        if query.lower() in ("/quit", "/exit", "quit", "exit"):
            console.print("[dim]Goodbye.[/dim]")
            break

        with console.status("[bold blue]Analyzing with Granite 4 Micro (local)...[/bold blue]"):
            try:
                response = agent.run(query)
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                continue

        console.print()
        console.print(Panel(Markdown(response), title="Amanat Report", border_style="blue"))
        console.print()


def run_single(agent: AmanatAgent, vault: Auth0TokenVault, query: str):
    """Single query mode."""
    show_banner()

    with console.status("[bold blue]Authenticating...[/bold blue]"):
        vault.login()
    show_consent(vault)

    console.print(f"[bold]Query:[/bold] {query}\n")

    with console.status("[bold blue]Analyzing with Granite 4 Micro (local)...[/bold blue]"):
        response = agent.run(query)

    console.print(Panel(Markdown(response), title="Amanat Report", border_style="blue"))


def main():
    parser = argparse.ArgumentParser(description="Amanat - Humanitarian Data Governance Agent")
    parser.add_argument("-q", "--query", help="Single query mode")
    parser.add_argument("--live", action="store_true", help="Use real Auth0 tenant (requires config)")
    parser.add_argument("--model", default="granite4-micro", help="Model name (default: granite4-micro)")
    parser.add_argument("--base-url", default="http://localhost:8080/v1", help="LLM API base URL")
    args = parser.parse_args()

    # Initialize Auth0
    vault = Auth0TokenVault(demo_mode=not args.live)

    # Initialize agent
    agent = AmanatAgent(
        base_url=args.base_url,
        model=args.model,
        tool_executor=execute_tool,
    )

    if args.query:
        run_single(agent, vault, args.query)
    else:
        run_interactive(agent, vault)


if __name__ == "__main__":
    main()
