from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256


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
        identity = f"{self.source}|{self.external_id or self.url}"
        return sha256(identity.encode()).hexdigest()


@dataclass(frozen=True)
class Match:
    job: Job
    score: int
    reasons: tuple[str, ...] = field(default_factory=tuple)
    discovered_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
