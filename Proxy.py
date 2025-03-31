import socket
import os
import sys
import re

BUFFER_SIZE = 4096
CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def handle_client(clientSocket):
    # Get HTTP request from client
    message_bytes = clientSocket.recv(BUFFER_SIZE)
    message = message_bytes.decode('utf-8')
    print('Received request:\n< ' + message)
    
    # Extract the method, URI and version of the HTTP client request
    requestParts = message.split()
    if len(requestParts) < 3:
        clientSocket.close()
        return
    
    method, URI, version = requestParts[:3]
    print(f'Method:\t\t{method}\nURI:\t\t{URI}\nVersion:\t{version}\n')
    
    # Get the requested resource from URI
    URI = re.sub('^(/?)http(s?)://', '', URI, count=1)
    URI = URI.replace('/..', '')
    
    # Split hostname from resource name
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
            clientSocket.sendall(cacheData)
            print(f'Cache hit! Loading from cache file: {cacheLocation}')
        else:
            # Create a socket to connect to origin server
            originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            address = socket.gethostbyname(hostname)
            originServerSocket.connect((address, 80))
            print(f'Connected to origin server: {hostname}')
            
            # Create request for origin server
            request = f'GET {resource} HTTP/1.1\r\nHost: {hostname}\r\nConnection: close\r\n\r\n'
            print('Forwarding request to origin server:')
            print('> ' + request.replace('\r\n', '\n> '))
            
            try:
                originServerSocket.sendall(request.encode())
            except socket.error:
                print('Forward request to origin failed')
                sys.exit()
            print('Request sent to origin server\n')
            
            # Get the response from the origin server
            response = b''
            while True:
                data = originServerSocket.recv(BUFFER_SIZE)
                if not data:
                    break
                response += data
            
            # Send the response to the client
            clientSocket.sendall(response)
            
            # Save origin server response in the cache file
            cacheDir = os.path.dirname(cacheLocation)
            if not os.path.exists(cacheDir):
                os.makedirs(cacheDir)
            
            with open(cacheLocation, 'wb') as cacheFile:
                cacheFile.write(response)
            
            print('Response cached successfully.')
            originServerSocket.close()
            clientSocket.shutdown(socket.SHUT_WR)
            print('Sockets closed successfully.')
    except Exception as e:
        print(f'Error: {e}')
        clientSocket.sendall(b'HTTP/1.1 500 Internal Server Error\r\n\r\n')
    finally:
        clientSocket.close()

def start_proxy():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind(("0.0.0.0", 8888))
    proxy_socket.listen(10)
    print('Proxy server running on 0.0.0.0:8888')
    
    while True:
        client_socket, addr = proxy_socket.accept()
        handle_client(client_socket)

if __name__ == "_main_":
    start_proxy()
