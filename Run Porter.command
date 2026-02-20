#!/bin/bash
# Porter Quick Start - Double-click to start monitoring!

cd "$(dirname "$0")"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

clear
echo "Starting Porter..."
echo ""

# Run the bot
python3 -m src.main run

echo ""
echo "Press any key to close..."
read -n 1
