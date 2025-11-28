"""
Session storage utilities.
Owner: Jie Lin, Ph.D. / TLin Investments LLC
"""

import time
from typing import Dict, Any

# In-memory session storage (cleared on restart)
# Structure: { session_id: { 'data': ParsedData, 'created_at': timestamp, 'last_accessed': timestamp } }
session_storage: Dict[str, Dict[str, Any]] = {}

# Session timeout in seconds (30 minutes)
SESSION_TIMEOUT = 1800


def cleanup_expired_sessions() -> int:
    """Remove sessions that have exceeded the timeout period."""
    current_time = time.time()
    expired = [
        sid for sid, session in session_storage.items()
        if current_time - session.get('last_accessed', 0) > SESSION_TIMEOUT
    ]
    for sid in expired:
        del session_storage[sid]
    return len(expired)


def touch_session(session_id: str):
    """Refresh last-access time for a session."""
    if session_id in session_storage:
        session_storage[session_id]['last_accessed'] = time.time()
