import socket
from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.table import Table

console = Console()


class SubdomainEnumerator:
    def __init__(self, config):
        self.config = config
        self.setup_subdomain_list()

    def setup_subdomain_list(self):
        """Setup the subdomain list path."""
        # First check if there's a custom path in config
        config_path = self.config.get("subdomain", "wordlist_path")
        if config_path:
            self.wordlist_path = Path(config_path)
        else:
            # Default to project's wordlist
            self.wordlist_path = (
                Path(__file__).parent.parent / "wordlists" / "subdomains.txt"
            )

        if not self.wordlist_path.exists():
            raise FileNotFoundError(
                f"Subdomain wordlist not found at {self.wordlist_path}"
            )

    def load_subdomains(self) -> list[str]:
        """Load subdomain list from file."""
        with open(self.wordlist_path) as f:
            return [line.strip() for line in f if line.strip()]

    def resolve_domain(self, domain: str) -> tuple[str, str]:
        """Resolve a single domain to IP address."""
        try:
            ip_address = socket.gethostbyname(domain)
            return domain, ip_address
        except OSError:
            return domain, "Could Not Resolve"

    def enumerate_subdomains(
        self, base_url: str, show_all: bool = False
    ) -> dict[str, str]:
        """Enumerate subdomains for a given base URL."""
        # Validate base URL
        try:
            socket.gethostbyname(base_url)
        except OSError:
            console.print(f"[red]Error: Could not resolve base URL {base_url}[/red]")
            return {}

        subdomains = self.load_subdomains()
        results = {}

        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Enumerating subdomains...", total=len(subdomains)
            )

            for sub in subdomains:
                full_url = f"{sub}.{base_url}"
                domain, ip = self.resolve_domain(full_url)

                if show_all or ip != "Could Not Resolve":
                    results[domain] = ip

                progress.update(task, advance=1)

        self._print_results(results)
        return results

    def _print_results(self, results: dict[str, str]) -> None:
        """Print formatted results."""
        if not results:
            console.print("[yellow]No subdomains found.[/yellow]")
            return

        # Group by IP address result table
        grouped = defaultdict(list)
        for domain, ip in results.items():
            if ip != "Could Not Resolve":
                grouped[ip].append(domain)

        if grouped:
            console.print(
                "\n[cyan]Subdomain Enumeration Results Grouped by IP Address[/cyan]"
            )
            ip_table = Table(show_header=True)
            ip_table.add_column("IP Address", style="green")
            ip_table.add_column("Subdomains", style="cyan")

            for ip, domains in sorted(grouped.items()):
                ip_table.add_row(ip, "\n".join(sorted(domains)))

            console.print(ip_table)

        # Print statistics
        console.print("\n[yellow]Statistics:[/yellow]")
        console.print(f"Total subdomains found: {len(results)}")
        console.print(f"Unique IP addresses: {len(grouped)}")
