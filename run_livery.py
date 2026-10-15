#!/usr/bin/env python3
"""Launcher: python run_livery.py <command> [options]   (see README.md). Same as: python -m fm4livery ..."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fm4livery.cli import main
if __name__ == '__main__':
    main(['gui'] if len(sys.argv) == 1 else None)   # double-click / no arguments: open the GUI
