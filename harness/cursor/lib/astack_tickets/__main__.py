"""Allow running via `python3 -m astack_tickets`."""
from __future__ import annotations

import sys

from astack_tickets.cli import main

if __name__ == "__main__":
    sys.exit(main())
