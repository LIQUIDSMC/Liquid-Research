"""
Liquid Research — API Sanity Check
Confirms all public Polymarket API endpoints are reachable.
No wallet. No auth. No private key. Read-only.
Usage: python3 collectors/api_sanity_check.py
"""

import requests
from rich.console import Console
from rich.table import Table

console = Console()

ENDPOINTS = [
    {
        "name": "Gamma API — Markets",
        "url": "https://gamma-api.polymarket.com/markets",
        "params": {"limit": 1, "active": "true"},
    },
    {
        "name": "Gamma API — Events",
        "url": "https://gamma-api.polymarket.com/events",
        "params": {"limit": 1},
    },
    {
        "name": "CLOB API — Status",
        "url": "https://clob.polymarket.com/",
        "params": {},
    },
    {
        "name": "Data API — Markets",
        "url": "https://data-api.polymarket.com/markets",
        "params": {"limit": 1},
    },
]

def check_endpoint(name, url, params):
    try:
        response = requests.get(url, params=params, timeout=10)
        status = response.status_code
        size = len(response.content)
        if status == 200:
            return ("✓", name, str(status), f"{size} bytes", "OK")
        else:
            return ("✗", name, str(status), f"{size} bytes", "NON-200")
    except requests.exceptions.ConnectionError:
        return ("✗", name, "—", "—", "CONNECTION ERROR")
    except requests.exceptions.Timeout:
        return ("✗", name, "—", "—", "TIMEOUT")
    except Exception as e:
        return ("✗", name, "—", "—", str(e)[:40])

def main():
    console.print("\n[bold cyan]Liquid Research — API Sanity Check[/bold cyan]")
    console.print("[dim]Testing all public Polymarket endpoints...[/dim]\n")

    table = Table(show_lines=True)
    table.add_column("", width=3)
    table.add_column("Endpoint", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Response", justify="right", style="dim")
    table.add_column("Result", justify="left")

    all_ok = True

    for ep in ENDPOINTS:
        icon, name, status, size, result = check_endpoint(
            ep["name"], ep["url"], ep["params"]
        )
        if icon == "✓":
            table.add_row(
                f"[green]{icon}[/green]", name, status, size,
                f"[green]{result}[/green]"
            )
        else:
            all_ok = False
            table.add_row(
                f"[red]{icon}[/red]", name, status, size,
                f"[red]{result}[/red]"
            )

    console.print(table)

    if all_ok:
        console.print("\n[bold green]All endpoints reachable. Safe to proceed.[/bold green]\n")
    else:
        console.print("\n[bold red]One or more endpoints failed. Check connection before proceeding.[/bold red]\n")

if __name__ == "__main__":
    main()
