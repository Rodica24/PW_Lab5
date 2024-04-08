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
    db.insert({'url': hash_url(url), 'response': response})


def is_cached(url):
    return db.contains(Query().url == hash_url(url))


def retrieve_cached_response(url):
    result = db.get(Query().url == hash_url(url))
    return result['response']


def print_cached_response(response):
    print("Response:")
    print(response)


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


def main():
    args = sys.argv[1:]

    if '-h' in args:
        print("Usage: ")
        print("python go2web.py -u URL")
        sys.exit()

    if '-u' in args:
        url_index = args.index('-u') + 1
        if url_index < len(args):
            url = args[url_index]
            response = make_http_request(url)
            print("Response from", url, ":")
            print_cached_response(response)
        else:
            print("Error: No URL provided after -u")
            sys.exit()


if __name__ == "__main__":
    main()
