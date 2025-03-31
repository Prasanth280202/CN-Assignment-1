import socket
import sys
import os
import argparse
import re

size = 1000000

parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='the IP Address Of Proxy Server')
parser.add_argument('port', type=int, help='the port number of the proxy server')
arg = parser.parse_args()
proxyHost = arg.hostname
proxyPort = arg.port

try:
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print('Created socket')
except socket.error as e:
    print(f'Failed to create socket: {e}')
    sys.exit()

try:
    serverSocket.bind((proxyHost, proxyPort))
    print('Port is bound')
except socket.error as e:
    print(f'Port is already in use: {e}')
    sys.exit()

serverSocket.listen(5)
print('Listening to socket')

def handle_client(clientSocket):
    try:
        message_bytes = clientSocket.recv(size)
        message = message_bytes.decode('utf-8')
        print(f'Received request:\n< {message}')
    except socket.error as e:
        print(f'Error receiving data: {e}')
        clientSocket.close()
        return

    requestParts = message.split() 
    if len(requestParts) < 3:
        print('Invalid request received')
        clientSocket.close()
        return
    
    method, URI, version = requestParts[:3]
    print(f'Method: {method}\nURI: {URI}\nVersion: {version}\n')
    
    URI = re.sub('^(/?)http(s?)://', '', URI, count=1)
    URI = URI.replace('/..', '')
    
    resourceParts = URI.split('/', 1)
    hostname = resourceParts[0]
    resource = '/' + resourceParts[1] if len(resourceParts) == 2 else '/'
    
    print(f'Requested Resource: {resource}')
    
    cacheLocation = f'./cache/{hostname}{resource}'
    if cacheLocation.endswith('/'):
        cacheLocation += 'default'
    
    print(f'Cache location: {cacheLocation}')
    
    if os.path.isfile(cacheLocation):
        try:
            with open(cacheLocation, 'rb') as cacheFile:
                cacheData = cacheFile.read()
                clientSocket.sendall(cacheData)
                print(f'Cache hit! Sent {cacheLocation} to client.')
                clientSocket.close()
                return
        except Exception as e:
            print(f'Error reading cache: {e}')
    
    try:
        originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        address = socket.gethostbyname(hostname)
        originServerSocket.connect((address, 80))
        print(f'Connected to {hostname}')
    except socket.error as e:
        print(f'Connection to origin server failed: {e}')
        clientSocket.close()
        return
    
    request = f'{method} {resource} HTTP/1.0\r\nHost: {hostname}\r\nConnection: close\r\n\r\n'
    try:
        originServerSocket.sendall(request.encode())
        print('Request sent to origin server')
    except socket.error as e:
        print(f'Error sending request: {e}')
        clientSocket.close()
        return
    
    try:
        response = b''
        while True:
            data = originServerSocket.recv(size)
            if not data:
                break
            response += data
        
        clientSocket.sendall(response)
        print('Response sent to client')
        
        os.makedirs(os.path.dirname(cacheLocation), exist_ok=True)
        with open(cacheLocation, 'wb') as cacheFile:
            cacheFile.write(response)
            print('Response cached')
    except socket.error as e:
        print(f'Error handling response: {e}')
    
    originServerSocket.close()
    clientSocket.close()
    print('Connections closed')

while True:
    print('Waiting for connection...')
    try:
        clientSocket, clientAddress = serverSocket.accept()
        print('Received a connection')
        handle_client(clientSocket)
    except socket.error as e:
        print(f'Failed to accept connection: {e}')
        sys.exit()
