#!/usr/bin/env python3

"""This file communicates with a GTO instance"""

import socket
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from xmlrpc.client import Boolean


class GTO:
    def __init__(self, port: int = 55143, addr: str = "localhost"):
        self.port: int = port
        self.addr: str = addr
        self.sock: Optional[socket.socket] = None

    def connect(self) -> str:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.addr, self.port))
        self.send("init")
        self.sock.recv(4096)
        resp = self.sock.recv(4096).decode().strip("~")
        return resp

    def disconnect(self) -> None:
        if not self.sock:
            print("Warning: trying to close unopened connection")
        self.sock.close()
        self.sock = None

    def load_file(self, path: str) -> str:
        self.send("Load file: {}".format(path))
        time.sleep(0.5)
        recv = self.receive().decode().strip("~")
        return recv

    def __parse_player_data(
        self, player_data_str: str, actions
    ) -> Tuple[Dict[str, Dict[str, Union[float, Dict[str, float]]]], Boolean]:
        """
        Parse player data string. For isntance, OOP's root node in the AKQ game is represented by:

            player_data_str: OOP, 6 hands, 2 actions
            HAND, COMBOS, EQUITY, WEIGHT1, WEIGHT2, EV1, EV2
            KcKh 1.0000 50.000 0 100.000 0 0.250
            KdKh 1.0000 50.000 0 100.000 0 0.250
            KsKh 1.0000 50.000 0 100.000 0 0.250
            KdKc 1.0000 50.000 0 100.000 0 0.250
            KsKc 1.0000 50.000 0 100.000 0 0.250
            KsKd 1.0000 50.000 0 100.000 0 0.250

        Action names are not specified here, so `actions` specifies the names
        of the actions taken (e.g., `"Call"`, `"Raise 2.5"`, `"Raise 7.5"`,
        etc). These should be given by `request_node_data()`.
        """
        # player_data: a row of `str` with each entry representing a single row
        # in a table.
        #
        # + The first row is some meta information: e.g.:
        #       'IP, 12 hands, 2 actions'
        #
        # + The next row is a _comma separated header_ for the table: e.g.:
        #
        #       'HAND, COMBOS, EQUITY, WEIGHT1, WEIGHT2, EV1, EV2'
        #
        #   Note that there are two actions, two weights, and two EVs.
        #
        # + Each successive row is a _space separated data row_: e.g.:
        #       'KcKh 1.0000 50.000 0 100.000 0 0.250'

        player_data: List[str] = player_data_str.strip().split("\r\n")
        meta = player_data[0].strip().split(", ")

        # To determine if this data is active player data or not we can look at
        # `meta` to see if there are any actions for this player at this node.
        # If so, `meta` will have length 3. Otherwise it will have length 2.
        if len(meta) == 3:
            player_data_is_for_active_player = True
        elif len(meta) == 2:
            player_data_is_for_active_player = False
        else:
            raise RuntimeError(
                f"Illegal state: meta string from node data must have length 2 or 3, but got {meta}"
            )

        player_data_dict = {}

        # Iterate over the hand data in player_data. Each hand_data row
        # results in a `hand_dict` of the form:
        #    {"COMBOS": NUM_COMBS,
        #     "EQUITY": HAND_EQUITY,
        #     "Check": {"FREQ": CHECK_FREQ, "EV": CHECK_EV},
        #     "Bet 2.5": {"FREQ": BET_2.5_FREQ, "EV": BET_2.5_EV},
        #     "Bet 10.5": {"FREQ": BET_10.5_FREQ, "EV": BET_10.5_EV}}
        for hand_data in [line.split() for line in player_data[2:]]:
            hand = hand_data[0]
            hand_dict: Dict[str, Any] = {}
            # represent numeric values as floats
            row_floats = [float(x) for x in hand_data[1:]]
            hand_dict["COMBOS"] = row_floats[0]
            hand_dict["EQUITY"] = row_floats[1]
            if player_data_is_for_active_player:
                # Map each action string to its frequency and ev stats
                for index, action in enumerate(actions):
                    hand_dict[action] = {
                        "FREQ": row_floats[2 + index],
                        "EV": row_floats[2 + index + len(actions)],
                    }
            player_data_dict[hand] = hand_dict
        return player_data_dict, player_data_is_for_active_player

    def request_node_data(self):
        """
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
        """
        self.send("Request node data")
        time.sleep(0.1)
        recv = self.receive().decode().strip("~").strip("[]")
        items = recv.split("][")
        _, board, oop, ip = items

        # Get actions at current node.
        actions = self.request_action_data()

        pos = None  # The position/player to act next

        # Parse board of form "Board: AsTd3h4d"
        board = board.split()[1].strip()
        board = [board[i : i + 2] for i in range(0, len(board), 2)]

        # Parse oop
        oop, oop_to_act = self.__parse_player_data(oop, actions)
        if oop_to_act:
            pos = "oop"

        # Parse ip
        ip, ip_to_act = self.__parse_player_data(ip, actions)
        if ip_to_act:
            assert pos is None
            pos = "ip"
        assert pos is not None
        return {"board": board, "oop": oop, "ip": ip, "pos": pos, "actions": actions}

    def request_pot_stacks(self):
        self.send("Request pot/stacks")
        time.sleep(0.1)
        recv = self.receive().decode().strip("~")

        # Skip Header
        idx = recv.index("]")
        recv = recv[idx + 1 :]

        # Pot
        idx = recv.index("]")
        pot = float(recv[6:idx])
        recv = recv[idx + 1 :]

        # OOP Stack
        idx = recv.index("]")
        oop_stack = float(recv[12:idx])
        recv = recv[idx + 1 :]

        # OOP Stack
        idx = recv.index("]")
        ip_stack = float(recv[11:idx])

        return {"pot": pot, "oop_stack": oop_stack, "ip_stack": ip_stack}

    def request_current_line(self) -> List[str]:
        self.send("Request current line")
        time.sleep(0.05)
        recv = self.receive().decode().strip("~")
        if recv == "Hand is at start of tree.":
            return []
        return recv.split(",")

    def take_action(self, action_n: int) -> None:
        self.send("Take action: {}".format(action_n))
        time.sleep(0.05)
        self.receive().decode().strip("~")

    def request_action_data(self) -> List[str]:
        self.send("Request action data")
        time.sleep(0.1)
        recv = self.receive().decode().strip("~")
        recv = recv.strip("]").split(": ")[1].split(",")
        return recv

    def ask_if_processing(self):
        return self.send("Still processing instruction?")

    def create_message(self, message: str) -> str:
        return "~{}~".format(message)

    def receive(self) -> bytes:
        chunks = []

        # This loop collects 'chunks' of length 4096 until there is no more to
        # collect (the sent message has been read in its entirety)

        while True:
            chunk = self.sock.recv(4096)
            if chunk == b"~Solver still running. Please try again later.~":
                print("still processing...")
                time.sleep(0.5)
                continue
            chunks.append(chunk)
            if len(chunk) < 4096:
                break

        return b"".join(chunks)

    def send(self, message: str, verbose=False) -> None:
        message = self.create_message(message).encode("utf-8")
        total_sent = 0
        if verbose:
            print('Sending payload: "{!r}"'.format(message))
        while total_sent < len(message):
            sent = self.sock.send(message[total_sent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            total_sent += sent

    def _load_akq_game(self) -> None:
        """
        load a dummy file holding the AKQ game strategy. This is useful for testing
        and for learning the API
        """
        akq_game = (
            Path(__file__).parent.parent / "resources" / "solves" / "AKQ-Game.gto"
        )
        self.load_file(str(akq_game))


if __name__ == "__main__":
    import doctest

    doctest.testmod()
