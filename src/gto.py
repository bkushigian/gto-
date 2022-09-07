#!/usr/bin/env python3

import socket
import time
from pathlib import Path
from typing import Optional, Tuple, Union, Dict, Any, List
from xmlrpc.client import Boolean


class GTO:
    def __init__(
        self, port: int = 55143, addr: str = "localhost", verbose: Boolean = False
    ):
        self._port: int = port
        self._addr: str = addr
        self._sock: Optional[socket.socket] = None
        self._verbose: Boolean = verbose

        # Messages to GTO+ are blocked into 4096 byte chunks
        self._block_len = 4096

        # GTO+ has fragile interrupt handling. We sleep at these points in attempt
        # to keep GTO+ running. Until retry logic is added and GTO+'s API is better
        # understood, these will have to suffice. Shorter sleep durations tend to
        # cause problems but these more-or-less work.
        self._long_sleep_sec = 0.5
        self._short_sleep_sec = 0.1

    def connect(self) -> str:
        """
        Opens a connection to GTO+ using the settings provided in the constructor.
        If GTO+ does not confirm a successful connection, this method raises an
        exception.
        """
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

    def disconnect(self) -> None:
        """
        Closes a connection to GTO+.
        """
        if not self._sock:
            return

        self._sock.close()
        self._sock = None

    def load_file(self, path: Union[Path, str]) -> str:
        """
        Loads a saved solve file
        """
        self._send("Load file: {}".format(path))
        time.sleep(self._short_sleep_sec)
        response = self._receive().decode().strip("~")

        return response

    def get_node_data(self) -> Dict[str, Any]:
        """
        Requests node data containing information about the board, player to act, each
        player's actions, and each player's holdings. This is stored as a `dict` with
        the following fields:

        + "board": a list of cards on the board, e.g., ["2h", "5c", "Td", "Jd"]
        + "next_to_act": the player who is next to act (either "ip" or "oop")
        + "oop": a dict representing OOP's the EV and weight for each of the
                combos in their range, as well as the frequency and EV of each
                action for each combo in their range; if they are not next to
                act then they have no actions and this part is blank.
        + "ip": a dict representing OOP's the EV and weight for each of the
                combos in their range, as well as the frequency and EV of each
                action for each combo in their range; if they are not next to
                act then they have no actions and this part is blank.
        + "actions": a list of each action available to the player who is next
                to act. E.g., `["Check", "Bet 1.0", "Bet 2.5"]

        >>> solver = GTO()
        >>> solver.connect()
        'You are connected to GTO+'
        >>> solver.load_akq_game()
        >>> node_data = solver.get_node_data()
        >>> node_data['next_to_act']
        'oop'
        >>> node_data['actions']
        ['Bet 1', 'Check']
        >>> node_data['oop']['KcKh']['COMBOS']
        1.0
        >>> node_data['oop']['KcKh']['EQUITY']
        50.0
        >>> node_data['oop']['KcKh']['Bet 1']['FREQ']
        0.0
        >>> node_data['oop']['KcKh']['Check']['FREQ']
        100.0
        >>> node_data['oop']['KcKh']['Check']['EV']
        0.25
        >>> node_data['ip']['QcQh']['COMBOS']
        1.0
        >>> node_data['ip']['QcQh']['EQUITY']
        0.0
        """
        board, oop, ip = self._request_node_data()
        actions = self._request_action_data()

        oop, is_oop_to_act = self._parse_player_data(oop, actions)
        ip, is_ip_to_act = self._parse_player_data(ip, actions)

        if is_ip_to_act == is_oop_to_act:
            message = f"IP to act: {is_ip_to_act}. OOP to act: {is_oop_to_act}."
            raise RuntimeError(f"Next to act collision. {message}")

        next_to_act = "ip" if is_ip_to_act else "oop"

        return {
            "board": board,
            "next_to_act": next_to_act,
            "oop": oop,
            "ip": ip,
            "actions": actions,
        }

    def _request_node_data(self) -> Tuple[List[str], str, str]:
        """
        Private method that parses the response to a request for node data. Returns a tuple
        containing raw text of the board, IP, and OOP data.
        """
        self._send("Request node data")

        time.sleep(self._long_sleep_sec)

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
        board = [board[i : i + 2] for i in range(0, len(board), 2)]

        return (board, oop, ip)

    def _request_action_data(self) -> List[str]:
        """
        Private method that parses the response to a request for action data
        """
        self._send("Request action data")

        time.sleep(self._short_sleep_sec)

        # The response has the following format:
        #
        # ~[n actions: X1,X2, ... Xn]~
        response = self._receive().decode().strip("~")

        # Drop the brackets and "n actions:" and collect each action's name in a list.
        # For example: ['Bet 1', 'Check']
        result = response.strip("]").split(": ")[1].split(",")

        return result

    def _parse_player_data(
        self, raw_player_data: str, actions: List[str]
    ) -> Tuple[Dict[str, Any], Boolean]:
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
        player_data_rows = raw_player_data.strip().split("\r\n")

        # Metadata are IP/OOP, number of combos, and number of available actions.
        # The available actions are only present when the player is next to act
        # (in this node). If the player is not next to act, there are only two
        # elements in the list.
        metadata = player_data_rows[0].strip().split(", ")
        is_next_to_act = True if len(metadata) == 3 else False

        # The first item in the raw response are the metadata. The second item is a
        # comma-separated list of column names. If the player is not next to act, it
        # contains 'HANDS, COMBOS, EQUITY'. When the player is next to act there are
        # additional columns for the frequency of each action. For example, when the
        # player can bet or fold these will be 'WEIGHT1, WEIGHT2, EV1, EV2'. The weights
        # are the frequencies.
        player_data_rows = [line.split() for line in player_data_rows[2:]]

        player_data = {}

        for row in player_data_rows:
            hand_details: Dict[str, Union[float, Dict[str, float]]] = {}

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

    def get_pot_stacks(self) -> Dict[str, float]:
        self._send("Request pot/stacks")

        time.sleep(self._short_sleep_sec)

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

    def get_current_line(self) -> List[str]:
        self._send("Request current line")
        time.sleep(self._short_sleep_sec)
        response = self._receive().decode().strip("~")

        if response == "Hand is at start of tree.":
            return []

        return response.split(",")

    def load_akq_game(self) -> None:
        akq_game = (
            Path(__file__).parent.parent / "resources" / "solves" / "AKQ-Game.gto"
        )
        self.load_file(akq_game)

    def take_action(self, action_n: int) -> None:
        self._send("Take action: {}".format(action_n))
        time.sleep(self._short_sleep_sec)
        self._receive().decode().strip("~")

    def ask_if_processing(self) -> bytes:
        """
        Check if GTO+ is available. If it is, we receive confirmation. If not, GTO+ will
        crash and the process will terminate. That will confirm it is not available.
        """
        self._send("Still processing instruction?")
        return self._receive()

    def _send(self, message: str) -> None:
        """
        Private method that sends a message to GTO+
        """
        if self._verbose:
            print(f'Attempting to send message to GTO+: "{message}"')

        message = self._format_message(message)

        total_sent = 0

        while total_sent < len(message):
            sent = self._sock.send(message[total_sent:])

            if sent == 0:
                raise RuntimeError("Socket connection lost")

            total_sent += sent

    def _format_message(self, message: str) -> bytes:
        """
        Private method that formats messages for GTO+
        """
        return "~{}~".format(message).encode("utf-8")

    def _receive(self) -> bytes:
        """
        Private method that receives a message from GTO+
        """
        chunks = []

        # Collect chunks of the message until it is fully received
        while True:
            chunk = self._sock.recv(self._block_len)

            if chunk == b"~Solver still running. Please try again later.~":
                if self._verbose:
                    print("Solver still processing. Will retry shortly.")

                time.sleep(self._short_sleep_sec)

                continue

            chunks.append(chunk)

            if len(chunk) < self._block_len:
                break

        response = b"".join(chunks)

        if self._verbose:
            print(f"Received response from GTO+: {response.decode()}")

        return response


if __name__ == "__main__":
    print("Running tests")

    import doctest

    doctest.testmod()

    print("Finished with tests")
