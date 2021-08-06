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
        time.sleep(0.5)
        recv = self.receive().decode()
        return recv

    def request_node_data(self):
        self.send('Request node data')
        time.sleep(0.5)
        recv = self.receive().decode().strip('~').strip('[]')
        items = recv.split('][')
        _, board, oop, ip = items

        return {'board': board, 'oop': oop, 'ip': ip}

    def request_pot_stacks(self):
        self.send('Request pot/stacks')
        time.sleep(0.1)
        recv = self.receive().decode().strip('~')
        print(recv)

        # Skip Header
        idx = recv.index(']')
        recv = recv[idx+1:]

        # Pot
        idx = recv.index(']')
        pot  = float(recv[6:idx])
        recv = recv[idx+1:]

        # OOP Stack
        idx = recv.index(']')
        oop_stack  = float(recv[12:idx])
        recv = recv[idx+1:]
        
        # OOP Stack
        idx = recv.index(']')
        ip_stack  = float(recv[11:idx])

        return {'pot': pot, 'oop_stack': oop_stack, 'ip_stack': ip_stack}

    def request_current_line(self):
        self.send('Request current line')
        time.sleep(0.05)
        recv = self.receive().decode().strip('~')
        if recv == 'Hand is at  start of tree.':
            return []
        return recv.split(',')

    def take_action(self, action_n):
        return self.send('Take action: {}'.format(action_n))

    def request_action_data(self):
        self.send('Request action data')
        time.sleep(0.1)
        recv = self.receive().decode().strip('~')
        recv = recv.strip(']').split(': ')[1].split(',')
        print(recv)
        return  recv

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
