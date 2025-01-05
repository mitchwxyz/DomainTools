# Find Subdomains Tool

`python SubDomains.py <base url> [<path to subdomain list>]`


**base url**: Ex. google.com

**subdomain list**: path to subdomain list, Default: ./sub_list.txt

# Next Steps:
### IP ASN Data
`whois -h whois.cymru.com 17.253.144.10` >>> 46606 - returns an AS Network Number
`https://www.peeringdb.com/search/v2?q=46606` - Get AKA Data (hosting providers)

### GeoLocation
https://github.com/ipinfo/python - Has a Free API for Location

