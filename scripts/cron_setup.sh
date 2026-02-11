#!/bin/bash
# AI Venture Digest - Cron Setup Script
# This script helps set up automated daily runs

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH=$(which python3)
RUN_SCRIPT="$SCRIPT_DIR/run_daily.py"

echo "==========================================="
echo "AI Venture Digest - Cron Setup"
echo "==========================================="
echo ""
echo "This will set up a daily cron job to run at 7:00 AM."
echo ""
echo "Script location: $RUN_SCRIPT"
echo "Python: $PYTHON_PATH"
echo ""

# Create the cron entry
CRON_ENTRY="0 7 * * * cd $SCRIPT_DIR/.. && $PYTHON_PATH $RUN_SCRIPT >> $SCRIPT_DIR/../logs/cron.log 2>&1"

echo "Proposed cron entry:"
echo "$CRON_ENTRY"
echo ""
echo "To install, run:"
echo "  (crontab -l 2>/dev/null; echo \"$CRON_ENTRY\") | crontab -"
echo ""
echo "Or manually add to your crontab with: crontab -e"
echo ""
echo "==========================================="
echo "Alternative: GitHub Actions"
echo "==========================================="
echo ""
echo "If you're hosting on GitHub, copy this workflow to .github/workflows/daily.yml:"
echo ""
cat << 'EOF'
name: Daily AI Digest

on:
  schedule:
    - cron: '0 7 * * *'  # Run at 7 AM UTC
  workflow_dispatch:  # Allow manual trigger

jobs:
  fetch-and-publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Run fetcher
        run: python scripts/fetcher.py

      - name: Generate newsletter
        env:
          MAILCHIMP_API_KEY: ${{ secrets.MAILCHIMP_API_KEY }}
          MAILCHIMP_LIST_ID: ${{ secrets.MAILCHIMP_LIST_ID }}
        run: python scripts/newsletter.py

      - name: Commit and push data
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add data/
          git diff --quiet && git diff --staged --quiet || git commit -m "Update daily digest"
          git push
EOF
echo ""
