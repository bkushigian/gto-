#!/usr/bin/env python3

"""This file communicates with a GTO instance"""

import socket
import time
from pathlib import Path

class GTO:

    def __init__(self, port=55143, addr='localhost'):
        self.port = port
        self.addr = addr
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.addr, self.port))
        self.send("init")
        self.sock.recv(4096)
        resp = self.sock.recv(4096).decode().strip('~')
        return resp

    def disconnect(self):
        if not self.sock:
            print("Warning: trying to close unopened connection")
        self.sock.close()
        self.sock = None

    def load_file(self, path: str):
        self.send("Load file: {}".format(path))
        time.sleep(0.5)
        recv = self.receive().decode().strip('~')
        return recv

    def __parse_player_data(self, player_data_str, actions):
        pos = None
        pd = player_data_str.strip().split('\r\n')
        meta = pd[0].strip().split(', ')
        if len(meta) == 3:
            pos = True

        pd = [line.split() for line in pd[2:]]
        pd_d = {}
        for row in pd:
            hand = row[0]
            row_d = {}
            rowf = [float(x) for x in row[1:]]
            row_d['COMBOS'] = rowf[0]
            row_d['EQUITY'] = rowf[1]
            if pos == True:
                for i, a in enumerate(actions):
                    row_d[a] = {'FREQ': rowf[2+i], 'EV': rowf[2+i+len(actions)]}
            pd_d[hand] = row_d
        return pd_d, pos

    def request_node_data(self):
        '''
        Return a dict representing node date. The dict has keys:
        + `board`: map to a list of board cards, in order
        + `actions`: list of actions performed by the current player
        + `pos`: current player ('ip', or 'oop')
        + `oop`: a dict mapping OOP's hands to that hand's stats (see below)
        + `ip`: a dict mapping IP's hands to that hand's stats (see below)
        >>> s = GTO()
        >>> s.connect()
        'You are connected to GTO+'
        >>> s._load_akq_game()
        >>> nd = s.request_node_data()
        >>> nd['pos']
        'oop'
        >>> nd['actions']
        ['Bet 1', 'Check']
        >>> nd['oop']['KcKh']['COMBOS']
        1.0
        >>> nd['oop']['KcKh']['EQUITY']
        50.0
        >>> nd['oop']['KcKh']['Bet 1']['FREQ']
        0.0
        >>> nd['oop']['KcKh']['Check']['FREQ']
        100.0
        >>> nd['oop']['KcKh']['Check']['EV']
        0.25
        >>> nd['ip']['QcQh']['COMBOS']
        1.0
        >>> nd['ip']['QcQh']['EQUITY']
        0.0
        '''
        self.send('Request node data')
        time.sleep(0.1)
        recv = self.receive().decode().strip('~').strip('[]')
        items = recv.split('][')
        _, board, oop, ip = items

        # Get actions at current node.
        actions = self.request_action_data()

        pos = None                            # The position/player to act next

        # Parse board of form "Board: AsTd3h4d"
        board = board.split()[1].strip()
        board = [ board[i:i+2] for i in range(0, len(board), 2)]

        # Parse oop
        oop, oop_to_act = self.__parse_player_data(oop, actions)
        if oop_to_act:
            pos = 'oop'

        # Parse ip
        ip, ip_to_act = self.__parse_player_data(ip, actions)
        if ip_to_act:
            assert pos is None
            pos = 'ip'
        assert pos is not None
        return {'board': board, 'oop': oop, 'ip': ip, 'pos': pos, 'actions': actions}

    def request_pot_stacks(self):
        self.send('Request pot/stacks')
        time.sleep(0.1)
        recv = self.receive().decode().strip('~')

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
        if recv == 'Hand is at start of tree.':
            return []
        return recv.split(',')

    def take_action(self, action_n):
        self.send('Take action: {}'.format(action_n))
        time.sleep(0.05)
        self.receive().decode().strip('~')

    def request_action_data(self):
        self.send('Request action data')
        time.sleep(0.1)
        recv = self.receive().decode().strip('~')
        recv = recv.strip(']').split(': ')[1].split(',')
        return  recv

    def ask_if_processing(self):
        return self.send('Still processing instruction?')

    def create_message(self, message: str):
        return "~{}~".format(message)

    def receive(self, timeout_sec=1.0):
        chunks = []
        received = 0

        # This loop collects 'chunks' of length 4096 until there is no more to
        # collect (the sent message has been read in its entirety)
        
        while True:
            chunk = self.sock.recv(4096)
            if chunk == b'~Solver still running. Please try again later.~':
                print('still processing...')
                time.sleep(0.5)
                continue
            received += len(chunk)
            chunks.append(chunk)
            if len(chunk) < 4096:
                break

        return b''.join(chunks)


    def send(self, message: str, verbose=False):
        message = self.create_message(message).encode('utf-8')
        total_sent = 0
        if verbose:
            print("Sending payload: \"{}\"".format(message))
        while total_sent < len(message):
            sent = self.sock.send(message[total_sent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            total_sent += sent
    
    def _load_akq_game(self):
        '''
        load a dummy file holding the AKQ game strategy. This is useful for testing
        and for learning the API
        '''
        akq_game = Path(__file__).parent.parent / 'resources' / 'solves' / 'AKQ-Game.gto'


if __name__ == '__main__':
    import doctest
    doctest.testmod()