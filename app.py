from __future__ import annotations

import argparse
from pathlib import Path

from square_cards.server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Square Cards Modulverwaltung")
    parser.add_argument("--host", default="127.0.0.1", help="Host für den Webserver")
    parser.add_argument("--port", default=8000, type=int, help="Port für den Webserver")
    parser.add_argument(
        "--workspace",
        default=str(Path(__file__).resolve().parent),
        help="Arbeitsverzeichnis mit callerschool-pattern und data/",
    )
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, workspace=Path(args.workspace).resolve())


if __name__ == "__main__":
    main()

