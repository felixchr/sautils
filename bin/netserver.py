#!/usr/bin/python

_doc_ = '''
netserver.py - Listen to a port and give response to telnet to this port

Author: Felix Cao(felix.chr@gmail.com)
Usage:
netserver.py -c <port number>

'''

import getopt, sys
import socket
import time

BUFSIZE = 512

def usage():
    print '''Usage: netserver.py [ -s address ] -p <port>
    -h: Print help information
    '''

try:
    opts, args = getopt.getopt(sys.argv[1:], 'hsp:')
except getopt.GetoptError:
    usage()
    sys.exit(2)

now = time.time()

port = 0
server = ""
for o,v in opts:
    if o == '-h':
        usage()
        sys.exit()
    if o == '-p':
        try:
            port = int(v)
        except:
            usage()
            sys.exit(1)
    if o == '-s':
        server = v

if server == "":
    server = socket.gethostbyname(socket.gethostname())
    
if port == 0:
    usage()
    sys.exit(2)
try:
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((server, port))
    s.listen(5)
except Exception, e:
    print e
    print "Bind/Listen failed"
    exit(1)
while True:
    try:
        print "Listen on", server, "port", port,
        print "(Ctrl+C to terminate)"
        print "Waiting for connection..."
        cs, address = s.accept()
        print "Connected from ", address
        cs.send("You are now connected to: " + server + " port " + str(port))
        cs.send(" from " + address[0] + " port " + str(address[1]) + "\n")
        cs.send(">>> ")
        while True:
            data = cs.recv(BUFSIZE)
            if not data:
                break
            input = data.strip('\n').strip('\r').lstrip().rstrip()
            print "Client send: " + input
            if input == "quit":
                cs.close()
                break
            elif input == "shutdown":
                cs.close()
                break
            elif input == "help":
                cs.send("help: print this usage\n")
                cs.send("quit: disconnect this connection\n")
                cs.send("shutdown: shutdown the server\n")
            else:
                cs.send("Your input is " + input + "\n")
            cs.send(">>> ")
        if input == "shutdown":
            break    
    except (EOFError,KeyboardInterrupt,IndexError):
        break
s.close()