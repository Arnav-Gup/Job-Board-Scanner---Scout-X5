from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .models import Match


def markdown(matches: list[Match], errors: list[str]) -> str:
    date = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Scout X5 matches - {date}", ""]
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
