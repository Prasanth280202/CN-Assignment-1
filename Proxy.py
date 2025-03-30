import socket
import threading
import os
import hashlib

CACHE_DIR = "cache"
BUFFER_SIZE = 4096
PROXY_HOST = "0.0.0.0"
PROXY_PORT = 8888

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_filename(url):
    return os.path.join(CACHE_DIR, hashlib.md5(url.encode()).hexdigest())

def handle_client(client_socket):
    request = client_socket.recv(BUFFER_SIZE).decode()
    
    if not request:
        client_socket.close()
        return
    
    request_lines = request.split("\r\n")
    first_line = request_lines[0].split()
    if len(first_line) < 2:
        client_socket.close()
        return
    
    method, url = first_line[0], first_line[1]
    
    if method != "GET":
        client_socket.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
        client_socket.close()
        return
    
    cache_file = get_cache_filename(url)
    
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            cached_response = f.read()
        client_socket.sendall(cached_response)
        print(f"Served from cache: {url}")
    else:
        try:
            host = url.split("/")[2]
            server_socket = socket.create_connection((host, 80))
            server_socket.sendall(request.encode())
            
            response = b""
            while True:
                data = server_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                response += data
            with open(cache_file, "wb") as f:
                f.write(response)
            
            client_socket.sendall(response)
            print(f"Fetched from server and cached: {url}")
            server_socket.close()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            client_socket.sendall(b"HTTP/1.1 500 Internal Server Error\r\n\r\n")
    
    client_socket.close()

def start_proxy():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind((PROXY_HOST, PROXY_PORT))
    proxy_socket.listen(10)
    print(f"Proxy server running on {PROXY_HOST}:{PROXY_PORT}")
    
    while True:
        client_socket, addr = proxy_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,)).start()

if __name__ == "_main_":
    start_proxy()