import json
import math
import struct
import unittest

import net


class NetworkFramingTests(unittest.TestCase):
    def test_message_round_trip_uses_a_bounded_object_frame(self):
        framed = net.pack_message({"t": "input", "tx": 0.25, "fire": False})
        length = struct.unpack(">I", framed[:4])[0]
        self.assertEqual(length, len(framed) - 4)
        self.assertEqual(json.loads(framed[4:]),
                         {"t": "input", "tx": 0.25, "fire": False})

    def test_non_objects_and_non_finite_numbers_are_rejected(self):
        with self.assertRaises(TypeError):
            net.pack_message(["not", "an", "object"])
        with self.assertRaises(ValueError):
            net.pack_message({"tx": math.nan})
        self.assertFalse(net._safe_json_value({"tx": math.inf}))

    def test_untrusted_coordinates_are_finite_and_clamped(self):
        self.assertEqual(net.bounded_float("nan", 0.5, 0.1, 0.9), 0.5)
        self.assertEqual(net.bounded_float(None, 0.5, 0.1, 0.9), 0.5)
        self.assertEqual(net.bounded_float(99, 0.5, 0.1, 0.9), 0.9)
        self.assertEqual(net.bounded_float(-2, 0.5, 0.1, 0.9), 0.1)


if __name__ == "__main__":
    unittest.main()
