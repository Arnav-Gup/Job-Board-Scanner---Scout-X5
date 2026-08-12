from pathlib import Path

from scout_x5.models import Job, Match
from scout_x5.report import write_collections


def test_collections_create_dated_and_all_time_reports(tmp_path: Path) -> None:
    match = Match(
        Job(
            "List",
            "42",
            "Software Engineer Intern",
            "Acme",
            "Remote",
            "https://jobs.example/42",
        ),
        60,
        ("SWE role",),
        "2026-08-13T06:30:00+00:00",
    )

    write_collections(tmp_path / "daily", tmp_path / "all.md", [match], "America/Los_Angeles")

    daily = (tmp_path / "daily" / "2026-08-12.md").read_text()
    overall = (tmp_path / "all.md").read_text()
    assert "Scout X5 jobs for August 12, 2026" in daily
    assert "Software Engineer Intern" in daily
    assert "Scout X5 all-time matching jobs" in overall
