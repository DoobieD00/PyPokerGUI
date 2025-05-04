#!/bin/bash
echo "Starting Poker Game Server..."
python -m pypokergui serve ./poker_conf.yaml --port 8000 --speed moderate
