import http.client
import socketserver
import os
import hashlib
from http.server import BaseHTTPRequestHandler

CACHE_DIR = "cache"
BUFFER_SIZE = 4096
PROXY_HOST = "0.0.0.0"
PROXY_PORT = 8888

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_filename(url):
    return os.path.join(CACHE_DIR, hashlib.md5(url.encode()).hexdigest())

class ProxyRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = self.path
        cache_file = get_cache_filename(url)

        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                cached_response = f.read()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(cached_response)
            print(f"Served from cache: {url}")
        else:
            try:
                host = url.split("/")[2]
                conn = http.client.HTTPConnection(host)
                conn.request("GET", url)
                response = conn.getresponse()
                data = response.read()
                
                with open(cache_file, "wb") as f:
                    f.write(data)
                
                self.send_response(response.status)
                self.send_header("Content-Type", response.getheader("Content-Type"))
                self.end_headers()
                self.wfile.write(data)
                print(f"Fetched from server and cached: {url}")
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Internal Server Error")

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

def start_proxy():
    with ThreadedTCPServer((PROXY_HOST, PROXY_PORT), ProxyRequestHandler) as server:
        print(f"Proxy server running on {PROXY_HOST}:{PROXY_PORT}")
        server.serve_forever()

if __name__ == "_main_":
    start_proxy()