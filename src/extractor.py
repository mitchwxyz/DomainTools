from bs4 import BeautifulSoup
import requests
from datetime import datetime
import json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
import random
from pathlib import Path
from tinydb import TinyDB
from urllib.parse import urlparse, urljoin
import time
from src.utils import is_valid_url, clean_text
from src.config import Config

console = Console()

class WebExtractor:
    """Main class for extracting JSON-LD and text content from websites."""
    
    def __init__(self, config: Config):
        """Initialize the WebExtractor with configuration."""
        self.config = config
        self.visited_urls: set[str] = set()
        self.setup_databases()
        self.setup_http_client()

    def setup_databases(self) -> None:
        """Initialize TinyDB databases for storing scraped data."""
        db_path = Path(self.config.get('storage', 'db_path'))
        db_path.mkdir(parents=True, exist_ok=True)
        
        self.jsonld_db = TinyDB(
            db_path / self.config.get('scraper', 'jsonld_output')
        )
        self.text_db = TinyDB(
            db_path / self.config.get('scraper', 'text_output')
        )

    def setup_http_client(self) -> None:
        """Configure HTTP client settings and headers."""
        self.headers = {
            'User-Agent': self.config.get('http', 'user_agent'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        self.timeout = self.config.getint('http', 'timeout')
        self.max_retries = self.config.getint('http', 'max_retries')
        self.min_delay = self.config.getfloat('scraper', 'min_delay')
        self.max_delay = self.config.getfloat('scraper', 'max_delay')

    def fetch_url(self, url: str) -> requests.Response | None:
        """Make HTTP request with retry logic and delay."""
        if self.visited_urls:  # Don't delay on first request
            delay = random.uniform(self.min_delay, self.max_delay)
            console.print(f"[dim]Waiting {delay:.1f}s...[/dim]")
            time.sleep(delay)

        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    console.print(f"[red]Failed to fetch {url}: {str(e)}[/red]")
                    return None
                console.print(f"[yellow]Retry {attempt + 1}/{self.max_retries} for {url}: {str(e)}[/yellow]")
        
        return None

    def extract_jsonld(self, url: str, html_content: str, headers: dict) -> list[dict]:
        """Extract JSON-LD data from webpage content."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            jsonld_scripts = soup.find_all('script', type='application/ld+json')
            
            results = []
            for script in jsonld_scripts:
                try:
                    data = json.loads(script.string)
                    results.append({
                        'url': url,
                        'data': data,
                        'crawled_at': datetime.now().isoformat(),
                        'response_headers': dict(headers)
                    })
                except json.JSONDecodeError:
                    console.print(f"[yellow]Invalid JSON-LD found at {url}[/yellow]")
                    continue
            return results
            
        except Exception as e:
            console.print(f"[red]Error processing JSON-LD at {url}: {str(e)}[/red]")
            return []

    def extract_text(self, url: str, html_content: str) -> dict:
        """Extract meaningful text content from webpage content."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup.find_all([
                'script', 'style', 'nav', 'header', 'footer', 
                'button', 'input', 'form', 'iframe'
            ]):
                element.decompose()
            
            # Extract title
            title = soup.title.string if soup.title else ""
            
            # Extract meta description
            meta_desc = ""
            meta_tag = soup.find('meta', attrs={'name': 'description'})
            if meta_tag:
                meta_desc = meta_tag.get('content', '')
            
            # Extract headings
            headings = []
            for h in soup.find_all(['h1', 'h2', 'h3']):
                text = clean_text(h.get_text())
                if text and len(text) > 5:
                    headings.append({
                        'level': h.name,
                        'text': text
                    })
            
            # Extract main content
            paragraphs = []
            for p in soup.find_all(['p', 'article', 'section', 'div']):
                text = clean_text(p.get_text())
                if len(text) > 50 and not any(skip in text.lower() 
                    for skip in ['cookie', 'accept', 'subscribe']):
                    paragraphs.append(text)
            
            return {
                'url': url,
                'title': clean_text(title),
                'meta_description': clean_text(meta_desc),
                'headings': headings,
                'paragraphs': paragraphs,
                'crawled_at': datetime.now().isoformat(),
                'word_count': sum(len(p.split()) for p in paragraphs)
            }
            
        except Exception as e:
            console.print(f"[red]Error extracting text from {url}: {str(e)}[/red]")
            return {}
    def find_links(self, html_content: str, base_url: str) -> list[str]:
        """Extract valid links from webpage content."""
        base_domain = urlparse(base_url).netloc
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            links = set()
            
            for link in soup.find_all('a', href=True):
                next_url = urljoin(base_url, link['href'])
                if (is_valid_url(next_url, base_domain) and 
                    next_url not in self.visited_urls and 
                    next_url not in links):
                    links.add(next_url)
                    
            return list(links)
            
        except Exception as e:
            console.print(f"[red]Error finding links at {base_url}: {str(e)}[/red]")
            return []

    def process_page(self, url: str, extract_jsonld: bool = False, 
                    extract_text_content: bool = False) -> tuple[list[str], bool]:
        """Process a single page and extract requested content."""
        if url in self.visited_urls:
            return [], False

        self.visited_urls.add(url)
        response = self.fetch_url(url)
        
        if not response:
            return [], False

        status_color = "green" if response.status_code == 200 else "yellow"
        console.print(f"[{status_color}][{response.status_code}][/{status_color}] {url}")

        # Extract and store JSON-LD if requested
        if extract_jsonld:
            jsonld_data = self.extract_jsonld(url, response.text, response.headers)
            if jsonld_data:
                self.jsonld_db.insert_multiple(jsonld_data)
                console.print(f"[green]Found {len(jsonld_data)} JSON-LD items[/green]")

        # Extract and store text content if requested
        if extract_text_content:
            text_data = self.extract_text(url, response.text)
            if text_data:
                self.text_db.insert(text_data)
                console.print(
                    f"[green]Extracted {len(text_data.get('paragraphs', []))} "
                    f"paragraphs ({text_data.get('word_count', 0)} words)[/green]"
                )

        # Find new links
        new_urls = self.find_links(response.text, url)
        if new_urls:
            console.print(f"[blue]Found {len(new_urls)} new URLs to crawl[/blue]")
        
        return new_urls, True

    def crawl_site(self, start_url: str, extract_jsonld: bool = False, 
                  extract_text_content: bool = False) -> None:
        """Crawl website and extract specified content types."""
        max_pages = self.config.getint('scraper', 'max_pages')
        urls_to_visit = [start_url]
        
        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]Scraping content...", 
                total=max_pages
            )
            
            while urls_to_visit and len(self.visited_urls) < max_pages:
                url = urls_to_visit.pop(0)
                new_urls, success = self.process_page(
                    url, 
                    extract_jsonld, 
                    extract_text_content
                )
                
                if success and new_urls:
                    urls_to_visit.extend(new_urls)
                
                progress.update(task, completed=len(self.visited_urls))
            
        console.print(f"\n[green]Scraping completed![/green]")
        console.print(f"[green]Pages scraped: {len(self.visited_urls)}[/green]")

    def scrape_jsonld(self, url: str) -> None:
        """Scrape only JSON-LD data from a website."""
        self.crawl_site(url, extract_jsonld=True)

    def scrape_text(self, url: str) -> None:
        """Scrape only text content from a website."""
        self.crawl_site(url, extract_text_content=True)

    def scrape_all(self, url: str) -> None:
        """Scrape both JSON-LD and text content from a website."""
        self.crawl_site(url, extract_jsonld=True, extract_text_content=True)