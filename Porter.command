#!/bin/bash
# Porter Interactive Launcher - Double-click to run!

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Interactive menu loop
while true; do
    clear

    # Run porter to show the menu
    python3 -m src.main

    echo ""
    echo "Enter command (or 'q' to quit):"
    read -p "> " choice

    case $choice in
        1|run)
            python3 -m src.main run
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        2|add|add-task)
            python3 -m src.main add-task
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        3|list|list-tasks)
            python3 -m src.main list-tasks
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        4|login)
            python3 -m src.main login
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        5|status)
            python3 -m src.main status
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        6|guide)
            python3 -m src.main guide
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        s|setup)
            python3 -m src.main setup
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        h|help|\?)
            python3 -m src.main --help
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        q|quit|exit)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            # Try to run whatever they typed as a porter command
            if [ -n "$choice" ]; then
                python3 -m src.main $choice
                echo ""
                echo "Press Enter to continue..."
                read
            fi
            ;;
    esac
done
