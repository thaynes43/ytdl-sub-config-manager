"""Entry point for running ytdl-sub config manager as a module."""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
