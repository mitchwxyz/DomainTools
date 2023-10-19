from os import path
import sys
import socket
from collections import defaultdict



default_list_path = path.join(sys.path[0], "sub_list.txt")

def resolve_subs(url: str, sub_list_path = default_list_path) -> dict:
    """ Check for subdomains using the sub_list.txt

    :param url: Base URL to check for subdomains
    :param sub_list_path: (optional) Alternate sub-domain name list
    """
    # Load subdomain list
    with open(sub_list_path, 'r') as f:
        subdomains = f.read().splitlines()

    # Loop through subdomain list
    results = {}
    for sub in subdomains:
        full_url = f"{sub}.{url}"
        try:
            ip_address = socket.gethostbyname(full_url)
        except socket.error:
            ip_address = "Could Not Resolve"

        # Print each
        print(f"{full_url:<32} | {ip_address}")
       
        if ip_address != "Could Not Resolve":
            results[full_url] = ip_address

    return results

# TODO Create a WHOIS lookup function
def ip_owner(ip: str) -> str:
    pass


if __name__ == "__main__":

    # open subdomain list
    try:
        lookup_url = sys.argv[1]
        socket.gethostbyname(lookup_url)
    except:
        print("Enter a valid URL as an argument")

    # Resolve subdomains and print to screen
    if len(sys.argv) > 2:
        url_dict = resolve_subs(lookup_url, sys.argv[2])
    else:
        url_dict = resolve_subs(lookup_url)

    # Build a dictionary of urls by IP
    # TODO Add a WHOIS lookup for each IP
    grouped = defaultdict(list)
    for key, val in url_dict.items():
        grouped[val].append(key)

    # Print grouped IP/URLs
    print()
    ip_width = max(len(x) for x in grouped.keys()) + 1
    url_width = max(len(x) for x in url_dict.keys()) + 1

    print(f" {'IP'.center(ip_width+1, '_')} {'URL'.center(url_width + 1, '_')}")
    for ip, urls in grouped.items():
        print(f"| {ip.ljust(ip_width, ' ')}| {urls[0].ljust(url_width, ' ')}|")
        for url in urls[1:]:
            print(f"|{' '*ip_width} | {url.ljust(url_width, ' ')}|")
    print(f"|{'_'*int(ip_width+1)}|{'_'*int(url_width+1)}|")