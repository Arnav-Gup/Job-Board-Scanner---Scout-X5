from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import Job


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_key TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                url TEXT NOT NULL,
                first_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def mark_seen(self, job: Job) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM jobs WHERE job_key = ?", (job.key,)
        ).fetchone()
        if row:
            self.connection.execute(
                "UPDATE jobs SET last_seen = CURRENT_TIMESTAMP WHERE job_key = ?", (job.key,)
            )
            self.connection.commit()
            return False
        self.connection.execute(
            "INSERT INTO jobs (job_key, source, title, company, url) VALUES (?, ?, ?, ?, ?)",
            (job.key, job.source, job.title, job.company, job.url),
        )
        self.connection.commit()
        return True

    def close(self) -> None:
        self.connection.close()
