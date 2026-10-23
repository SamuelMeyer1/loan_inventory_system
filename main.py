from __future__ import annotations

import argparse

from backend.server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Loan Inventory HTTP server")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port måste vara mellan 0 och 65535")
    run_server(port=args.port)


if __name__ == "__main__":
    main()
