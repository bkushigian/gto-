from pathlib import Path
import unittest
from gto import GTO


class TestGTO(unittest.TestCase):
    """
    Although using a unit testing library, these are integration tests. They require a running
    instance of GTO+.
    """

    def setUp(self) -> None:
        self.akq_game = (
            Path(__file__).parent.parent / "resources" / "solves" / "AKQ-Game.gto"
        )
        self.solver = GTO(verbose=True)
        self.solver.connect()

        result = self.solver.load_file(self.akq_game)

        self.assertEqual(result, "File successfully loaded.")

    def tearDown(self) -> None:
        self.solver.disconnect()

    def test_load_file(self) -> None:
        result = self.solver.load_file(self.akq_game)
        self.assertEqual(result, "File successfully loaded.")

    def test_get_node_data(self) -> None:
        node_data = self.solver.get_node_data()

        self.assertEqual(["2d", "2c", "2h", "3d", "3c"], node_data["board"])
        self.assertEqual("oop", node_data["next_to_act"])
        self.assertEqual(["Bet 1", "Check"], node_data["actions"])

    def test_get_pot_stacks(self) -> None:
        pot_and_stacks = self.solver.get_pot_stacks()

        self.assertEqual(1.0, pot_and_stacks["pot"])
        self.assertEqual(1.0, pot_and_stacks["oop_stack"])
        self.assertEqual(1.0, pot_and_stacks["ip_stack"])

    def test_get_current_line(self) -> None:
        current_line = self.solver.get_current_line()
        self.assertEqual([], current_line)

    def test_take_first_action(self) -> None:
        self.solver.take_action(0)

        nd = self.solver.get_node_data()
        self.assertEqual("ip", nd["next_to_act"])

        current_line = self.solver.get_current_line()
        self.assertEqual(["Bet 1"], current_line)

    def test_take_second_action(self) -> None:
        self.solver.take_action(1)

        nd = self.solver.get_node_data()
        self.assertEqual("ip", nd["next_to_act"])

        current_line = self.solver.get_current_line()
        self.assertEqual(["Check"], current_line)


if __name__ == "__main__":
    unittest.main()
