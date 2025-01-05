# DomainTools(1)                        General Commands Manual                       DomainTools(1)

## NAME
DomainTools - Web Analysis and Scrapping Tool

## SYNOPSIS
`python DomainTools.py COMMAND [OPTIONS] [ARGUMENTS]`

## DESCRIPTION
A tool for scraping and analyzing web content.

## COMMANDS

### Scraping Commands
**scrape-jsonld** *URL* [OPTIONS]
       Extract JSON-LD structured data from a website

**scrape-text** *URL* [OPTIONS]
       Extract textual content from a website

**scrape-all** *URL* [OPTIONS]
       Extract both JSON-LD and text content

### Analysis Commands
**analyze** [*URL*]
       Analyze collected JSON-LD data

**analyze-text** [*URL*]
       Analyze collected text content

**analyze-property** *PROPERTY* [*URL*]
       Analyze specific JSON-LD property usage

### Enumeration Commands
**enumerate-subdomains** [*URL*] [OPTIONS]
       Enumerate subdomains for a given domain

## OPTIONS

### Scraping Options
**--max-pages** *INTEGER*
       Maximum number of pages to crawl (default: 100)

**--min-delay** *FLOAT*
       Minimum delay between requests in seconds (default: 1.0)

**--max-delay** *FLOAT*
       Maximum delay between requests in seconds (default: 3.0)

### Subdomain Options
**--wordlist** *TEXT*
       Path to custom subdomain wordlist

**--show-all**
       Show all results including unresolved domains

## OUTPUT
All data is stored in the configured data directory (default: ./data)

### JSON-LD Data
Stored in: data/jsonld_data.json
- Original JSON-LD data
- Source URL
- Crawl timestamp
- Response headers

### Text Data
Stored in: data/text_data.json
- Page title
- Meta description
- Headings (h1-h3)
- Main content paragraphs
- Word count
- Crawl timestamp

## CONFIGURATION
Default configuration file: config/default.ini
