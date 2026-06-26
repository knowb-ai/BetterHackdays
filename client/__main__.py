#!/usr/bin/env python3
"""Terminal CLI for BetterHackdays.

Invoke from a terminal to derive your anonymous harness_id from your Git email
and talk to the shared backend. No flags needed for the most common flow:

    export BETTERHACKDAYS_BACKEND_URL=https://8000-<sandbox>.proxy.daytona.work
    python -m client connect
    python -m client cards
    python -m client like harness_backend_002

Identity is derived automatically from `git config user.email` (SHA-256 hashed),
or override with `BETTERHACKDAYS_HARNESS_ID`.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from . import (
    connect,
    derive_harness_id,
    get_harness_id,
    get_match_cards,
    get_matches,
    like_profile,
    pass_profile,
    update_profile,
)


def _dump(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print(__doc__)
        print("commands: whoami, connect, update, cards, like <id>, pass <id>, matches")
        return 0

    cmd = argv[0]
    rest = argv[1:]

    if cmd == "whoami":
        print(f"harness_id: {get_harness_id()}")
        return 0

    if cmd == "connect":
        _dump(connect())
        return 0

    if cmd == "update":
        # Accept either inline JSON or key=val pairs for convenience.
        data: dict[str, Any] = {}
        if rest and rest[0].startswith("{"):
            data = json.loads(rest[0])
        else:
            for pair in rest:
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    data[k] = v.split(",") if "," in v else v
        _dump(update_profile(**data))
        return 0

    if cmd == "cards":
        _dump(get_match_cards())
        return 0

    if cmd == "like":
        if not rest:
            print("usage: like <to_harness_id>", file=sys.stderr)
            return 2
        _dump(like_profile(rest[0]))
        return 0

    if cmd == "pass":
        if not rest:
            print("usage: pass <to_harness_id>", file=sys.stderr)
            return 2
        _dump(pass_profile(rest[0]))
        return 0

    if cmd == "matches":
        _dump(get_matches())
        return 0

    print(f"unknown command: {cmd}", file=sys.stderr)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
