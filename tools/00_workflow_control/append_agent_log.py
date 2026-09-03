#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append a screen-visible agent message to a run log."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    parser.add_argument(
        "--agent",
        default="agent",
        help="Agent or workflow-step name to show in the log heading.",
    )
    parser.add_argument(
        "--message",
        help="Message to append. If omitted, stdin is used.",
    )
    args = parser.parse_args()

    message = args.message if args.message is not None else sys.stdin.read()
    message = message.strip()
    if not message:
        print("ERROR: no message provided", file=sys.stderr)
        return 1

    run_dir = Path(args.run_dir)
    log_path = run_dir / "logs" / "agent_screen_log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text(
            "# Agent Screen Log\n\n"
            "This file records substantive screen-visible agent output for this run. "
            "Do not include hidden chain-of-thought, credentials, paper full text, "
            "or large generated artifacts.\n",
            encoding="utf-8",
        )

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## {timestamp} - {args.agent}\n\n{message}\n")
    print(f"Appended log entry to {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
