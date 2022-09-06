from pathlib import Path
import unittest
from gto import GTO


class TestGTO(unittest.TestCase):
    akq_game = Path(__file__).parent.parent / "resources" / "solves" / "AKQ-Game.gto"
    solver = GTO()

    def test_connect_and_disconnect(self):
        s = self.solver
        self.assertEqual(s.connect(), "You are connected to GTO+")
        s.disconnect()
        self.assertIsNone(s.sock)

    def test_load_file(self):
        s = self.solver
        s.connect()
        self.assertEqual(s.load_file(self.akq_game), "File successfully loaded.")
        s.disconnect()

    def test_request_node_data(self):
        s = self.solver
        s.connect()
        s.load_file(self.akq_game)
        node_data = s.request_node_data()
        oop = node_data["oop"]
        ip = node_data["ip"]
        self.assertEqual(["Bet 1", "Check"], node_data["actions"])
        self.assertEqual("oop", node_data["pos"])
        # TODO: test oop, ip
        s.disconnect()

    def test_request_pot_stacks(self):
        s = self.solver
        s.connect()
        s.load_file(self.akq_game)
        ps = s.request_pot_stacks()
        self.assertEqual(1.0, ps["pot"])
        self.assertEqual(1.0, ps["oop_stack"])
        self.assertEqual(1.0, ps["ip_stack"])
        s.disconnect()

    def test_request_current_line(self):
        s = self.solver
        s.connect()
        s.load_file(self.akq_game)
        self.assertEqual([], s.request_current_line())
        s.disconnect()

    def test_take_action(self):
        s = self.solver
        s.connect()
        s.load_file(self.akq_game)
        s.take_action(0)
        nd = s.request_node_data()
        self.assertEqual("ip", nd["pos"])
        self.assertEqual(["Bet 1"], s.request_current_line())

        s.load_file(self.akq_game)
        s.take_action(1)
        nd = s.request_node_data()
        self.assertEqual("ip", nd["pos"])
        self.assertEqual(["Check"], s.request_current_line())


if __name__ == "__main__":
    unittest.main()
