import click
from rich.console import Console

from src.analysis import DataAnalyzer
from src.config import Config
from src.extractor import WebExtractor
from src.subdomain import SubdomainEnumerator

console = Console()


@click.group()
def cli():
    """Website content scraping tool"""
    pass


@cli.command(name="scrape-jsonld")
@click.argument("url")
@click.option("--max-pages", help="Maximum number of pages to scrape")
@click.option("--min-delay", help="Minimum delay between requests in seconds")
@click.option("--max-delay", help="Maximum delay between requests in seconds")
def scrape_jsonld(url: str, max_pages: int, min_delay: float, max_delay: float):
    """Scrape JSON-LD data from a website"""
    config = Config()
    extractor = WebExtractor(config)
    extractor.scrape_jsonld(url)


@cli.command(name="scrape-text")
@click.argument("url")
@click.option("--max-pages", help="Maximum number of pages to scrape")
@click.option("--min-delay", help="Minimum delay between requests in seconds")
@click.option("--max-delay", help="Maximum delay between requests in seconds")
def scrape_text(url: str, max_pages: int, min_delay: float, max_delay: float):
    """Scrape text content from a website"""
    config = Config()
    extractor = WebExtractor(config)
    extractor.scrape_text(url)


@cli.command(name="scrape-all")
@click.argument("url")
@click.option("--max-pages", help="Maximum number of pages to scrape")
@click.option(
    "--max-pages", type=int, default=None, help="Maximum number of pages to scrape"
)
@click.option("--min-delay", help="Minimum delay between requests in seconds")
@click.option("--max-delay", help="Maximum delay between requests in seconds")
def scrape_all(url: str, max_pages: int, min_delay: float, max_delay: float):
    """Scrape both JSON-LD and text content from a website"""
    config = Config()
    extractor = WebExtractor(config, max_pages)
    extractor.scrape_all(url)


@cli.command()
@click.argument("url", required=False)
@click.option("--wordlist", help="Path to custom subdomain wordlist")
@click.option(
    "--show-all", is_flag=True, help="Show all results including unresolved domains"
)
def enumerate_subdomains(
    url: str | None = None, wordlist: str | None = None, show_all: bool = False
):
    """
    Enumerate subdomains for a given URL.
    If no URL is provided, will prompt for one.
    """
    try:
        config = Config()
        if wordlist:
            config.config["subdomain"]["wordlist_path"] = wordlist

        # If no URL provided, prompt for one
        if not url:
            url = click.prompt("Please enter a URL to enumerate")

        # Strip any protocol prefix and trailing slashes
        url = url.replace("http://", "").replace("https://", "").rstrip("/")

        enumerator = SubdomainEnumerator(config)
        enumerator.enumerate_subdomains(url, show_all)
    except KeyboardInterrupt:
        console.print("\n[yellow]Enumeration cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error enumerating subdomains: {str(e)}[/red]")


@cli.command()
@click.argument("url", required=False)
def analyze(url: str | None = None):
    """Analyze collected data. Optionally provide a URL to analyze specific site data."""
    try:
        config = Config()
        analyzer = DataAnalyzer(config)
        analyzer.analyze(url)
    except NotImplementedError:
        console.print("[yellow]Analysis feature is not implemented yet.[/yellow]")


@cli.command()
@click.argument("property")
@click.argument("url", required=False)
def analyze_property(property: str, url: str | None):
    """
    Analyze a specific property in JSON-LD data.
    Optionally provide a URL to analyze data from a specific site.
    """
    try:
        config = Config()
        analyzer = DataAnalyzer(config)
        analyzer.analyze_property(property, url)
    except Exception as e:
        console.print(f"[red]Error analyzing property: {str(e)}[/red]")


@cli.command(name="analyze-text")
@click.argument("url", required=False)
def analyze_text(url: str | None = None):
    """
    Analyze collected text content.
    Optionally provide a URL to analyze specific site data.
    """
    try:
        config = Config()
        analyzer = DataAnalyzer(config)
        analyzer.analyze_text(url)
    except Exception as e:
        console.print(f"[red]Error analyzing text data: {str(e)}[/red]")
