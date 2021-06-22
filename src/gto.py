#!/usr/bin/env python3

"""This file communicates with a GTO instance"""

import socket

class GTO:

    def __init__(self, port=55144, addr='localhost'):
        self.port = port
        self.addr = addr
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.addr, self.port))

    def disconnect(self):
        if not self.sock:
            print("Warning: trying to close unopened connection")
        self.sock.close()

    def load_file(self, path: str):
        self.send("Load file: {}".format(path))
        recv = self.receive()
        return recv

    def request_node_data(self):
        return self.send('Request node data')

    def request_pot_stacks(self):
        return self.send('Request pot/stacks')

    def request_current_line(self):
        return self.send('Request current line')

    def take_action(self, action_n):
        return self.send('Take action: {}'.format(action_n))

    def request_action_data():
        return self.send('Request action data')

    def create_message(self, message: str):
        return "~{}~".format(message)

    def receive(self):
        chunks = []
        received = 0
        while True:
            chunk = self.sock.recv(2048)
            received += len(chunk)
            if len(chunk) == 0:
                return b''.join(chunks)
            chunks.append(chunk)


    def send(self, message: str):
        message = self.create_message(message).encode('utf-8')
        total_sent = 0
        while total_sent < len(message):
            sent = self.sock.send(message[total_sent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            total_sent += sent
