#!/usr/bin/env python3

"""This file communicates with a GTO instance"""

import socket
import time

class GTO:

    def __init__(self, port=55143, addr='localhost'):
        self.port = port
        self.addr = addr
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.addr, self.port))
        self.send("init")
        self.sock.recv(5096)
        resp = self.sock.recv(5096)
        print(resp)

    def disconnect(self):
        if not self.sock:
            print("Warning: trying to close unopened connection")
        self.sock.close()

    def load_file(self, path: str):
        self.send("Load file: {}".format(path))
        # recv = self.receive()
        # return recv

    def request_node_data(self):
        return self.send('Request node data')

    def request_pot_stacks(self):
        return self.send('Request pot/stacks')

    def request_current_line(self):
        return self.send('Request current line')

    def take_action(self, action_n):
        return self.send('Take action: {}'.format(action_n))

    def request_action_data(self):
        return self.send('Request action data')

    def ask_if_processing(self):
        return self.send('Still processing instruction?')

    def create_message(self, message: str):
        return "~{}~".format(message)

    def receive(self, timeout_ms=1000):
        now = time.time()
        chunks = []
        received = 0
        while True:
            chunk = self.sock.recv(5096)
            if chunk == b'~Solver still running. Please try again later.~':
                print('still processing...', time.time() - now)
                if time.time() - now > timeout_ms:
                    raise TimeoutError()
                time.sleep(2.0)
                continue
            received += len(chunk)
            chunks.append(chunk)
            if len(chunk) < 5096:
                return b''.join(chunks)


    def send(self, message: str):
        message = self.create_message(message).encode('utf-8')
        total_sent = 0
        print("Sending payload: \"{}\"".format(message))
        while total_sent < len(message):
            sent = self.sock.send(message[total_sent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            total_sent += sent


def test():
    g = GTO()
    g.connect()
    g.load_file(r"C:\Users\bkush\Documents\GTO+\Kd3s2c-7-6-2021.gto")
    print(g.receive())
    g.request_node_data()
    print(g.receive())
    g.request_action_data()
    print(g.receive())

    g.request_current_line()
    print(g.receive())

if __name__ == '__main__':
    test()