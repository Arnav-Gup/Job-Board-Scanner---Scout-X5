from pathlib import Path

from scout_x5.models import Job, Match
from scout_x5.store import Store


def match(source: str, url: str) -> Match:
    return Match(
        Job(source, url, "Software Engineer Intern", "Acme", "Remote", url),
        60,
        ("SWE role",),
    )


def test_store_deduplicates_tracking_urls_across_sources(tmp_path: Path) -> None:
    store = Store(tmp_path / "scout.db")
    try:
        assert store.mark_seen(match("List A", "https://jobs.example/42?utm_source=list"))
        assert not store.mark_seen(match("List B", "https://jobs.example/42?ref=other"))
        assert len(store.all_matches()) == 1
    finally:
        store.close()


def test_store_deduplicates_apply_suffix(tmp_path: Path) -> None:
    store = Store(tmp_path / "scout.db")
    try:
        assert store.mark_seen(match("List A", "https://jobs.lever.co/acme/42/apply"))
        assert not store.mark_seen(match("List B", "https://jobs.lever.co/acme/42"))
    finally:
        store.close()
