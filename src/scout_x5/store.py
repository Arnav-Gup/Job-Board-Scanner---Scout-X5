from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import Job, Match, canonical_job_url


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_key TEXT PRIMARY KEY,
                canonical_key TEXT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL,
                score INTEGER NOT NULL DEFAULT 0,
                reasons TEXT NOT NULL DEFAULT '[]',
                first_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._migrate()

    def _migrate(self) -> None:
        columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(jobs)")}
        additions = {
            "canonical_key": "TEXT",
            "location": "TEXT NOT NULL DEFAULT ''",
            "score": "INTEGER NOT NULL DEFAULT 0",
            "reasons": "TEXT NOT NULL DEFAULT '[]'",
        }
        for name, definition in additions.items():
            if name not in columns:
                self.connection.execute(f"ALTER TABLE jobs ADD COLUMN {name} {definition}")
        rows = self.connection.execute(
            "SELECT job_key, url FROM jobs WHERE canonical_key IS NULL OR canonical_key = ''"
        ).fetchall()
        for row in rows:
            canonical = canonical_job_url(row["url"]) or row["job_key"]
            self.connection.execute(
                "UPDATE jobs SET canonical_key = ? WHERE job_key = ?",
                (canonical, row["job_key"]),
            )
        self.connection.commit()

    def mark_seen(self, match: Match) -> bool:
        job = match.job
        canonical = canonical_job_url(job.url) or job.key
        row = self.connection.execute(
            """
            SELECT job_key, score, location
            FROM jobs WHERE canonical_key = ? OR job_key = ? LIMIT 1
            """,
            (canonical, job.key),
        ).fetchone()
        if row:
            if row["score"] == 0 or not row["location"]:
                self.connection.execute(
                    """
                    UPDATE jobs
                    SET title = ?, company = ?, location = ?, score = ?, reasons = ?
                    WHERE job_key = ?
                    """,
                    (
                        job.title,
                        job.company,
                        job.location,
                        match.score,
                        json.dumps(match.reasons),
                        row["job_key"],
                    ),
                )
                self.connection.commit()
            return False
        self.connection.execute(
            """
            INSERT INTO jobs
                (job_key, canonical_key, source, title, company, location, url, score, reasons)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.key,
                canonical,
                job.source,
                job.title,
                job.company,
                job.location,
                job.url,
                match.score,
                json.dumps(match.reasons),
            ),
        )
        self.connection.commit()
        return True

    def all_matches(self) -> list[Match]:
        rows = self.connection.execute(
            """
            SELECT canonical_key, source, job_key, title, company, location, url,
                   score, reasons, first_seen
            FROM jobs
            ORDER BY first_seen DESC, score DESC
            """
        ).fetchall()
        matches: list[Match] = []
        seen: set[str] = set()
        for row in rows:
            identity = row["canonical_key"] or row["job_key"]
            if identity in seen:
                continue
            seen.add(identity)
            matches.append(
                Match(
                job=Job(
                    source=row["source"],
                    external_id=row["job_key"],
                    title=row["title"],
                    company=row["company"],
                    location=row["location"],
                    url=row["url"],
                ),
                score=row["score"],
                reasons=tuple(json.loads(row["reasons"] or "[]")),
                discovered_at=row["first_seen"],
            )
            )
        return matches

    def close(self) -> None:
        self.connection.close()
