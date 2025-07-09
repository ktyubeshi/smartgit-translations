#!/usr/bin/env bash

# SmartGit Diff Tool wrapper for extract_changes.py
# Usage:
#   Command: extract_changes.sh
#   Arguments: ${leftFile} ${rightFile} --output ${rightLocalFile}_changes.po

# Function to show usage
show_usage() {
    echo "Usage: $0 <base_file> <compare_file> [--output <output_file>]" >&2
    echo "" >&2
    echo "Arguments:" >&2
    echo "  base_file      The original PO file" >&2
    echo "  compare_file   The modified PO file to compare" >&2
    echo "" >&2
    echo "Options:" >&2
    echo "  --output       Specify output file (default: <compare_file>_changes.po)" >&2
    exit 1
}

# Check if running in a TTY
if [ ! -t 0 ] && [ ! -t 1 ]; then
    # Not in a TTY, open in Terminal
    # Pass all arguments to the new terminal
    osascript -e "tell application \"Terminal\" to do script \"cd '$PWD' && '$0' $*\""
    exit 0
fi

# Parse arguments
BASE_FILE=""
COMPARE_FILE=""
OUTPUT_FILE=""
CUSTOM_OUTPUT=false

while [ "$#" -gt 0 ]; do
    case "$1" in
        --output)
            if [ -z "$2" ]; then
                echo "Error: --output requires a file name" >&2
                show_usage
            fi
            OUTPUT_FILE="$2"
            CUSTOM_OUTPUT=true
            shift 2
            ;;
        -*)
            echo "Error: Unknown option: $1" >&2
            show_usage
            ;;
        *)
            if [ -z "$BASE_FILE" ]; then
                BASE_FILE="$1"
            elif [ -z "$COMPARE_FILE" ]; then
                COMPARE_FILE="$1"
            else
                echo "Error: Too many arguments" >&2
                show_usage
            fi
            shift
            ;;
    esac
done

# Check if required arguments provided
if [ -z "$BASE_FILE" ] || [ -z "$COMPARE_FILE" ]; then
    echo "Error: Missing required arguments" >&2
    show_usage
fi

# Check if files exist
if [ ! -f "$BASE_FILE" ]; then
    echo "Error: Base file '$BASE_FILE' does not exist" >&2
    exit 1
fi

if [ ! -f "$COMPARE_FILE" ]; then
    echo "Error: Compare file '$COMPARE_FILE' does not exist" >&2
    exit 1
fi

# Generate output filename if not specified
if [ -z "$OUTPUT_FILE" ]; then
    OUTPUT_FILE="${COMPARE_FILE%.po}_changes.po"
fi

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv first." >&2
    echo "See: https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "Error: Virtual environment not found at $SCRIPT_DIR/.venv" >&2
    echo "Please run 'uv venv' in the src directory first." >&2
    exit 1
fi

# Run extract_changes.py with uv
echo "Extracting changes from '$BASE_FILE' to '$COMPARE_FILE'..." >&2
echo "Output will be saved to: $OUTPUT_FILE" >&2

uv run "$SCRIPT_DIR/extract_changes.py" "$BASE_FILE" "$COMPARE_FILE" --output "$OUTPUT_FILE"

# Check exit status
if [ $? -eq 0 ]; then
    echo "Successfully extracted changes to '$OUTPUT_FILE'" >&2
    # Keep terminal open if not in TTY
    if [ ! -t 0 ] && [ ! -t 1 ]; then
        echo ""
        echo "Press Enter to close this window..."
        read -r
    fi
else
    echo "Error: Failed to extract changes" >&2
    # Keep terminal open if not in TTY
    if [ ! -t 0 ] && [ ! -t 1 ]; then
        echo ""
        echo "Press Enter to close this window..."
        read -r
    fi
    exit 1
fi