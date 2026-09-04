"""Audit logging utilities (append-only in-memory for scaffold)

In Step 4 we'll expose endpoints to read the last 50 logs.
"""
from collections import deque
from datetime import datetime

# append-only ring buffer for last N logs (persist in-memory)
AUDIT_LOG = deque(maxlen=1000)


def append_log(entry: dict):
    entry_copy = dict(entry)
    entry_copy.setdefault("timestamp", datetime.utcnow().isoformat() + "Z")
    AUDIT_LOG.append(entry_copy)


def get_recent(n=50):
    return list(AUDIT_LOG)[-n:]
