import socket
import os
import sys
import re
import argparse

BUFFER_SIZE = 4096
CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def handle_client(client_socket, proxy_host=None, proxy_port=None):
    message_bytes = client_socket.recv(BUFFER_SIZE)
    message = message_bytes.decode('utf-8')
    print('Received request:\n< ' + message)
    
    request_parts = message.split()
    if len(request_parts) < 3:
        client_socket.close()
        return
    
    method, URI, version = request_parts[:3]
    print(f'Method:\t\t{method}\nURI:\t\t{URI}\nVersion:\t{version}\n')
    
    URI = re.sub('^(/?)http(s?)://', '', URI, count=1)
    URI = URI.replace('/..', '')
    
    resource_parts = URI.split('/', 1)
    hostname = resource_parts[0]
    resource = '/' + resource_parts[1] if len(resource_parts) == 2 else '/'
    print(f'Requested Resource:\t{resource}')
    
    cache_location = os.path.join(CACHE_DIR, hostname + resource.replace('/', '_'))
    if cache_location.endswith('/'):
        cache_location += 'default'
    print(f'Cache location:\t\t{cache_location}')
    
    try:
        if os.path.isfile(cache_location):
            with open(cache_location, "rb") as cache_file:
                cache_data = cache_file.read()
            client_socket.sendall(cache_data)
            print(f'Cache hit! Loading from cache file: {cache_location}')
        else:
            origin_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            if proxy_host and proxy_port:
                print(f'Connecting through proxy: {proxy_host}:{proxy_port}')
                origin_server_socket.connect((proxy_host, proxy_port))
                request = f'{method} http://{hostname}{resource} HTTP/1.1\r\nHost: {hostname}\r\nConnection: close\r\n\r\n'
            else:
                address = socket.gethostbyname(hostname)
                origin_server_socket.connect((address, 80))
                request = f'{method} {resource} HTTP/1.1\r\nHost: {hostname}\r\nConnection: close\r\n\r\n'
            
            print('Forwarding request:')
            print('> ' + request.replace('\r\n', '\n> '))
            
            origin_server_socket.sendall(request.encode())
            print('Request sent to origin server\n')
            
            response = b''
            while True:
                data = origin_server_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                response += data
            
            client_socket.sendall(response)
            
            cache_dir = os.path.dirname(cache_location)
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            
            with open(cache_location, 'wb') as cache_file:
                cache_file.write(response)
            
            print('Response cached successfully.')
            origin_server_socket.close()
            client_socket.shutdown(socket.SHUT_WR)
            print('Sockets closed successfully.')
    except Exception as e:
        print(f'Error: {e}')
        client_socket.sendall(b'HTTP/1.1 500 Internal Server Error\r\n\r\n')
    finally:
        client_socket.close()

def start_proxy(proxy_host=None, proxy_port=None):
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind(("0.0.0.0", 8888))
    proxy_socket.listen(10)
    print('Proxy server running on 0.0.0.0:8888')
    
    while True:
        client_socket, addr = proxy_socket.accept()
        handle_client(client_socket, proxy_host, proxy_port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--proxy_host', type=str, help='Upstream proxy hostname', default=None)
    parser.add_argument('--proxy_port', type=int, help='Upstream proxy port', default=None)
    args = parser.parse_args()
    
    start_proxy(args.proxy_host, args.proxy_port)
