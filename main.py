#!/usr/bin/env python3
"""POPVPN X entry point.

    python main.py                 # full run
    python main.py --dry-run       # fetch + parse only
    python main.py --help          # all options
"""

from popvpn.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
