#!/usr/bin/env python3
"""
Run vulture and fail if any unused code is found that is not listed in
`tools/vulture_whitelist.txt`.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "JiraVision" / "app" / "app"
WHITELIST = ROOT / "tools" / "vulture_whitelist.txt"
MIN_CONFIDENCE = "50"

NAME_RE = re.compile(r"^(.+?):(\d+): .* '(?P<name>[^']+)' \(.*$")


def load_whitelist() -> set[str]:
    if not WHITELIST.exists():
        return set()
    s = set()
    for line in WHITELIST.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        s.add(line)
    return s


def run_vulture(path: Path) -> list[tuple[str, int, str]]:
    cmd = [sys.executable, "-m", "vulture", "--min-confidence", MIN_CONFIDENCE, str(path)]
    p = subprocess.run(cmd, capture_output=True, text=True)

    if p.returncode != 0 and p.stdout.strip() == "":
        # vulture may write errors to stderr
        print(p.stderr, file=sys.stderr)
        p.check_returncode()

    out = p.stdout.strip()
    if not out:
        return []

    results: list[tuple[str, int, str]] = []
    for line in out.splitlines():
        m = NAME_RE.match(line)
        if m:
            filename, lineno, name = m.group(1), int(m.group(2)), m.group("name")
            results.append((filename, lineno, name))
        else:
            # fallback: try to extract a quoted name
            q = re.search(r"'([^']+)'", line)
            if q:
                results.append((line, 0, q.group(1)))
            else:
                results.append((line, 0, "<unknown>"))
    return results


def main() -> int:
    whitelist = load_whitelist()
    results = run_vulture(TARGET)

    unexpected = [r for r in results if r[2] not in whitelist]

    if unexpected:
        print("Unexpected unused code found:")
        for filename, lineno, name in unexpected:
            if lineno:
                print(f"{filename}:{lineno}: '{name}'")
            else:
                print(f"{filename}: '{name}'")
        print("\nIf these are false positives, add the symbol names to tools/vulture_whitelist.txt")
        return 2

    print("No unexpected unused code found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
