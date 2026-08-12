from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import Match


def markdown(matches: list[Match], errors: list[str], mention: str = "") -> str:
    date = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Scout X5 matches - {date}", ""]
    if mention:
        lines.extend([f"@{mention} new matching jobs are ready.", ""])
    if not matches:
        lines.extend(["No new matching jobs were found.", ""])
    for match in sorted(matches, key=lambda item: item.score, reverse=True):
        job = match.job
        lines.extend(
            [
                f"## [{job.title}]({job.url}) - {match.score}/100",
                "",
                f"- Company/source: {job.company} / {job.source}",
                f"- Location: {job.location}",
                f"- Why: {'; '.join(match.reasons) or 'broad match'}",
                "",
            ]
        )
    if errors:
        lines.extend(["## Source warnings", "", *[f"- {error}" for error in errors], ""])
    return "\n".join(lines)


def write_report(path: str | Path, content: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


def write_collections(
    daily_directory: str | Path,
    overall_path: str | Path,
    matches: list[Match],
    timezone_name: str,
) -> None:
    timezone = ZoneInfo(timezone_name)
    now = datetime.now(timezone)
    by_date: dict[date, list[Match]] = {}
    for match in matches:
        discovered = _parse_discovered_at(match.discovered_at).astimezone(timezone)
        by_date.setdefault(discovered.date(), []).append(match)

    daily_directory = Path(daily_directory)
    daily_directory.mkdir(parents=True, exist_ok=True)
    for discovered_date, daily_matches in by_date.items():
        title = f"Scout X5 jobs for {discovered_date:%B %d, %Y}"
        daily_updated = max(
            _parse_discovered_at(match.discovered_at).astimezone(timezone)
            for match in daily_matches
        )
        write_report(
            daily_directory / f"{discovered_date.isoformat()}.md",
            _collection_markdown(title, daily_matches, daily_updated),
        )
    write_report(
        overall_path,
        _collection_markdown("Scout X5 all-time matching jobs", matches, now),
    )


def _parse_discovered_at(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _collection_markdown(title: str, matches: list[Match], now: datetime) -> str:
    ordered = sorted(matches, key=lambda item: item.discovered_at, reverse=True)
    lines = [
        f"# {title}",
        "",
        f"Updated {now:%Y-%m-%d %H:%M %Z}. {len(ordered)} unique matching jobs.",
        "",
        "| Score | Job | Company | Location | Source | First seen |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for match in ordered:
        job = match.job
        discovered = _parse_discovered_at(match.discovered_at).astimezone(now.tzinfo)
        lines.append(
            f"| {match.score} | [{_cell(job.title)}]({job.url}) | {_cell(job.company)} | "
            f"{_cell(job.location)} | {_cell(job.source)} | {discovered:%Y-%m-%d %H:%M} |"
        )
    lines.append("")
    return "\n".join(lines)
