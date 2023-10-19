from os import path
import sys
import socket
from collections import defaultdict



default_list_path = path.join(sys.path[0], "sub_list.txt")

def resolve_subs(url: str, sub_list_path = default_list_path) -> dict:
    """ Check for subdomains using the sub_list.txt

    :param url: Base URL to check for subdomains
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
    # TODO Add a WHOIS lookup to get the owner of each IP
    grouped = defaultdict(list)
    for key, val in url_dict.items():
        grouped[val].append(key)

    # Print grouped IP/URLs
    print()
    print(f" {'IP':_^17} {'URL':_^31}")
    for ip, urls in grouped.items():
        print(f"| {ip:<15} | {urls[0]:<29} |")
        for url in urls[1:]:
            print(f"| {' '*15} | {url:<29} |")
    print(f"|{'_'*17}|{'_'*31}|")