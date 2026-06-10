import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

_store: dict[str, list[float]] = defaultdict(list)
_LIMIT = 20
_WINDOW = 60  # seconds


def reset() -> None:
    """Clear all buckets. Used between tests to prevent cross-test contamination."""
    _store.clear()


def rate_limit(request: Request) -> None:
    """Dependency: 20 POST requests per IP per 60 seconds."""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    hits = [t for t in _store[ip] if now - t < _WINDOW]
    if len(hits) >= _LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов. Повторите попытку через минуту.",
        )
    hits.append(now)
    _store[ip] = hits
