#!/usr/bin/env python3
"""
AI Venture Digest - Daily Automation Script
Run this script daily to fetch, curate, and optionally send newsletter.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPTS_DIR = Path(__file__).parent


def run_script(script_name: str) -> bool:
    """Run a Python script and return success status."""
    script_path = SCRIPTS_DIR / script_name
    print(f"\n{'='*50}")
    print(f"Running: {script_name}")
    print(f"{'='*50}\n")

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            cwd=SCRIPTS_DIR.parent
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running {script_name}: {e}")
        return False


def main():
    """Run the daily digest pipeline."""
    print("\n" + "=" * 60)
    print("🚀 AI VENTURE DIGEST - DAILY RUN")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Step 1: Fetch and curate content
    if not run_script('fetcher.py'):
        print("\n❌ Fetcher failed. Aborting.")
        sys.exit(1)

    # Step 2: Generate newsletter
    if not run_script('newsletter.py'):
        print("\n⚠️ Newsletter generation failed, but content was fetched.")

    print("\n" + "=" * 60)
    print("✅ DAILY RUN COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("  • Open index.html in your browser to view the digest")
    print("  • Check templates/ for the generated newsletter HTML")
    print("\n")


if __name__ == '__main__':
    main()
