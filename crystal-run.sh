#!/usr/bin/env bash
#
# crystal-run.sh - AI Venture Digest Launch Script
# Safely kills any running instances before launching the project.
#

set -e

PROJECT_NAME="ai-venture-digest"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔍 Checking for running instances..."

# Kill any running Python processes for this project
# Look for processes running fetcher.py, newsletter.py, or run_daily.py
pgrep -f "python.*scripts/(fetcher|newsletter|run_daily)\.py" | while read -r pid; do
    echo "  → Killing process $pid"
    kill "$pid" 2>/dev/null || true
done

# Kill any running local dev servers on port 8000
if lsof -ti:8000 >/dev/null 2>&1; then
    echo "  → Killing local server on port 8000"
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
fi

# Give processes a moment to terminate
sleep 1

echo ""
echo "🚀 Launching AI Venture Digest..."
echo ""

# Run the daily pipeline
cd "$SCRIPT_DIR"
python3 scripts/run_daily.py

echo ""
echo "✅ Launch complete!"
echo ""
