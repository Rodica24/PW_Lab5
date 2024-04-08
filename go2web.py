import sys
import socket
import ssl
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import json
import hashlib
from tinydb import TinyDB, Query

cache_file = "cache.json"
db = TinyDB(cache_file)


def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()


def cache_response(url, response):
    if 'text/html' in response:
        parsed_response = parse_html(response)
    else:
        parsed_response = response

    db.insert({'url': hash_url(url), 'response': parsed_response})


def is_cached(url):
    return db.contains(Query().url == hash_url(url))


def retrieve_cached_response(url):
    result = db.get(Query().url == hash_url(url))
    return result['response']


def print_cached_response(response):
    if isinstance(response, list):
        for item in response:
            print(item)
    elif isinstance(response, str):
        print("Modified JSON Response:")
        try:
            json_data = json.loads(response.split('\r\n\r\n', 1)[1])
            print(json.dumps(json_data, indent=4))  # Print JSON data with indentation
        except json.JSONDecodeError as e:
            print("Error: Unable to parse JSON data:", e)
    else:
        print("Unknown response type")



def extract_url_data(url):
    parsed_url = urlparse(url)

    port = None
    if parsed_url.scheme == "https":
        port = 443
    elif parsed_url.scheme == "http":
        port = 80

    return parsed_url.netloc, port, parsed_url.path


def make_http_request(url):
    if is_cached(url):
        print("Retrieving cached response:", url)
        return retrieve_cached_response(url)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    host, port, path = extract_url_data(url)
    print("Establishing connection:", host, port, path)

    if port == 443:
        client_socket = ssl.wrap_socket(client_socket)

    try:
        client_socket.settimeout(2)
        client_socket.connect((host, port))

        request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\n\r\n"
        client_socket.send(request.encode())

        response = b""
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break

                response += data

            except socket.timeout:
                break

        resp_data = response.decode('utf-8', errors='ignore')
        cache_response(url, resp_data)

        return resp_data

    finally:
        client_socket.close()


def handle_html_or_json(url):
    if is_cached(url):
        print("Retrieving cached response for:", url)
        response = retrieve_cached_response(url)
        print_cached_response(response)
        return response
    else:
        response = make_http_request(url)
        if 'text/html' in response:
            try:
                parsed_response = parse_html(response)
                cache_response(url, parsed_response)
                return parsed_response
            except Exception as e:
                print("Error: Unable to parse HTML data:", e)
        elif 'application/json' in response:
            try:
                json_data = json.loads(response.split('\r\n\r\n', 1)[1])
                print("Modified JSON Response:")
                print(json.dumps(json_data, indent=4))  # Modified JSON output
                return json_data
            except json.JSONDecodeError as e:
                print("Error: Unable to parse JSON data:", e)
        else:
            print(response)

def parse_html(response):
    soup = BeautifulSoup(response, 'html.parser')
    all_elements = soup.find_all(['h1', 'h2', 'h3', 'p'])
    all_info = []

    for element in all_elements:
        if element.name.startswith('h'):
            depth = len(element.name) - 1  # Depth based on heading level
            tag = f"[{element.name}]"
            stars = '*' * (4 - depth)  # Adjusting the number of asterisks
            all_info.append(f"{stars} {tag} {element.get_text()}")  # Customized representation
        elif element.name == 'p':
            tag = f"[{element.name}]"
            all_info.append(f"* {tag} {element.get_text()}")

    links = soup.find_all('a', href=True)
    links_href = [link['href'] for link in links if link['href'].startswith('http')]
    all_info.append("-- Links --")
    all_info += links_href

    return all_info


def search(term):
    search_url = "https://999.md/ro/"
    if is_cached(search_url):
        response = retrieve_cached_response(search_url)
    else:
        print("Retrieving response for", search_url, "...")
        response = handle_html_or_json(search_url)
        cache_response(search_url, response)

    matching_info = [info for info in response if term.lower() in info.lower()]
    if matching_info:
        print("Search results for", term, ":")
        for info in matching_info[:10]:
            print(info)
    else:
        print("No matching results found for", term)


def print_error():
    print("No option provided.")
    print("Usage: ")
    print("python websocket.py -u URL")
    print("python websocket.py -s SEARCH_TERM")
    print("python websocket.py -h")
    sys.exit()


def main():
    args = sys.argv[1:]

    if not args:
        print_error()

    if '-u' in args:
        url_index = args.index('-u') + 1
        if url_index < len(args):
            url = args[url_index]
            response = handle_html_or_json(url)
            print("Information extracted from", url, ":")
            if isinstance(response, list):
                for info in response:
                    print(info)
            elif isinstance(response, dict):
                pass
        else:
            print("Error: No URL provided after -u")
            sys.exit()

    elif '-s' in args:
        search_index = args.index('-s') + 1
        if search_index < len(args):
            term = ' '.join(args[search_index:])
            search(term)
        else:
            print("Error: No search term provided after -s")
            sys.exit()

    elif '-h' in args:
        print("go2web -u <URL>         # make an HTTP request to the specified URL and print the response")
        print("go2web -s <search-term> # make an HTTP request to search the term using your favorite search engine and print top 10 results")
        print("go2web -h               # show this help")


if __name__ == "__main__":
    main()
