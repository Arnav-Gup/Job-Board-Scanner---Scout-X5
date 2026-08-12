import httpx

from scout_x5.sources import GithubMarkdownSource, GreenhouseSource, JsonApiSource, LeverSource


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_greenhouse_normalizes_jobs() -> None:
    def handler(request):
        assert request.url.params["content"] == "true"
        return httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "id": 42,
                        "title": "Software Engineer Intern",
                        "location": {"name": "Remote"},
                        "absolute_url": "https://example.com/42",
                        "content": "<p>Build <b>systems</b>.</p>",
                        "updated_at": "2026-08-01T00:00:00Z",
                    }
                ]
            },
        )

    with client(handler) as http:
        jobs = GreenhouseSource("Acme", "acme", http).fetch()
    assert jobs[0].external_id == "42"
    assert jobs[0].description == "Build systems ."


def test_lever_normalizes_jobs() -> None:
    def handler(request):
        return httpx.Response(
            200,
            json=[
                {
                    "id": "abc",
                    "text": "Backend Engineer",
                    "hostedUrl": "https://jobs.lever.co/acme/abc",
                    "categories": {"location": "California"},
                    "descriptionPlain": "Python services",
                    "createdAt": 1,
                }
            ],
        )

    with client(handler) as http:
        jobs = LeverSource("Acme", "acme", http).fetch()
    assert jobs[0].title == "Backend Engineer"
    assert jobs[0].location == "California"


def test_github_markdown_keeps_job_links_and_deduplicates() -> None:
    def handler(request):
        return httpx.Response(
            200,
            text="[Apply](https://jobs.example.com/1) [Apply](https://jobs.example.com/1) "
            "[Docs](https://example.com/docs)",
        )

    with client(handler) as http:
        jobs = GithubMarkdownSource("List", "https://raw.example/readme", http).fetch()
    assert len(jobs) == 1


def test_github_html_table_extracts_company_role_location_and_apply_url() -> None:
    table = """
    <table><tbody><tr>
      <td><strong><a href="https://company.example">Acme</a></strong></td>
      <td>Software Engineer Intern</td><td>Remote</td>
      <td><a href="https://jobs.example/42"><img alt="Apply"></a></td>
      <td>0d</td>
    </tr></tbody></table>
    """

    def handler(request):
        return httpx.Response(200, text=table)

    with client(handler) as http:
        jobs = GithubMarkdownSource("List", "https://raw.example/readme", http).fetch()
    assert len(jobs) == 1
    assert jobs[0].company == "Acme"
    assert jobs[0].title == "Software Engineer Intern"
    assert jobs[0].location == "Remote"
    assert jobs[0].url == "https://jobs.example/42"


def test_github_mixed_markdown_table_extracts_application() -> None:
    table = (
        "| Company | Role | Location | Application/Link | Date Posted |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| Acme | Firmware Engineer Intern | Remote</br>California | "
        '<a href="https://jobs.example/42?utm_source=list"><img alt="Apply"></a> | Aug 12 |'
    )

    def handler(request):
        return httpx.Response(200, text=table)

    with client(handler) as http:
        jobs = GithubMarkdownSource("List", "https://raw.example/readme", http).fetch()
    assert len(jobs) == 1
    assert jobs[0].company == "Acme"
    assert jobs[0].location == "Remote California"
    assert jobs[0].title == "Firmware Engineer Intern"


def test_json_api_normalizes_rich_job_data() -> None:
    def handler(request):
        return httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "id": "job-42",
                        "company": "Acme",
                        "title": "Firmware Engineer Intern",
                        "location": "California",
                        "url": "https://jobs.example/42",
                        "category": "Software",
                        "season": "Summer 2027",
                        "skills": ["C++", "Linux"],
                        "sponsorship": "unknown",
                        "salary": "$40/hr",
                        "posted_at": "2026-08-12T00:00:00Z",
                    }
                ]
            },
        )

    with client(handler) as http:
        jobs = JsonApiSource("Engine", "https://api.example/jobs.json", http).fetch()
    assert jobs[0].company == "Acme"
    assert "C++ Linux" in jobs[0].description
