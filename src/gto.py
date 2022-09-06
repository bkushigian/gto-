#!/usr/bin/env python3

import socket
import time
from pathlib import Path


class GTO:
    def __init__(self, port=55143, addr="localhost", verbose=False):
        self._port = port
        self._addr = addr
        self._sock = None
        self._verbose = verbose

        # Messages to GTO+ are blocked into 4096 byte chunks
        self._block_len = 4096

        # GTO+ has fragile interrupt handling. We sleep at these points in attempt
        # to keep GTO+ running. Note this value may be dependent on your machine
        # (i.e., this value is sensitive to your box's performance with respect to
        # its hardware and current load).
        self._sleep_time_sec = 0.5

        # TODO: Maybe add big sleep, little sleep. Sometimes we can just nap.

    """
    Opens a connection to GTO+ using the settings provided in the constructor.
    If GTO+ does not confirm a successful connection, this method raises an
    exception.
    """

    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self._addr, self._port))

        self._send("init")
        self._sock.recv(self._block_len)

        response = self._sock.recv(self._block_len).decode().strip("~")

        if self._verbose:
            print(f"Connection result: {response}")

        if response != "You are connected to GTO+":
            raise RuntimeError("Unable to connect to GTO+")

        return response

    """
    Closes a connection to GTO+.
    """

    def disconnect(self):
        if not self._sock:
            return

        self._sock.close()
        self._sock = None

    """
    Loads a saved solve file
    """

    def load_file(self, path: str):
        self._send("Load file: {}".format(path))
        time.sleep(self._sleep_time_sec)
        response = self._receive().decode().strip("~")

        return response

    """
    Requests node data containing information about the board, player to act, each
    player's actions, and each player's holdings.
    """

    def request_node_data(self):
        board, oop, ip = self._get_node_data()
        actions = self._get_action_data()

        oop, is_oop_to_act = self._parse_player_data(oop, actions)
        ip, is_ip_to_act = self._parse_player_data(ip, actions)

        if is_ip_to_act == is_oop_to_act:
            raise RuntimeError("IP and OOP can't both be next to act")

        next_to_act = "ip" if is_ip_to_act else "oop"

        return {
            "board": board,
            "next_to_act": next_to_act,
            "oop": oop,
            "ip": ip,
            "actions": actions,
        }

    """
    Private method that parses the response to a request for node data. Returns a tuple
    containing raw text of the board, IP, and OOP data.
    """

    def _get_node_data(self):
        self._send("Request node data")

        time.sleep(self._sleep_time_sec)

        response = self._receive().decode()

        # The response format is roughly as follows (note that XX, YY, and ZZ are
        # dealt with later):
        #
        # "~[GTO+ export][Board: XX][OOP, YY][IP, ZZ]~"
        #
        # Strip the response of '~' and starting and ending brackets. This makes
        # splitting easier later. We're left with a format as follows:
        #
        # "GTO+ export][Board: XX][OOP, YY][IP, ZZ"
        result = response.strip("~").strip("[]")

        # Split the raw board, OOP, and IP data. Each will require further parsing.
        # Drop "GTO+ export". We should have:
        #
        # board="Board: XX"
        # oop="OOP, YY"
        # ip="IP, ZZ"
        result = result.split("][")
        _, board, oop, ip = result

        # Drop "Board:" so we're left with something of the form "AsTd3h"
        board = board.split()[1].strip()

        return (board, oop, ip)

    """
    Private method that parses the response to a request for action data
    """

    def _get_action_data(self):
        self._send("Request action data")

        time.sleep(self._sleep_time_sec)

        # The response has the following format:
        #
        # ~[n actions: X1,X2, ... Xn]~
        response = self._receive().decode().strip("~")

        # Drop the brackets and "n actions:" and collect each action's name in a list.
        # For example: ['Bet 1', 'Check']
        result = response.strip("]").split(": ")[1].split(",")

        return result

    """
    Private method that parses player data at a node. Returns a dictionary of the
    following form:

    {
        'KcKh': {
            'COMBOS': 1.0,
            'EQUITY': 50.0,
            'Bet 1': {'FREQ': 0.0, 'EV': 0.0},
            'Check': {'FREQ' 100.0, 'EV': 0.25}
        }
    }

    Note that if the player is not next to act then there will not be any actions
    (i.e., 'Bet 1' and 'Check').

    GTO+ seems to return these data per combo.
    """

    def _parse_player_data(self, raw_player_data, actions):
        raw_player_data = raw_player_data.strip().split("\r\n")

        # Metadata are IP/OOP, number of combos, and number of available actions.
        # The available actions are only present when the player is next to act
        # (in this node). If the player is not next to act, there are only two
        # elements in the list.
        metadata = raw_player_data[0].strip().split(", ")
        is_next_to_act = True if len(metadata) == 3 else False

        # The first item in the raw response are the metadata. The second item is a
        # comma-separated list of column names. If the player is not next to act, it
        # contains 'HANDS, COMBOS, EQUITY'. When the player is next to act there are
        # additional columns for the frequency of each action. For example, when the
        # player can bet or fold these will be 'WEIGHT1, WEIGHT2, EV1, EV2'. The weights
        # are the frequencies.
        raw_player_data = [line.split() for line in raw_player_data[2:]]

        player_data = {}

        for row in raw_player_data:
            hand_details = {}

            # Below is a reference of the possible column names and a row with example
            # values.
            #
            # 'HAND, COMBOS, EQUITY, WEIGHT1, WEIGHT2, EV1, EV2'
            # 'KcKh  1.0000  50.000  0        100.000  0    0.250'
            row_values = [float(x) for x in row[1:]]

            hand = row[0]

            hand_details["COMBOS"] = row_values[0]
            hand_details["EQUITY"] = row_values[1]

            # The player to act also has an EV and frequency
            if is_next_to_act:
                for i, action in enumerate(actions):
                    hand_details[action] = {
                        "FREQ": row_values[2 + i],
                        "EV": row_values[2 + i + len(actions)],
                    }

            player_data[hand] = hand_details

        return player_data, is_next_to_act

    """
    TODO
    """

    def request_pot_stacks(self):
        self._send("Request pot/stacks")

        time.sleep(self._sleep_time_sec)

        response = self._receive().decode().strip("~")

        print(f"response={response}")

        # Skip the header
        idx = response.index("]")
        response = response[idx + 1 :]

        # Pot
        idx = response.index("]")
        pot = float(response[6:idx])
        response = response[idx + 1 :]

        # OOP stack
        idx = response.index("]")
        oop_stack = float(response[12:idx])
        response = response[idx + 1 :]

        # OOP stack
        idx = response.index("]")
        ip_stack = float(response[11:idx])

        return {"pot": pot, "oop_stack": oop_stack, "ip_stack": ip_stack}

    """
    TODO
    """

    def request_current_line(self):
        self._send("Request current line")
        time.sleep(self._sleep_time_sec)
        response = self._receive().decode().strip("~")

        if response == "Hand is at start of tree.":
            return []

        return response.split(",")

    """
    TODO
    """

    def take_action(self, action_n):
        self._send("Take action: {}".format(action_n))
        time.sleep(self._sleep_time_sec)
        self._receive().decode().strip("~")

    """
    Check if GTO+ is available. If it is, we receive confirmation. If not, GTO+ will
    crash and the process will terminate. That will confirm it is not available.
    """

    def ask_if_processing(self):
        return self._send("Still processing instruction?")

    """
    Private method that sends a message to GTO+
    """

    def _send(self, message: str):
        if self._verbose:
            print(f'Attempting to send message to GTO+: "{message}"')

        message = self._format_message(message)

        total_sent = 0

        while total_sent < len(message):
            sent = self._sock.send(message[total_sent:])

            if sent == 0:
                raise RuntimeError("Socket connection lost")

            total_sent += sent

    """
    Private method that formats messages for GTO+
    """

    def _format_message(self, message: str):
        return "~{}~".format(message).encode("utf-8")

    """
    Private method that receives a message from GTO+
    """

    def _receive(self):
        chunks, received = [], 0

        # Collect chunks of the message until it is fully received
        while True:
            chunk = self._sock.recv(self._block_len)

            if chunk == b"~Solver still running. Please try again later.~":
                if self._verbose:
                    print("Solver still processing. Will retry shortly.")

                time.sleep(self._sleep_time_sec)

                continue

            received += len(chunk)
            chunks.append(chunk)

            if len(chunk) < self._block_len:
                break

        response = b"".join(chunks)

        if self._verbose:
            print(f"Received response from GTO+: {response}")

        return response


if __name__ == "__main__":
    print("Running tests")

    import doctest

    doctest.testmod()

    print("Finished with tests")
