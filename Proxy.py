import socket
import os
import sys
import re

CACHE_DIR = "cache"
BUFFER_SIZE = 4096
PROXY_HOST = "0.0.0.0"
PROXY_PORT = 8888

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def handle_client(client_socket):
    message_bytes = client_socket.recv(BUFFER_SIZE)
    message = message_bytes.decode('utf-8')
    print('Received request:\n< ' + message)
    
    requestParts = message.split()
    if len(requestParts) < 3:
        client_socket.close()
        return
    
    method = requestParts[0]
    URI = requestParts[1]
    version = requestParts[2]
    print(f'Method:\t\t{method}\nURI:\t\t{URI}\nVersion:\t{version}\n')
    
    URI = re.sub('^(/?)http(s?)://', '', URI, count=1)
    URI = URI.replace('/..', '')
    
    resourceParts = URI.split('/', 1)
    hostname = resourceParts[0]
    resource = '/' + resourceParts[1] if len(resourceParts) == 2 else '/'
    print(f'Requested Resource:\t{resource}')
    
    cacheLocation = os.path.join(CACHE_DIR, hostname + resource.replace('/', '_'))
    if cacheLocation.endswith('/'):
        cacheLocation += 'default'
    print(f'Cache location:\t\t{cacheLocation}')
    
    try:
        if os.path.isfile(cacheLocation):
            with open(cacheLocation, "rb") as cacheFile:
                cacheData = cacheFile.read()
            client_socket.sendall(cacheData)
            print(f'Cache hit! Loading from cache file: {cacheLocation}')
        else:
            originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            address = socket.gethostbyname(hostname)
            originServerSocket.connect((address, 80))
            print(f'Connected to origin server: {hostname}')
            
            request = f'GET {resource} HTTP/1.1\r\nHost: {hostname}\r\nConnection: close\r\n\r\n'
            print('Forwarding request to origin server:')
            print('> ' + request.replace('\r\n', '\n> '))
            
            originServerSocket.sendall(request.encode())
            response = b''
            
            while True:
                data = originServerSocket.recv(BUFFER_SIZE)
                if not data:
                    break
                response += data
            
            client_socket.sendall(response)
            
            cacheDir = os.path.dirname(cacheLocation)
            if not os.path.exists(cacheDir):
                os.makedirs(cacheDir)
            
            with open(cacheLocation, 'wb') as cacheFile:
                cacheFile.write(response)
            
            print('Response cached successfully.')
            originServerSocket.close()
            client_socket.shutdown(socket.SHUT_WR)
            print('Sockets closed successfully.')
    except Exception as e:
        print(f'Error: {e}')
        client_socket.sendall(b'HTTP/1.1 500 Internal Server Error\r\n\r\n')
    finally:
        client_socket.close()

def start_proxy():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind((PROXY_HOST, PROXY_PORT))
    proxy_socket.listen(10)
    print(f'Proxy server running on {PROXY_HOST}:{PROXY_PORT}')
    
    while True:
        client_socket, addr = proxy_socket.accept()
        handle_client(client_socket)

if __name__ == "_main_":
    start_proxy()