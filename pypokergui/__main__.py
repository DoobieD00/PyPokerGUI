#!/usr/bin/env python

import os
import sys
import argparse
import webbrowser
import yaml

sys.stdout.reconfigure(encoding='utf-8')


# Path setup
root = os.path.join(os.path.dirname(__file__), "..")
src = os.path.join(root, "pypokergui")
sys.path.append(root)
sys.path.append(src)

from pypokergui.server.poker import start_server
from pypokergui.config_builder import build_config

def serve(config_path, port, speed):
    host = "localhost"

    # Open browser
    webbrowser.open(f"http://{host}:{port}")

    # Load YAML config
    with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
        raw_data = f.read()
        clean_data = raw_data.replace("\x00", "")  # null characters in string form
        config = yaml.safe_load(clean_data)

    start_server(config_path, port, speed)

def main():
    parser = argparse.ArgumentParser(description="PyPokerGUI CLI (no click)")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Run the poker GUI server")
    serve_parser.add_argument("config", help="Path to config YAML file")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to run server on")
    serve_parser.add_argument("--speed", choices=["dev", "slow", "moderate", "fast"], default="moderate", help="Game speed")

    # Build config command
    build_parser = subparsers.add_parser("build_config", help="Build a new poker config YAML")
    build_parser.add_argument("-r", "--maxround", type=int, default=10, help="Final round of the game")
    build_parser.add_argument("-s", "--stack", type=int, default=100, help="Starting stack for each player")
    build_parser.add_argument("-b", "--small_blind", type=int, default=5, help="Small blind amount")
    build_parser.add_argument("-a", "--ante", type=int, default=0, help="Ante amount")

    args = parser.parse_args()

    if args.command == "serve":
        serve(args.config, args.port, args.speed)
    elif args.command == "build_config":
        build_config(args.maxround, args.stack, args.small_blind, args.ante, None)
    else:
        parser.print_help()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except OSError:
            pass  # stdout might already be closed when piping
        print("\n[INFO] Interrupted by user. Exiting gracefully.", file=sys.stderr)
        sys.exit(0)

