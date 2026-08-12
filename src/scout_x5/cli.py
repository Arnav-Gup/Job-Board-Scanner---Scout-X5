from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import httpx
import yaml

from .matcher import score
from .report import markdown, write_collections, write_report
from .sources import build_sources
from .store import Store


def load_yaml(path: str) -> dict:
    with Path(path).open(encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def scan(
    config_path: str,
    profile_path: str,
    state_path: str,
    output_path: str,
    daily_directory: str,
    overall_path: str,
) -> int:
    config = load_yaml(config_path)
    profile = load_yaml(profile_path)
    minimum = int(profile.get("minimum_score", 40))
    maximum = int(config.get("max_alerts_per_run", 25))
    notification = config.get("notifications", {})
    username = notification.get("github_username", "")
    timezone_name = config.get("reporting_timezone", "America/Los_Angeles")
    errors: list[str] = []
    matches = []
    store = Store(state_path)
    try:
        headers = {"User-Agent": "Scout-X5/0.1 (+https://github.com/Arnav-Gup)"}
        with httpx.Client(headers=headers, timeout=30, follow_redirects=True) as client:
            for source in build_sources(config, client):
                try:
                    for job in source.fetch():
                        match = score(job, profile)
                        if match.score >= minimum and store.mark_seen(match):
                            matches.append(match)
                except (httpx.HTTPError, ValueError, KeyError) as exc:
                    errors.append(f"{source.name}: {exc}")
        all_matches = store.all_matches()
    finally:
        store.close()

    new_count = len(matches)
    shown_matches = sorted(matches, key=lambda item: item.score, reverse=True)[:maximum]
    content = markdown(shown_matches, errors, username if matches else "")
    if new_count > len(shown_matches):
        content += (
            f"\nShowing the top {len(shown_matches)} of {new_count} new matches. "
            "The complete set is in today's dated report.\n"
        )
    print(content)
    if matches:
        write_report(output_path, content)
        write_collections(daily_directory, overall_path, all_matches, timezone_name)
        _notify_github(output_path, new_count, username)
    return 0


def _notify_github(report_path: str, count: int, username: str) -> None:
    if os.environ.get("SCOUT_GITHUB_ISSUES") != "1" or not os.environ.get("GITHUB_REPOSITORY"):
        return
    command = [
        "gh",
        "issue",
        "create",
        "--repo",
        os.environ["GITHUB_REPOSITORY"],
        "--title",
        f"Scout X5 found {count} new job match{'es' if count != 1 else ''}",
        "--body-file",
        report_path,
        "--label",
        "job-alert",
    ]
    if username:
        command.extend(["--assignee", username])
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan configured boards for new job matches")
    parser.add_argument("--config", default="config/sources.yml")
    parser.add_argument("--profile", default="config/profile.yml")
    parser.add_argument("--state", default="data/scout.db")
    parser.add_argument("--output", default="data/latest.md")
    parser.add_argument("--daily-directory", default="data/daily")
    parser.add_argument("--overall", default="data/all-jobs.md")
    args = parser.parse_args()
    sys.exit(
        scan(
            args.config,
            args.profile,
            args.state,
            args.output,
            args.daily_directory,
            args.overall,
        )
    )


if __name__ == "__main__":
    main()
