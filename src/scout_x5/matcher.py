from __future__ import annotations

import re

from .models import Job, Match


def _contains(text: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase.lower())}(?!\w)", text) is not None


def score(job: Job, profile: dict) -> Match:
    title = job.title.lower()
    text = f"{job.title} {job.description} {job.location}".lower()
    points = 0
    reasons: list[str] = []

    excluded = [x.lower() for x in profile.get("exclude", [])]
    if any(_contains(text, term) for term in excluded):
        return Match(job=job, score=0, reasons=("excluded keyword",))

    role_hits = [term for term in profile.get("broad_roles", []) if _contains(title, term)]
    if role_hits:
        points += min(45, 25 + 5 * len(role_hits))
        reasons.append(f"SWE role: {', '.join(role_hits[:3])}")

    boost_hits = [term for term in profile.get("resume_boosts", []) if _contains(text, term)]
    if boost_hits:
        points += min(30, 4 * len(boost_hits))
        reasons.append(f"profile overlap: {', '.join(boost_hits[:5])}")

    early_hits = [term for term in profile.get("early_career_terms", []) if _contains(text, term)]
    if early_hits:
        points += 20
        reasons.append(f"early career: {', '.join(early_hits[:3])}")

    location_hits = [term for term in profile.get("locations", []) if term.lower() in text]
    if location_hits:
        points += 10
        reasons.append(f"location: {', '.join(location_hits[:2])}")

    penalty_hits = [
        term for term in profile.get("seniority_penalties", []) if _contains(title, term)
    ]
    if penalty_hits:
        points -= 35
        reasons.append(f"seniority penalty: {', '.join(penalty_hits[:2])}")

    return Match(job=job, score=max(0, min(100, points)), reasons=tuple(reasons))
