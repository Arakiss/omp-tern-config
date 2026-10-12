import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import orbit

TASKS = [
    {"id": 1, "title": "Polish the navigation console"},
    {"id": 2, "title": "Add CAFÉ search support"},
    {"id": 3, "title": "Review the navigation tests"},
]


def run(*args):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "tasks.json"
        path.write_text(json.dumps(TASKS), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            orbit.main(["list", "--file", str(path), *args])
    return out.getvalue()


class OrbitTests(unittest.TestCase):
    def test_filtered_json_unicode_in_order(self):
        out = run("--search", "café", "--json")
        self.assertIn("CAFÉ", out)
        self.assertEqual(json.loads(out), [TASKS[1]])
        nav = json.loads(run("--search", "NAVIGATION", "--json"))
        self.assertEqual([t["id"] for t in nav], [1, 3])

    def test_empty_result(self):
        self.assertEqual(json.loads(run("--search", "zzz", "--json")), [])
        self.assertEqual(run("--search", "zzz"), "")


if __name__ == "__main__":
    unittest.main()
