#!/usr/bin/env python3

import socket

def run():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("connecting...")
    s.connect(('localhost', 55143))
    print("connected! sending...")
    s.send('~test~'.encode('utf-8'))
    print("sent! receiving...")
    return s.recv(0)

def test():
    '''
    This test asserts 
    '''
    try:
        recv = run()
        assert recv, "Failed: no connection message"
        print("Passed: no connection message")
        print("Message: " + recv.decode('utf-8'))
    except Exception as e:
        print("Failed")
        print(e)

test()