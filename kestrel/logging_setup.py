from __future__ import annotations

import logging


def setup_logging(level: str = "INFO") -> logging.Logger:
    root = logging.getLogger("kestrel")
    if not root.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(h)
    root.setLevel(getattr(logging, level, logging.INFO))
    root.propagate = False
    return root
