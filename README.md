# Scout X5

Scout X5 checks public job sources on a schedule, ranks new postings against a
configurable profile, remembers what it has already seen, and opens a GitHub Issue
when it finds new matches.

The default profile is intentionally broad: general software engineering roles are
eligible, while systems, firmware, embedded, networking, Linux, C/C++, Python,
robotics, and hardware experience improve the ranking. A resume is **not** stored in
this public repository.

## What works today

- Public Greenhouse Job Board API sources
- Public Lever Postings API sources
- Structured JSON job feeds
- Community GitHub Markdown job lists
- Deterministic, explainable 0-100 scoring
- Cross-source URL canonicalization and SQLite deduplication
- Per-day reports and an expanding all-time job index
- 30-minute GitHub Actions scans and new-job-only GitHub Issue alerts
- Failure isolation: one broken board does not stop the others

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
scout-x5
```

The most recent non-empty batch is written to `data/latest.md`. Dated reports live
in `data/daily/`, the expanding index is `data/all-jobs.md`, and seen-job history is
kept in `data/scout.db`. Delete the database only when you intentionally want every
current posting to be treated as new again.

## Configure matching

Edit [`config/profile.yml`](config/profile.yml):

- `broad_roles` controls which job titles receive the baseline score.
- `resume_boosts` improves relevant roles but never acts as a requirement.
- `early_career_terms` boosts internships and new-grad positions.
- `seniority_penalties` lowers roles unlikely to fit a student or new graduate.
- `exclude` is reserved for true deal-breakers.
- `minimum_score` controls alert sensitivity.

The matcher is keyword-based and explainable. It does not send resume text or job
descriptions to an external AI service.

## Add sources

Edit [`config/sources.yml`](config/sources.yml). For a Greenhouse careers URL such
as `https://boards.greenhouse.io/acme`, use `acme` as `board`. For a Lever URL such
as `https://jobs.lever.co/acme`, use `acme` as `site`.

```yaml
- type: greenhouse
  name: Acme
  board: acme

- type: lever
  name: Example Corp
  site: example-corp

- type: github_markdown
  name: Community List
  url: https://raw.githubusercontent.com/owner/repo/main/README.md

- type: json_api
  name: Structured Feed
  url: https://example.com/jobs.json
```

Use documented public APIs where possible. Before adding arbitrary scraping, review
the site's terms, robots policy, and rate limits.

## Notifications and scheduling

The workflow runs at minutes 17 and 47 of every hour and can also be started from
the Actions tab. It opens an assigned Issue labeled `job-alert` only when it finds
previously unseen matches. Empty scans produce no issue and no repository commit.

Each successful discovery batch immediately updates the current date's report.
After local midnight in the configured reporting timezone, that dated file naturally
stops changing and the next day's file begins. Every match is also retained in the
all-time index.

To receive alerts, enable **On GitHub** and **Email** in GitHub notification settings,
then watch this repository. GitHub Mobile can turn the same assigned issue into a
phone push; without GitHub Mobile, your phone's existing mail app can display the
email notification. No job database or resume is downloaded to the phone.

Scheduled Actions may run a few minutes late during busy periods. Public-repository
schedules can be disabled by GitHub after 60 days with no repository activity; the
scanner's state commits normally keep this repository active while jobs are opening.

## Development

```bash
python -m pip install -e '.[dev]'
ruff check .
pytest
```

## Roadmap

- Ashby adapter
- Optional email, Slack, Discord, and Telegram notifiers
- Company/source health dashboard
- Location and work-authorization rules
- Compensation extraction
- Optional semantic ranking behind a feature flag

## Privacy and safety

Do not commit resumes, contact details, passwords, or tokens. Put notification
credentials in GitHub Actions secrets. Scout X5 discovers roles; it never applies to
jobs automatically.
