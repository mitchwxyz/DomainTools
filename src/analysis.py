from tinydb import TinyDB, Query
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict, Counter
from rich.console import Console
from rich.table import Table
from itertools import combinations
import json
import requests

from src.config import Config


console = Console()

class DataAnalyzer:
    """Analyzer for JSON-LD and text content data."""
    
    def __init__(self, config: Config):
        """Initialize the analyzer with configuration."""
        self.config = config
        db_path = Path(self.config.get('storage', 'db_path'))
        self.jsonld_db = TinyDB(db_path / self.config.get('scraper', 'jsonld_output'))
        self.text_db = TinyDB(db_path / self.config.get('scraper', 'text_output'))

    def _normalize_url(self, url: str) -> str:
        """Normalize URL to match domain."""
        parsed = urlparse(url)
        return parsed.netloc

    def _filter_data_by_url(self, url: str, db_type: str = 'jsonld') -> list[dict]:
        """Filter database entries by URL domain.
        
        Args:
            url: URL to filter by
            db_type: Type of database to filter ('jsonld' or 'text')
        """
        domain = self._normalize_url(url)
        Query_obj = Query()
        
        # Select the appropriate database
        db = self.jsonld_db if db_type == 'jsonld' else self.text_db
        
        # Filter entries where the URL contains the domain
        return db.search(
            Query_obj.url.test(lambda x: domain in x)
        )

    def analyze_jsonld(self, url: str | None = None) -> dict:
        """Analyze the JSON-LD data."""
        if url:
            data = self._filter_data_by_url(url, db_type='jsonld')  # Specify db_type here
            site_info = f" for {self._normalize_url(url)}"
        else:
            data = self.jsonld_db.all()
            site_info = " across all sites"

        if not data:
            console.print(f"[yellow]No JSON-LD data found{site_info}[/yellow]")
            return {}
        
        # Initialize analysis containers
        analysis = {
            'total_pages': len({item['url'] for item in data}),
            'total_items': len(data),
            'types': {},
            'contexts': {},
            'authors': {},
            'organizations': {},
            'dates': {
                'published': {},
                'modified': {}
            },
            'properties': {},
            'nested_types': {}
        }

        # Analyze each JSON-LD item
        for item in data:
            self._analyze_jsonld_item(item['data'], analysis)

        self._print_jsonld_analysis(analysis, site_info)
        return analysis

    def _analyze_jsonld_item(self, data: dict, analysis: dict, depth: int = 0) -> None:
        """Recursively analyze a JSON-LD item."""
        if isinstance(data, list):
            for item in data:
                self._analyze_jsonld_item(item, analysis, depth)
            return

        if not isinstance(data, dict):
            return

        # Analyze type (handle both single string and list of types)
        if '@type' in data:
            types = data['@type']
            if isinstance(types, str):
                if depth == 0:
                    analysis['types'][types] = analysis['types'].get(types, 0) + 1
                else:
                    analysis['nested_types'][types] = analysis['nested_types'].get(types, 0) + 1
            elif isinstance(types, list):
                for type_name in types:
                    if isinstance(type_name, str):
                        if depth == 0:
                            analysis['types'][type_name] = analysis['types'].get(type_name, 0) + 1
                        else:
                            analysis['nested_types'][type_name] = analysis['nested_types'].get(type_name, 0) + 1

        # Analyze context
        if '@context' in data:
            contexts = data['@context']
            if isinstance(contexts, str):
                analysis['contexts'][contexts] = analysis['contexts'].get(contexts, 0) + 1
            elif isinstance(contexts, list):
                for ctx in contexts:
                    if isinstance(ctx, str):
                        analysis['contexts'][ctx] = analysis['contexts'].get(ctx, 0) + 1
            elif isinstance(contexts, dict):
                # Handle context objects by using their keys
                for ctx_key in contexts.keys():
                    if isinstance(ctx_key, str):
                        analysis['contexts'][ctx_key] = analysis['contexts'].get(ctx_key, 0) + 1

        # Analyze authors
        if 'author' in data:
            self._extract_author(data['author'], analysis)

        # Analyze organizations
        if isinstance(data.get('@type'), str) and data['@type'] in ['Organization', 'Corporation', 'Company']:
            org_name = data.get('name', 'Unknown Organization')
            analysis['organizations'][org_name] = analysis['organizations'].get(org_name, 0) + 1
        elif isinstance(data.get('@type'), list):
            if any(t in ['Organization', 'Corporation', 'Company'] for t in data['@type']):
                org_name = data.get('name', 'Unknown Organization')
                analysis['organizations'][org_name] = analysis['organizations'].get(org_name, 0) + 1

        # Analyze dates
        if 'datePublished' in data:
            date = data['datePublished'][:10]  # Get just the date part
            analysis['dates']['published'][date] = analysis['dates']['published'].get(date, 0) + 1
        if 'dateModified' in data:
            date = data['dateModified'][:10]  # Get just the date part
            analysis['dates']['modified'][date] = analysis['dates']['modified'].get(date, 0) + 1

        # Count property usage
        for key in data.keys():
            if not key.startswith('@'):
                analysis['properties'][key] = analysis['properties'].get(key, 0) + 1

        # Recurse into nested objects
        for value in data.values():
            if isinstance(value, (dict, list)):
                self._analyze_jsonld_item(value, analysis, depth + 1)

    def _extract_author(self, author_data: dict, analysis: dict) -> None:
        """Extract and analyze author information."""
        if isinstance(author_data, str):
            analysis['authors'][author_data] = analysis['authors'].get(author_data, 0) + 1
        elif isinstance(author_data, list):
            for author in author_data:
                self._extract_author(author, analysis)
        elif isinstance(author_data, dict):
            author_name = author_data.get('name', 'Unknown Author')
            analysis['authors'][author_name] = analysis['authors'].get(author_name, 0) + 1

    def _print_jsonld_analysis(self, analysis: dict, site_info: str) -> None:
        """Print formatted analysis results."""
        console.print(f"\n[cyan]JSON-LD Analysis Report{site_info}[/cyan]")
        console.print("=" * 50)

        # Basic stats
        console.print(f"\n[yellow]Basic Statistics:[/yellow]")
        console.print(f"Total Pages Scraped: {analysis['total_pages']}")
        console.print(f"Total JSON-LD Items: {analysis['total_items']}")
        if analysis['total_pages'] > 0:
            console.print(f"Items per Page: {analysis['total_items'] / analysis['total_pages']:.2f}")

        # Types table
        if analysis['types']:
            console.print("\n[yellow]Top JSON-LD Types:[/yellow]")
            table = Table(show_header=True)
            table.add_column("Type", style="cyan")
            table.add_column("Count", style="green", justify="right")
            table.add_column("Percentage", style="blue", justify="right")
            
            total_types = sum(analysis['types'].values())
            sorted_types = sorted(analysis['types'].items(), key=lambda x: x[1], reverse=True)
            for type_name, count in sorted_types[:10]:
                percentage = (count / total_types) * 100
                table.add_row(
                    type_name,
                    str(count),
                    f"{percentage:.1f}%"
                )
            console.print(table)

        # Authors table
        if analysis['authors']:
            console.print("\n[yellow]Top Authors:[/yellow]")
            table = Table(show_header=True)
            table.add_column("Author", style="cyan")
            table.add_column("Count", style="green", justify="right")
            
            sorted_authors = sorted(analysis['authors'].items(), key=lambda x: x[1], reverse=True)
            for author, count in sorted_authors[:10]:
                table.add_row(author, str(count))
            console.print(table)

        # Organizations table
        if analysis['organizations']:
            console.print("\n[yellow]Top Organizations:[/yellow]")
            table = Table(show_header=True)
            table.add_column("Organization", style="cyan")
            table.add_column("Count", style="green", justify="right")
            
            sorted_orgs = sorted(analysis['organizations'].items(), key=lambda x: x[1], reverse=True)
            for org, count in sorted_orgs[:10]:
                table.add_row(org, str(count))
            console.print(table)

        # Properties table
        if analysis['properties']:
            console.print("\n[yellow]Most Common Properties:[/yellow]")
            table = Table(show_header=True)
            table.add_column("Property", style="cyan")
            table.add_column("Usage Count", style="green", justify="right")
            
            sorted_props = sorted(analysis['properties'].items(), key=lambda x: x[1], reverse=True)
            for prop, count in sorted_props[:15]:
                table.add_row(prop, str(count))
            console.print(table)

        # Contexts
        if analysis['contexts']:
            console.print("\n[yellow]JSON-LD Contexts Used:[/yellow]")
            sorted_contexts = sorted(analysis['contexts'].items(), key=lambda x: x[1], reverse=True)
            for context, count in sorted_contexts:
                console.print(f"  {context}: {count}")

    def analyze(self, url: str | None = None) -> None:
        """Analyze all collected data."""
        self.analyze_jsonld(url)
        # Text analysis can be added later

    def analyze_property(self, property_name: str, url: str | None = None) -> dict:
        """Analyze a specific property across JSON-LD data, optionally filtered by URL."""
        if url:
            data = self._filter_data_by_url(url)
            site_info = f" for {self._normalize_url(url)}"
        else:
            data = self.jsonld_db.all()
            site_info = " across all sites"

        if not data:
            console.print(f"[yellow]No JSON-LD data found{site_info}[/yellow]")
            return {}

        analysis = {
            'property': property_name,
            'total_occurrences': 0,
            'unique_values': set(),
            'value_counts': {},
            'nested_occurrences': 0,
            'types_containing_property': set(),
            'context_usage': set(),
            'data_types': set(),
            'urls_containing_property': set(),  # New: track URLs where property appears
        }

        def analyze_dict(item: dict, item_url: str, is_nested: bool = False) -> None:
            """Recursively analyze dictionary for property."""
            if not isinstance(item, dict):
                return

            # Track property in current level
            if property_name in item:
                value = item[property_name]
                analysis['total_occurrences'] += 1
                analysis['urls_containing_property'].add(item_url)
                
                if is_nested:
                    analysis['nested_occurrences'] += 1

                # Track the @type of items containing this property
                if '@type' in item:
                    if isinstance(item['@type'], list):
                        analysis['types_containing_property'].update(item['@type'])
                    else:
                        analysis['types_containing_property'].add(item['@type'])

                # Track @context when property is found
                if '@context' in item:
                    if isinstance(item['@context'], str):
                        analysis['context_usage'].add(item['@context'])
                    elif isinstance(item['@context'], list):
                        analysis['context_usage'].update(
                            [ctx for ctx in item['@context'] if isinstance(ctx, str)]
                        )
                    elif isinstance(item['@context'], dict):
                        analysis['context_usage'].update(item['@context'].keys())

                # Analyze the value
                if isinstance(value, (str, int, float, bool)):
                    analysis['unique_values'].add(str(value))
                    analysis['value_counts'][str(value)] = analysis['value_counts'].get(str(value), 0) + 1
                    analysis['data_types'].add(type(value).__name__)
                elif isinstance(value, list):
                    analysis['data_types'].add('list')
                    for v in value:
                        if isinstance(v, (str, int, float, bool)):
                            analysis['unique_values'].add(str(v))
                            analysis['value_counts'][str(v)] = analysis['value_counts'].get(str(v), 0) + 1
                        elif isinstance(v, dict):
                            analyze_dict(v, item_url, True)
                elif isinstance(value, dict):
                    analysis['data_types'].add('dict')
                    analyze_dict(value, item_url, True)

            # Recursively check nested dictionaries
            for v in item.values():
                if isinstance(v, dict):
                    analyze_dict(v, item_url, True)
                elif isinstance(v, list):
                    for nested_item in v:
                        if isinstance(nested_item, dict):
                            analyze_dict(nested_item, item_url, True)

        # Analyze each JSON-LD item
        for item in data:
            analyze_dict(item['data'], item['url'])

        # Convert sets to sorted lists for output
        analysis['unique_values'] = sorted(analysis['unique_values'])
        analysis['types_containing_property'] = sorted(analysis['types_containing_property'])
        analysis['context_usage'] = sorted(analysis['context_usage'])
        analysis['data_types'] = sorted(analysis['data_types'])
        analysis['urls_containing_property'] = sorted(analysis['urls_containing_property'])

        self._print_property_analysis(analysis, site_info)
        return analysis

    def _print_property_analysis(self, analysis: dict, site_info: str) -> None:
        """Print formatted property analysis results."""
        console.print(f"\n[cyan]Property Analysis Report for '{analysis['property']}'{site_info}[/cyan]")
        console.print("=" * 50)

        # Basic stats
        console.print(f"\n[yellow]Basic Statistics:[/yellow]")
        console.print(f"Total Occurrences: {analysis['total_occurrences']}")
        console.print(f"Nested Occurrences: {analysis['nested_occurrences']}")
        console.print(f"Unique Values: {len(analysis['unique_values'])}")
        console.print(f"Pages Containing Property: {len(analysis['urls_containing_property'])}")
        console.print(f"Data Types Used: {', '.join(analysis['data_types'])}")

        # Top 10 Values with detailed information
        if analysis['value_counts']:
            console.print("\n[yellow]Top 10 Values:[/yellow]")
            
            # Create main value table
            value_table = Table(show_header=True, title="Value Distribution")
            value_table.add_column("Rank", style="dim", justify="right")
            value_table.add_column("Value", style="cyan")
            value_table.add_column("Count", style="green", justify="right")
            value_table.add_column("Percentage", style="blue", justify="right")
            value_table.add_column("Sample URL", style="magenta")
            
            total_values = sum(analysis['value_counts'].values())
            sorted_values = sorted(analysis['value_counts'].items(), 
                                key=lambda x: x[1], reverse=True)
            
            # Find URLs containing each value
            value_urls = defaultdict(list)
            for item in self.jsonld_db:
                def find_value_in_dict(d, value):
                    if isinstance(d, dict):
                        for k, v in d.items():
                            if k == analysis['property']:
                                if isinstance(v, (str, int, float, bool)) and str(v) == value:
                                    return True
                                elif isinstance(v, list):
                                    return any(str(x) == value for x in v if isinstance(x, (str, int, float, bool)))
                            elif isinstance(v, (dict, list)):
                                if find_value_in_dict(v, value):
                                    return True
                    elif isinstance(d, list):
                        return any(find_value_in_dict(x, value) for x in d)
                    return False

                for value, _ in sorted_values[:10]:
                    if find_value_in_dict(item['data'], value):
                        value_urls[value].append(item['url'])

            # Add rows to the table
            for rank, (value, count) in enumerate(sorted_values[:10], 1):
                percentage = (count / total_values) * 100
                sample_url = value_urls[value][0] if value_urls[value] else "N/A"
                sample_url = sample_url[:50] + "..." if len(sample_url) > 50 else sample_url
                
                display_value = value
                if len(display_value) > 50:
                    display_value = display_value[:47] + "..."
                
                value_table.add_row(
                    str(rank),
                    display_value,
                    str(count),
                    f"{percentage:.1f}%",
                    sample_url
                )
            
            console.print(value_table)

            # Print detailed information for each top value
            console.print("\n[yellow]Detailed Value Analysis:[/yellow]")
            for rank, (value, count) in enumerate(sorted_values[:10], 1):
                console.print(f"\n[cyan]#{rank}: {value}[/cyan]")
                console.print(f"  Count: {count} ({(count / total_values) * 100:.1f}%)")
                
                # Show types using this value
                types_with_value = set()
                for item in self.jsonld_db:
                    def find_types_for_value(d):
                        if isinstance(d, dict):
                            if '@type' in d and analysis['property'] in d:
                                if isinstance(d[analysis['property']], (str, int, float, bool)):
                                    if str(d[analysis['property']]) == value:
                                        return {d['@type']} if isinstance(d['@type'], str) else set(d['@type'])
                                elif isinstance(d[analysis['property']], list):
                                    if any(str(x) == value for x in d[analysis['property']] if isinstance(x, (str, int, float, bool))):
                                        return {d['@type']} if isinstance(d['@type'], str) else set(d['@type'])
                            types = set()
                            for v in d.values():
                                if isinstance(v, (dict, list)):
                                    types.update(find_types_for_value(v))
                            return types
                        elif isinstance(d, list):
                            types = set()
                            for item in d:
                                types.update(find_types_for_value(item))
                            return types
                        return set()

                    types_with_value.update(find_types_for_value(item['data']))
                
                if types_with_value:
                    console.print("  Types:")
                    for type_name in sorted(types_with_value):
                        console.print(f"    • {type_name}")
                
                # Show sample URLs (up to 3)
                if value in value_urls and value_urls[value]:
                    console.print("  Sample URLs:")
                    for url in value_urls[value][:3]:
                        console.print(f"    • {url}")

        # Types containing this property
        if analysis['types_containing_property']:
            console.print("\n[yellow]Types Containing Property:[/yellow]")
            for type_name in analysis['types_containing_property']:
                console.print(f"  • {type_name}")

        # Context usage
        if analysis['context_usage']:
            console.print("\n[yellow]Context Usage:[/yellow]")
            for context in analysis['context_usage']:
                console.print(f"  • {context}")

        # Show sample URLs
        if analysis['urls_containing_property']:
            console.print("\n[yellow]Sample URLs containing property (up to 5):[/yellow]")
            for url in analysis['urls_containing_property'][:5]:
                console.print(f"  • {url}")

    def analyze_text(self, url: str | None = None) -> dict:
        """Analyze the text content data."""
        if url:
            data = self._filter_data_by_url(url, db_type='text')  # Specify db_type here
            site_info = f" for {self._normalize_url(url)}"
        else:
            data = self.text_db.all()
            site_info = " across all sites"

        if not data:
            console.print(f"[yellow]No text data found{site_info}[/yellow]")
            return {}

        analysis = {
            'page_stats': {
                'total_pages': len(data),
                'total_words': sum(item.get('word_count', 0) for item in data),
                'avg_words_per_page': 0,
                'pages_with_meta': 0,
                'pages_with_headings': 0
            },
            'heading_stats': {
                'total_headings': 0,
                'by_level': defaultdict(int),
                'common_headings': Counter()
            },
            'content_stats': {
                'avg_paragraphs_per_page': 0,
                'paragraph_length_distribution': defaultdict(int),
                'common_phrases': Counter(),
                'keyword_density': Counter()
            },
            'meta_stats': {
                'pages_with_titles': 0,
                'unique_titles': set(),
                'pages_with_descriptions': 0,
                'avg_description_length': 0
            },
            'temporal_stats': {
                'crawl_dates': Counter(),
                'content_by_date': defaultdict(int)
            }
        }

        # Analyze each page
        for page in data:
            self._analyze_page_content(page, analysis)

        # Calculate averages
        if analysis['page_stats']['total_pages'] > 0:
            analysis['page_stats']['avg_words_per_page'] = (
                analysis['page_stats']['total_words'] / 
                analysis['page_stats']['total_pages']
            )
            analysis['content_stats']['avg_paragraphs_per_page'] = (
                sum(1 for page in data for _ in page.get('paragraphs', [])) / 
                analysis['page_stats']['total_pages']
            )

        self._print_text_analysis(analysis, site_info)
        return analysis

    def _analyze_page_content(self, page: dict, analysis: dict) -> None:
        """Analyze content of a single page."""
        # Title analysis
        if page.get('title'):
            analysis['meta_stats']['pages_with_titles'] += 1
            analysis['meta_stats']['unique_titles'].add(page['title'])

        # Meta description analysis
        if page.get('meta_description'):
            analysis['meta_stats']['pages_with_descriptions'] += 1
            analysis['meta_stats']['avg_description_length'] += len(page['meta_description'].split())

        # Heading analysis
        headings = page.get('headings', [])
        if headings:
            analysis['page_stats']['pages_with_headings'] += 1
            analysis['heading_stats']['total_headings'] += len(headings)
            
            for heading in headings:
                level = heading.get('level', 'unknown')
                text = heading.get('text', '').lower()
                analysis['heading_stats']['by_level'][level] += 1
                analysis['heading_stats']['common_headings'][text] += 1

        # Content analysis
        paragraphs = page.get('paragraphs', [])
        for para in paragraphs:
            words = para.split()
            length = len(words)
            
            # Paragraph length distribution
            if length < 50:
                analysis['content_stats']['paragraph_length_distribution']['very_short'] += 1
            elif length < 100:
                analysis['content_stats']['paragraph_length_distribution']['short'] += 1
            elif length < 200:
                analysis['content_stats']['paragraph_length_distribution']['medium'] += 1
            else:
                analysis['content_stats']['paragraph_length_distribution']['long'] += 1

            # Keyword analysis (simple implementation)
            words = [word.lower() for word in words if len(word) > 3]
            analysis['content_stats']['keyword_density'].update(words)

        # Temporal analysis
        crawl_date = page.get('crawled_at', '')[:10]  # Get just the date part
        if crawl_date:
            analysis['temporal_stats']['crawl_dates'][crawl_date] += 1
            analysis['temporal_stats']['content_by_date'][crawl_date] += page.get('word_count', 0)

    def _print_text_analysis(self, analysis: dict, site_info: str) -> None:
        """Print formatted text analysis results."""
        console.print(f"\n[cyan]Text Content Analysis Report{site_info}[/cyan]")
        console.print("=" * 50)

        # Basic Stats
        console.print("\n[yellow]Page Statistics:[/yellow]")
        stats_table = Table(show_header=True)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green", justify="right")
        
        stats_table.add_row("Total Pages", str(analysis['page_stats']['total_pages']))
        stats_table.add_row("Total Words", str(analysis['page_stats']['total_words']))
        stats_table.add_row("Average Words per Page", f"{analysis['page_stats']['avg_words_per_page']:.1f}")
        stats_table.add_row("Pages with Headings", str(analysis['page_stats']['pages_with_headings']))
        stats_table.add_row("Pages with Meta Description", str(analysis['meta_stats']['pages_with_descriptions']))
        
        console.print(stats_table)

        # Heading Distribution
        if analysis['heading_stats']['by_level']:
            console.print("\n[yellow]Heading Distribution:[/yellow]")
            heading_table = Table(show_header=True)
            heading_table.add_column("Level", style="cyan")
            heading_table.add_column("Count", style="green", justify="right")
            
            for level, count in sorted(analysis['heading_stats']['by_level'].items()):
                heading_table.add_row(level, str(count))
            
            console.print(heading_table)

        # Common Headings
        if analysis['heading_stats']['common_headings']:
            console.print("\n[yellow]Most Common Headings:[/yellow]")
            common_headings_table = Table(show_header=True)
            common_headings_table.add_column("Heading", style="cyan")
            common_headings_table.add_column("Count", style="green", justify="right")
            
            for heading, count in analysis['heading_stats']['common_headings'].most_common(10):
                common_headings_table.add_row(heading[:50], str(count))
            
            console.print(common_headings_table)

        # Paragraph Length Distribution
        if analysis['content_stats']['paragraph_length_distribution']:
            console.print("\n[yellow]Paragraph Length Distribution:[/yellow]")
            para_table = Table(show_header=True)
            para_table.add_column("Length Category", style="cyan")
            para_table.add_column("Count", style="green", justify="right")
            
            for category, count in sorted(analysis['content_stats']['paragraph_length_distribution'].items()):
                para_table.add_row(category, str(count))
            
            console.print(para_table)

        # Top Keywords
        if analysis['content_stats']['keyword_density']:
            console.print("\n[yellow]Top Keywords:[/yellow]")
            keyword_table = Table(show_header=True)
            keyword_table.add_column("Keyword", style="cyan")
            keyword_table.add_column("Occurrences", style="green", justify="right")
            
            for word, count in analysis['content_stats']['keyword_density'].most_common(20):
                keyword_table.add_row(word, str(count))
            
            console.print(keyword_table)

        # Temporal Analysis
        if analysis['temporal_stats']['crawl_dates']:
            console.print("\n[yellow]Content by Date:[/yellow]")
            date_table = Table(show_header=True)
            date_table.add_column("Date", style="cyan")
            date_table.add_column("Pages", style="green", justify="right")
            date_table.add_column("Words", style="blue", justify="right")
            
            for date in sorted(analysis['temporal_stats']['crawl_dates'].keys()):
                date_table.add_row(
                    date,
                    str(analysis['temporal_stats']['crawl_dates'][date]),
                    str(analysis['temporal_stats']['content_by_date'][date])
                )
            
            console.print(date_table)


class ContentGroup:
    def __init__(self, similarity_threshold: int = 85):
        self.groups: list[list[dict]] = []
        self.threshold = similarity_threshold

    def add_content(self, content: dict) -> None:
        """Add content to appropriate group based on fuzzy matching."""
        text = content.get('text', '').lower()
        
        # Try to find a matching group
        for group in self.groups:
            # Compare with first item in group (reference content)
            reference = group[0].get('text', '').lower()
            similarity = fuzz.ratio(text, reference)
            
            if similarity >= self.threshold:
                group.append(content)
                return

        # If no matching group found, create new group
        self.groups.append([content])

def analyze_subdomains_content(self, url: str, similarity_threshold: int = 85) -> dict:
    """Analyze content across subdomains using fuzzy matching for grouping."""
    try:
        from .subdomain import SubdomainEnumerator
        enumerator = SubdomainEnumerator(self.config)
        
        subdomains = enumerator.enumerate_subdomains(url, show_all=False)
        
        analysis = {
            'total_subdomains': len(subdomains),
            'accessible_urls': 0,
            'content_groups': [],
            'redirects': {},
            'json_ld_groups': [],
            'errors': []
        }

        # Initialize content grouping
        content_grouper = ContentGroup(similarity_threshold)
        jsonld_grouper = ContentGroup(similarity_threshold)

        console.print(f"\n[cyan]Analyzing content across subdomains for {url}[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]Analyzing subdomains...", 
                total=len(subdomains)
            )

            for subdomain, ip in subdomains.items():
                try:
                    for protocol in ['https://', 'http://']:
                        try:
                            response = requests.get(
                                f"{protocol}{subdomain}", 
                                headers=self.headers,
                                timeout=self.timeout,
                                allow_redirects=True
                            )
                            
                            # Track redirects
                            if response.history:
                                analysis['redirects'][subdomain] = {
                                    'initial_url': f"{protocol}{subdomain}",
                                    'final_url': response.url,
                                    'redirect_chain': [r.url for r in response.history]
                                }

                            soup = BeautifulSoup(response.text, 'html.parser')
                            
                            # Remove dynamic elements
                            for elem in soup.find_all(['script', 'style', 'meta', 'link']):
                                elem.decompose()
                            
                            # Extract main content
                            content = {
                                'url': response.url,
                                'subdomain': subdomain,
                                'ip': ip,
                                'status_code': response.status_code,
                                'content_length': len(response.text),
                                'title': soup.title.string if soup.title else None,
                                'text': soup.get_text(separator=' ', strip=True)
                            }

                            # Add to content groups
                            content_grouper.add_content(content)

                            # Extract and group JSON-LD
                            jsonld_scripts = soup.find_all('script', type='application/ld+json')
                            if jsonld_scripts:
                                jsonld_data = []
                                for script in jsonld_scripts:
                                    try:
                                        data = json.loads(script.string)
                                        jsonld_data.append(data)
                                    except json.JSONDecodeError:
                                        continue
                                
                                if jsonld_data:
                                    jsonld_content = {
                                        'url': response.url,
                                        'subdomain': subdomain,
                                        'json_ld': jsonld_data,
                                        'text': json.dumps(jsonld_data, sort_keys=True)
                                    }
                                    jsonld_grouper.add_content(jsonld_content)

                            analysis['accessible_urls'] += 1
                            break  # Success, no need to try other protocol
                            
                        except requests.RequestException:
                            continue
                            
                except Exception as e:
                    analysis['errors'].append({
                        'subdomain': subdomain,
                        'error': str(e)
                    })
                
                progress.update(task, advance=1)

        # Store grouped results
        analysis['content_groups'] = content_grouper.groups
        analysis['json_ld_groups'] = jsonld_grouper.groups

        self._print_subdomain_content_analysis(analysis, url)
        return analysis

    except Exception as e:
        console.print(f"[red]Error analyzing subdomain content: {str(e)}[/red]")
        return {}

def _print_subdomain_content_analysis(self, analysis: dict, base_url: str) -> None:
    """Print formatted subdomain content analysis results."""
    console.print(f"\n[cyan]Subdomain Content Analysis Report for {base_url}[/cyan]")
    console.print("=" * 50)

    # Basic Stats
    console.print("\n[yellow]Basic Statistics:[/yellow]")
    console.print(f"Total Subdomains: {analysis['total_subdomains']}")
    console.print(f"Accessible URLs: {analysis['accessible_urls']}")
    console.print(f"Content Groups: {len(analysis['content_groups'])}")
    console.print(f"JSON-LD Groups: {len(analysis['json_ld_groups'])}")

    # Content Groups
    console.print("\n[yellow]Content Groups:[/yellow]")
    for idx, group in enumerate(analysis['content_groups'], 1):
        console.print(f"\n[cyan]Group {idx} ({len(group)} URLs)[/cyan]")
        
        # Calculate average similarity within group
        if len(group) > 1:
            similarities = []
            for url1, url2 in combinations(group, 2):
                similarity = fuzz.ratio(
                    url1.get('text', '').lower(),
                    url2.get('text', '').lower()
                )
                similarities.append(similarity)
            avg_similarity = sum(similarities) / len(similarities)
            console.print(f"Average Similarity: {avg_similarity:.1f}%")

        table = Table(show_header=True)
        table.add_column("URL", style="green")
        table.add_column("Title", style="blue")
        table.add_column("Status", style="yellow", justify="right")
        
        for url_data in group:
            table.add_row(
                url_data['url'],
                str(url_data['title'])[:50] + "..." if url_data['title'] and len(url_data['title']) > 50 else str(url_data['title']),
                str(url_data['status_code'])
            )
        console.print(table)

    # Redirects
    if analysis['redirects']:
        console.print("\n[yellow]Redirects:[/yellow]")
        table = Table(show_header=True)
        table.add_column("Original URL", style="cyan")
        table.add_column("Final URL", style="green")
        table.add_column("Steps", style="yellow", justify="right")
        
        for subdomain, redirect_info in analysis['redirects'].items():
            table.add_row(
                redirect_info['initial_url'],
                redirect_info['final_url'],
                str(len(redirect_info['redirect_chain']))
            )
        console.print(table)

    # JSON-LD Groups
    if analysis['json_ld_groups']:
        console.print("\n[yellow]JSON-LD Groups:[/yellow]")
        for idx, group in enumerate(analysis['json_ld_groups'], 1):
            console.print(f"\n[cyan]JSON-LD Group {idx} ({len(group)} URLs)[/cyan]")
            table = Table(show_header=True)
            table.add_column("URL", style="green")
            table.add_column("Types", style="blue")
            
            for item in group:
                types = set()
                for ld in item['json_ld']:
                    if isinstance(ld, dict) and '@type' in ld:
                        if isinstance(ld['@type'], list):
                            types.update(ld['@type'])
                        else:
                            types.add(ld['@type'])
                
                table.add_row(
                    item['url'],
                    ', '.join(sorted(types)) if types else 'N/A'
                )
            console.print(table)

    # Errors
    if analysis['errors']:
        console.print("\n[yellow]Errors:[/yellow]")
        for error in analysis['errors']:
            console.print(f"[red]{error['subdomain']}: {error['error']}[/red]")
