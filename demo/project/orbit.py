#!/usr/bin/env python3
"""Orbit: a tiny task-list CLI for a staged public coding demo."""
import argparse
import json
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list",))
    parser.add_argument("--file", type=Path, default=Path(__file__).with_name("tasks.json"))
    parser.add_argument("--search", metavar="QUERY", help="case-insensitive (Unicode casefold) title filter")
    parser.add_argument("--json", action="store_true", help="emit a JSON array")
    args = parser.parse_args(argv)
    tasks = json.loads(args.file.read_text(encoding="utf-8"))
    if args.search is not None:
        query = args.search.casefold()
        tasks = [t for t in tasks if query in t["title"].casefold()]
    if args.json:
        print(json.dumps(tasks, ensure_ascii=False))
        return
    for task in tasks:
        print(f"{task['id']:>2}  {task['title']}")


if __name__ == "__main__":
    main()
