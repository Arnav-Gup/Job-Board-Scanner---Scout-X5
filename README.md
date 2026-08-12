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
- Community GitHub Markdown job lists
- Deterministic, explainable 0-100 scoring
- SQLite deduplication across runs
- Markdown scan reports
- Daily GitHub Actions scans and GitHub Issue alerts
- Failure isolation: one broken board does not stop the others

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
scout-x5
```

Results are written to `data/latest.md`; seen-job history is kept in
`data/scout.db`. Delete the database only when you intentionally want every current
posting to be treated as new again.

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
```

Use documented public APIs where possible. Before adding arbitrary scraping, review
the site's terms, robots policy, and rate limits.

## Notifications and scheduling

The workflow runs once daily and can also be started from the Actions tab. When
matches are found, it opens an Issue labeled `job-alert`. Watch the repository or
enable GitHub email/mobile notifications to receive alerts.

GitHub schedules use UTC and may run later than the exact cron minute during busy
periods. Change `.github/workflows/scan.yml` to adjust frequency.

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
