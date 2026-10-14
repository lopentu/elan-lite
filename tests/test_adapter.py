import unittest
from backend.pose_adapter import adapt_results
from backend.core import ValidationError


class Adapter(unittest.TestCase):
    def test_topology_timestamps_missing_and_2d(self):
        source = {
            "model": {"name": "synthetic-mediapipe-shaped-fixture", "version": "1"},
            "topologyVersion": "test-two-v1",
            "durationMs": 1000,
            "groups": {"rightWrist": {"count": 2, "edges": [[0, 1]]}},
            "frames": [
                {
                    "timeMs": 0,
                    "rightWrist": [{"x": 0.1, "y": 0.2, "z": 99}, {"x": 0.3, "y": 0.4}],
                },
                {"timeMs": 100, "rightWrist": None},
            ],
        }
        pose = adapt_results(source)
        self.assertEqual(pose["frames"][0]["points"]["rightWrist:0"], [0.1, 0.2])
        self.assertEqual(pose["frames"][1]["points"], {})
        self.assertEqual(pose["topology"]["edges"], [["rightWrist:0", "rightWrist:1"]])
        self.assertIn("z", pose["discardedFields"])
        source["frames"][0]["rightWrist"] = []
        with self.assertRaises(ValidationError):
            adapt_results(source)
