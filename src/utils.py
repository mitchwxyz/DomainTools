from urllib.parse import urlparse


def is_valid_url(url: str, base_domain: str) -> bool:
    """Validate if URL should be crawled"""
    parsed_url = urlparse(url)
    return (
        parsed_url.netloc == base_domain
        and parsed_url.scheme in ('http', 'https')
        and not parsed_url.path.endswith(('.jpg', '.png', '.pdf'))
    )

def clean_text(text: str) -> str:
    """Clean and normalize text content"""
    return ' '.join(text.split())