from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMETERS = {
    "embed",
    "ref",
    "source",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def canonical_job_url(url: str) -> str:
    """Remove tracking-only URL differences so sources share one job identity."""
    if not url:
        return ""
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/")
    for suffix in ("/apply", "/application"):
        if path.lower().endswith(suffix):
            path = path[: -len(suffix)]
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.lower() not in TRACKING_PARAMETERS and not key.lower().startswith("utm_")
        )
    )
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


@dataclass(frozen=True)
class Job:
    source: str
    external_id: str
    title: str
    company: str
    location: str
    url: str
    description: str = ""
    updated_at: str = ""

    @property
    def key(self) -> str:
        identity = canonical_job_url(self.url) or f"{self.source}|{self.external_id}"
        return sha256(identity.encode()).hexdigest()


@dataclass(frozen=True)
class Match:
    job: Job
    score: int
    reasons: tuple[str, ...] = field(default_factory=tuple)
    discovered_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
