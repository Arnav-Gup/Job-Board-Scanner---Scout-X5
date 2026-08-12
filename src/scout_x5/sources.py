from __future__ import annotations

import re
from abc import ABC, abstractmethod
from html import unescape
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .models import Job


class Source(ABC):
    def __init__(self, name: str, client: httpx.Client) -> None:
        self.name = name
        self.client = client

    @abstractmethod
    def fetch(self) -> list[Job]: ...


def plain_text(value: str | None) -> str:
    return BeautifulSoup(unescape(value or ""), "html.parser").get_text(" ", strip=True)


class GreenhouseSource(Source):
    def __init__(self, name: str, board: str, client: httpx.Client) -> None:
        super().__init__(name, client)
        self.board = board

    def fetch(self) -> list[Job]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.board}/jobs"
        response = self.client.get(url, params={"content": "true"})
        response.raise_for_status()
        return [
            Job(
                source=self.name,
                external_id=str(item["id"]),
                title=item.get("title", "Untitled"),
                company=self.name,
                location=item.get("location", {}).get("name", "Unspecified"),
                url=item.get("absolute_url", ""),
                description=plain_text(item.get("content")),
                updated_at=item.get("updated_at", ""),
            )
            for item in response.json().get("jobs", [])
        ]


class LeverSource(Source):
    def __init__(self, name: str, site: str, client: httpx.Client, region: str = "global") -> None:
        super().__init__(name, client)
        self.site = site
        self.region = region

    def fetch(self) -> list[Job]:
        host = "api.eu.lever.co" if self.region == "eu" else "api.lever.co"
        response = self.client.get(
            f"https://{host}/v0/postings/{self.site}", params={"mode": "json"}
        )
        response.raise_for_status()
        jobs = []
        for item in response.json():
            categories = item.get("categories") or {}
            description = " ".join(
                filter(
                    None,
                    [
                        item.get("descriptionPlain"),
                        plain_text(item.get("additionalPlain")),
                        " ".join(plain_text(x.get("content")) for x in item.get("lists", [])),
                    ],
                )
            )
            jobs.append(
                Job(
                    source=self.name,
                    external_id=str(item.get("id", item.get("hostedUrl", ""))),
                    title=item.get("text", "Untitled"),
                    company=self.name,
                    location=categories.get("location", "Unspecified"),
                    url=item.get("hostedUrl", ""),
                    description=description,
                    updated_at=str(item.get("createdAt", "")),
                )
            )
        return jobs


class JsonApiSource(Source):
    def __init__(self, name: str, url: str, client: httpx.Client) -> None:
        super().__init__(name, client)
        self.url = url

    def fetch(self) -> list[Job]:
        response = self.client.get(self.url)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("jobs", payload) if isinstance(payload, dict) else payload
        jobs: list[Job] = []
        for item in items:
            details = " ".join(
                str(value)
                for value in (
                    item.get("category"),
                    item.get("season"),
                    item.get("sponsorship"),
                    item.get("salary"),
                    " ".join(item.get("skills") or []),
                )
                if value
            )
            jobs.append(
                Job(
                    source=self.name,
                    external_id=str(item.get("id", item.get("url", ""))),
                    title=item.get("title", "Untitled"),
                    company=item.get("company", self.name),
                    location=item.get("location", "Unspecified"),
                    url=item.get("url", ""),
                    description=details,
                    updated_at=item.get("posted_at", item.get("first_seen_at", "")),
                )
            )
        return jobs


MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")


class GithubMarkdownSource(Source):
    def __init__(self, name: str, url: str, client: httpx.Client) -> None:
        super().__init__(name, client)
        self.url = url

    def fetch(self) -> list[Job]:
        response = self.client.get(self.url)
        response.raise_for_status()
        jobs = self._html_table_jobs(response.text)
        if jobs:
            return jobs

        jobs = self._markdown_table_jobs(response.text)
        if jobs:
            return jobs

        jobs = []
        seen: set[str] = set()
        for label, url in MARKDOWN_LINK.findall(response.text):
            clean_url = url.replace("&amp;", "&")
            if clean_url in seen or not _looks_like_job_link(label, clean_url):
                continue
            seen.add(clean_url)
            host = urlparse(clean_url).netloc.removeprefix("www.")
            jobs.append(
                Job(
                    source=self.name,
                    external_id=clean_url,
                    title=plain_text(label),
                    company=host,
                    location="See posting",
                    url=clean_url,
                    description=f"Listing from {self.name}: {plain_text(label)}",
                )
            )
        return jobs

    def _markdown_table_jobs(self, content: str) -> list[Job]:
        jobs: list[Job] = []
        last_company = self.name
        for line in content.splitlines():
            if not line.startswith("|") or "<a " not in line.lower():
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 4 or "<s>" in line.lower() or "<del>" in line.lower():
                continue
            company = plain_text(cells[0])
            if company and company != "↳":
                last_company = company
            title = plain_text(cells[1])
            location = plain_text(cells[2].replace("</br>", "<br>"))
            application = BeautifulSoup(cells[3], "html.parser")
            apply_link = next(
                (
                    link.get("href")
                    for link in application.find_all("a", href=True)
                    if link.find("img", alt=re.compile("apply", re.I))
                ),
                None,
            )
            if not apply_link or not title:
                continue
            jobs.append(
                Job(
                    source=self.name,
                    external_id=apply_link,
                    title=title,
                    company=last_company,
                    location=location or "Unspecified",
                    url=apply_link,
                    description=f"{title} at {last_company} in {location}",
                )
            )
        return jobs

    def _html_table_jobs(self, content: str) -> list[Job]:
        soup = BeautifulSoup(content, "html.parser")
        jobs: list[Job] = []
        last_company = self.name
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 4 or row.find(["s", "del"]):
                continue
            company = cells[0].get_text(" ", strip=True)
            if company and company != "↳":
                last_company = company
            title = cells[1].get_text(" ", strip=True)
            location = cells[2].get_text(" ", strip=True)
            apply_link = next(
                (
                    link.get("href")
                    for link in cells[3].find_all("a", href=True)
                    if link.find("img", alt=re.compile("apply", re.I))
                ),
                None,
            )
            if not apply_link or not title:
                continue
            jobs.append(
                Job(
                    source=self.name,
                    external_id=apply_link,
                    title=title,
                    company=last_company,
                    location=location or "Unspecified",
                    url=apply_link,
                    description=f"{title} at {last_company} in {location}",
                )
            )
        return jobs


def _looks_like_job_link(label: str, url: str) -> bool:
    haystack = f"{label} {url}".lower()
    ignored = ("linkedin.com/company", "github.com/sponsors", "discord.gg", "mailto:")
    job_signals = ("job", "career", "apply", "greenhouse", "lever.co", "ashbyhq")
    return not any(x in haystack for x in ignored) and any(x in haystack for x in job_signals)


def build_sources(config: dict, client: httpx.Client) -> list[Source]:
    sources: list[Source] = []
    for item in config.get("sources", []):
        if not item.get("enabled", True):
            continue
        kind = item["type"]
        if kind == "greenhouse":
            sources.append(GreenhouseSource(item["name"], item["board"], client))
        elif kind == "lever":
            sources.append(
                LeverSource(item["name"], item["site"], client, item.get("region", "global"))
            )
        elif kind == "github_markdown":
            sources.append(GithubMarkdownSource(item["name"], item["url"], client))
        elif kind == "json_api":
            sources.append(JsonApiSource(item["name"], item["url"], client))
        else:
            raise ValueError(f"Unsupported source type: {kind}")
    return sources
