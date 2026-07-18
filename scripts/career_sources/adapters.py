"""Small, versioned adapters used by Phase 3A source verification."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

from .http_client import HttpPage, SafeHttpClient
from .models import (
    StagingJob,
    build_job_key,
    job_content_hash,
    normalize_detail_url,
    normalized_strings,
    plain_text,
)


class AdapterError(RuntimeError):
    pass


class SchemaDriftError(AdapterError):
    pass


class IdentityError(AdapterError):
    pass


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_named(values: Any) -> str | None:
    if not isinstance(values, list):
        return None
    for value in values:
        if isinstance(value, dict) and _optional_string(value.get("name")):
            return _optional_string(value["name"])
    return None


class BaseSourceAdapter(ABC):
    adapter_name: str
    adapter_version = "1.0.0"
    parser_version = "1.0.0"
    source_type: str

    def validate_source_config(self, source: dict[str, Any]) -> None:
        if source["source_type"] != self.source_type:
            raise AdapterError(
                f"Adapter {self.adapter_name} requires source_type={self.source_type}"
            )
        if source["adapter_name"] != self.adapter_name:
            raise AdapterError("Source adapter_name does not match the selected adapter")
        if source["adapter_version"] != self.adapter_version:
            raise AdapterError("Source adapter_version does not match repository code")
        if source["parser_version"] != self.parser_version:
            raise AdapterError("Source parser_version does not match repository code")

    def fetch_listing(self, client: SafeHttpClient, source: dict[str, Any]) -> HttpPage:
        return client.fetch(
            source["listing_url"],
            allowed_domains=source["allowed_domains"],
            request_interval_seconds=source["request_interval_seconds"],
            timeout_seconds=source["timeout_seconds"],
        )

    @abstractmethod
    def parse_listing(self, page: HttpPage, source: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    def extract_detail_links(self, listing: list[dict[str, Any]]) -> list[str]:
        links = [item.get("request_url") or item.get("detail_url") for item in listing]
        return [link for link in links if isinstance(link, str) and link]

    def fetch_detail(
        self, client: SafeHttpClient, source: dict[str, Any], url: str
    ) -> HttpPage:
        return client.fetch(
            url,
            allowed_domains=source["allowed_domains"],
            request_interval_seconds=source["request_interval_seconds"],
            timeout_seconds=source["timeout_seconds"],
        )

    @abstractmethod
    def parse_detail(
        self,
        page: HttpPage,
        listing_item: dict[str, Any],
        source: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    def extract_external_job_id(self, parsed_detail: dict[str, Any]) -> str | None:
        return _optional_string(parsed_detail.get("external_job_id"))

    def normalize_detail_url(self, url: str) -> str:
        return normalize_detail_url(url)

    def extract_canonical_url(self, parsed_detail: dict[str, Any], page: HttpPage) -> str:
        value = parsed_detail.get("canonical_url") or page.final_url
        return normalize_detail_url(str(value))

    def build_staging_record(
        self,
        source: dict[str, Any],
        listing_item: dict[str, Any],
        parsed_detail: dict[str, Any],
        detail_page: HttpPage,
    ) -> StagingJob:
        external_job_id = self.extract_external_job_id(parsed_detail)
        canonical_url = self.extract_canonical_url(parsed_detail, detail_page)
        detail_url = normalize_detail_url(
            str(listing_item.get("detail_url") or parsed_detail.get("detail_url") or canonical_url)
        )
        strategy = source["external_id_strategy"]
        if strategy == "native_job_id" and not external_job_id:
            raise IdentityError("Configured native_job_id strategy did not produce an ID")
        if strategy == "review_required":
            raise IdentityError("Source does not have a stable identity strategy")
        title = _optional_string(parsed_detail.get("title") or listing_item.get("title"))
        if not title:
            raise SchemaDriftError("Job detail did not produce a title")
        locations_value = parsed_detail.get("locations", listing_item.get("locations", []))
        if isinstance(locations_value, str):
            locations_value = [locations_value]
        locations = normalized_strings(locations_value)
        normalized = {
            "title": title,
            "location": " | ".join(locations) or None,
            "department": _optional_string(parsed_detail.get("department")),
            "employment_type": _optional_string(parsed_detail.get("employment_type")),
            "description": plain_text(_optional_string(parsed_detail.get("description"))),
            "published_at": _optional_string(parsed_detail.get("published_at")),
        }
        return StagingJob(
            source_id=source["source_id"],
            company_id=source["company_id"],
            external_job_id=external_job_id,
            job_key=build_job_key(source["source_id"], external_job_id, detail_url),
            title=title,
            location=normalized["location"],
            department=normalized["department"],
            employment_type=normalized["employment_type"],
            description=normalized["description"],
            detail_url=detail_url,
            canonical_url=canonical_url,
            published_at=normalized["published_at"],
            content_hash=job_content_hash(normalized),
            fetched_at=detail_page.fetched_at,
            requested_url=detail_page.requested_url,
            final_url=detail_page.final_url,
            identity_strategy="native_job_id" if external_job_id else "normalized_detail_url",
        )


class _OfficialHtmlListingParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.jobs: list[dict[str, Any]] = []
        self.next_url: str | None = None
        self._active: dict[str, Any] | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value for key, value in attrs}
        if tag == "a" and ("data-career-job" in values or "data-job-id" in values):
            href = values.get("href")
            if href:
                self._active = {
                    "external_job_id": values.get("data-job-id"),
                    "detail_url": urljoin(self.base_url, href),
                    "locations": [values["data-location"]] if values.get("data-location") else [],
                }
                self._text = []
        if tag == "a" and values.get("rel") == "next" and values.get("href"):
            self.next_url = urljoin(self.base_url, values["href"] or "")

    def handle_data(self, data: str) -> None:
        if self._active is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._active is not None:
            self._active["title"] = " ".join("".join(self._text).split())
            self.jobs.append(self._active)
            self._active = None
            self._text = []


class _OfficialHtmlDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, str | None] = {
            "canonical_url": None,
            "external_job_id": None,
            "location": None,
            "department": None,
            "employment_type": None,
            "published_at": None,
            "title": None,
        }
        self._h1_depth = 0
        self._description_depth = 0
        self._h1_text: list[str] = []
        self._description_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value for key, value in attrs}
        if tag == "link" and "canonical" in (values.get("rel") or "").split():
            self.values["canonical_url"] = values.get("href")
        if tag in {"main", "article"}:
            mapping = {
                "external_job_id": "data-job-id",
                "location": "data-location",
                "department": "data-department",
                "employment_type": "data-employment-type",
                "published_at": "data-published-at",
            }
            for target, attribute in mapping.items():
                self.values[target] = values.get(attribute) or self.values[target]
        if tag == "h1":
            self._h1_depth = 1
        elif self._h1_depth:
            self._h1_depth += 1
        if "data-job-description" in values:
            self._description_depth = 1
        elif self._description_depth:
            self._description_depth += 1

    def handle_data(self, data: str) -> None:
        if self._h1_depth:
            self._h1_text.append(data)
        if self._description_depth:
            self._description_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._h1_depth:
            self._h1_depth -= 1
            if not self._h1_depth:
                self.values["title"] = " ".join("".join(self._h1_text).split())
        if self._description_depth:
            self._description_depth -= 1

    @property
    def description(self) -> str | None:
        return " ".join(" ".join(self._description_text).split()) or None


class OfficialHtmlAdapter(BaseSourceAdapter):
    adapter_name = "official_html_v1"
    source_type = "official_html"

    def parse_listing(self, page: HttpPage, source: dict[str, Any]) -> list[dict[str, Any]]:
        if page.content_type != "text/html":
            raise SchemaDriftError("official_html listing is not HTML")
        parser = _OfficialHtmlListingParser(page.final_url)
        parser.feed(page.body.decode("utf-8", errors="replace"))
        if not parser.jobs:
            raise SchemaDriftError("official_html listing contains no recognized job links")
        return parser.jobs

    def parse_detail(
        self, page: HttpPage, listing_item: dict[str, Any], source: dict[str, Any]
    ) -> dict[str, Any]:
        if page.content_type != "text/html":
            raise SchemaDriftError("official_html detail is not HTML")
        parser = _OfficialHtmlDetailParser()
        parser.feed(page.body.decode("utf-8", errors="replace"))
        if not parser.values["title"]:
            raise SchemaDriftError("official_html detail is missing h1 title")
        return {
            "external_job_id": parser.values["external_job_id"] or listing_item.get("external_job_id"),
            "title": parser.values["title"],
            "locations": [parser.values["location"]] if parser.values["location"] else listing_item.get("locations", []),
            "department": parser.values["department"],
            "employment_type": parser.values["employment_type"],
            "description": parser.description,
            "published_at": parser.values["published_at"],
            "canonical_url": urljoin(page.final_url, parser.values["canonical_url"] or page.final_url),
        }


class StandardAtsAdapter(BaseSourceAdapter):
    adapter_name = "standard_ats_greenhouse_v1"
    source_type = "standard_ats"

    def validate_source_config(self, source: dict[str, Any]) -> None:
        super().validate_source_config(source)
        if str(source.get("ats_vendor", "")).lower() != "greenhouse":
            raise AdapterError("The Phase 3A standard ATS adapter supports Greenhouse only")

    def _json(self, page: HttpPage) -> dict[str, Any]:
        if page.content_type not in {"application/json", "application/ld+json"}:
            raise SchemaDriftError("standard_ats response is not JSON")
        try:
            value = json.loads(page.body)
        except json.JSONDecodeError as error:
            raise SchemaDriftError("standard_ats returned invalid JSON") from error
        if not isinstance(value, dict):
            raise SchemaDriftError("standard_ats JSON root must be an object")
        return value

    def _detail_request_url(self, page: HttpPage, job_id: str) -> str:
        parsed = urlsplit(page.final_url)
        path = parsed.path.rstrip("/")
        if not path.endswith("/jobs"):
            raise SchemaDriftError("Greenhouse listing URL must end with /jobs")
        return urlunsplit((parsed.scheme, parsed.netloc, f"{path}/{quote(job_id)}", "", ""))

    def _listing_jobs(self, page: HttpPage) -> list[dict[str, Any]]:
        jobs = self._json(page).get("jobs")
        if not isinstance(jobs, list) or not jobs:
            raise SchemaDriftError("Greenhouse listing is missing jobs")
        seen_ids: set[str] = set()
        for job in jobs:
            if not isinstance(job, dict) or job.get("id") is None or not job.get("absolute_url"):
                raise SchemaDriftError("Greenhouse job is missing id or absolute_url")
            job_id = str(job["id"])
            if job_id in seen_ids:
                raise SchemaDriftError(f"Greenhouse listing contains duplicate job id: {job_id}")
            seen_ids.add(job_id)
        return jobs

    @staticmethod
    def _employment_type(job: dict[str, Any]) -> str | None:
        metadata = job.get("metadata")
        if not isinstance(metadata, list):
            return None
        for item in metadata:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip().lower()
            if name not in {"employment type", "time type"}:
                continue
            value = item.get("value")
            return ", ".join(map(str, value)) if isinstance(value, list) else _optional_string(value)
        return None

    def parse_listing(self, page: HttpPage, source: dict[str, Any]) -> list[dict[str, Any]]:
        jobs = self._listing_jobs(page)
        parsed: list[dict[str, Any]] = []
        for job in jobs:
            job_id = str(job["id"])
            location = job.get("location", {})
            parsed.append({
                "external_job_id": job_id,
                "request_url": self._detail_request_url(page, job_id),
                "detail_url": str(job["absolute_url"]),
                "title": str(job.get("title", "")),
                "locations": [location.get("name")] if isinstance(location, dict) and location.get("name") else [],
            })
        return parsed

    def parse_complete_listing(
        self, page: HttpPage, source: dict[str, Any]
    ) -> list[StagingJob]:
        """Parse a Greenhouse ``content=true`` response without detail requests."""

        jobs = self._listing_jobs(page)
        parsed: list[StagingJob] = []
        for job in jobs:
            if not _optional_string(job.get("title")):
                raise SchemaDriftError("Greenhouse listing job is missing title")
            if not isinstance(job.get("content"), str):
                raise SchemaDriftError(
                    "Greenhouse listing is missing content; content=true is required"
                )
            job_id = str(job["id"])
            detail_url = normalize_detail_url(str(job["absolute_url"]))
            location = job.get("location", {})
            locations = (
                [str(location["name"])]
                if isinstance(location, dict) and _optional_string(location.get("name"))
                else []
            )
            normalized = {
                "title": str(job["title"]).strip(),
                "location": " | ".join(normalized_strings(locations)) or None,
                "department": _first_named(job.get("departments")),
                "employment_type": self._employment_type(job),
                "description": plain_text(str(job["content"])),
                "published_at": _optional_string(
                    job.get("published_at") or job.get("first_published")
                ),
            }
            parsed.append(
                StagingJob(
                    source_id=source["source_id"],
                    company_id=source["company_id"],
                    external_job_id=job_id,
                    job_key=build_job_key(source["source_id"], job_id, detail_url),
                    title=normalized["title"],
                    location=normalized["location"],
                    department=normalized["department"],
                    employment_type=normalized["employment_type"],
                    description=normalized["description"],
                    detail_url=detail_url,
                    canonical_url=detail_url,
                    published_at=normalized["published_at"],
                    content_hash=job_content_hash(normalized),
                    fetched_at=page.fetched_at,
                    requested_url=page.requested_url,
                    final_url=page.final_url,
                    identity_strategy="native_job_id",
                )
            )
        return parsed

    def parse_detail(
        self, page: HttpPage, listing_item: dict[str, Any], source: dict[str, Any]
    ) -> dict[str, Any]:
        job = self._json(page)
        if job.get("id") is None or not job.get("title"):
            raise SchemaDriftError("Greenhouse detail is missing id or title")
        if str(job["id"]) != str(listing_item.get("external_job_id")):
            raise IdentityError("Greenhouse listing and detail job IDs do not match")
        location = job.get("location", {})
        return {
            "external_job_id": str(job["id"]),
            "title": str(job["title"]),
            "locations": [location.get("name")] if isinstance(location, dict) and location.get("name") else listing_item.get("locations", []),
            "department": _first_named(job.get("departments")),
            "employment_type": self._employment_type(job),
            "description": job.get("content"),
            "published_at": job.get("published_at"),
            "canonical_url": job.get("absolute_url") or listing_item.get("detail_url") or page.final_url,
        }


class OfficialJsonAdapter(BaseSourceAdapter):
    adapter_name = "official_json_v1"
    source_type = "official_json"

    def _json(self, page: HttpPage) -> dict[str, Any]:
        if page.content_type not in {"application/json", "application/ld+json"}:
            raise SchemaDriftError("official_json response is not JSON")
        try:
            value = json.loads(page.body)
        except json.JSONDecodeError as error:
            raise SchemaDriftError("official_json returned invalid JSON") from error
        if not isinstance(value, dict):
            raise SchemaDriftError("official_json JSON root must be an object")
        return value

    def parse_listing(self, page: HttpPage, source: dict[str, Any]) -> list[dict[str, Any]]:
        openings = self._json(page).get("openings")
        if not isinstance(openings, list) or not openings:
            raise SchemaDriftError("official_json listing is missing openings")
        parsed: list[dict[str, Any]] = []
        for opening in openings:
            if not isinstance(opening, dict) or not opening.get("detailUrl"):
                raise SchemaDriftError("official_json opening is missing detailUrl")
            detail_url = urljoin(page.final_url, str(opening["detailUrl"]))
            parsed.append({
                "external_job_id": str(opening["jobId"]) if opening.get("jobId") is not None else None,
                "request_url": urljoin(page.final_url, str(opening.get("requestUrl") or detail_url)),
                "detail_url": detail_url,
                "title": str(opening.get("title", "")),
                "locations": opening.get("locations", []),
            })
        return parsed

    def parse_detail(
        self, page: HttpPage, listing_item: dict[str, Any], source: dict[str, Any]
    ) -> dict[str, Any]:
        value = self._json(page)
        if not value.get("title"):
            raise SchemaDriftError("official_json detail is missing title")
        return {
            "external_job_id": str(value["jobId"]) if value.get("jobId") is not None else listing_item.get("external_job_id"),
            "title": str(value["title"]),
            "locations": value.get("locations", listing_item.get("locations", [])),
            "department": value.get("department"),
            "employment_type": value.get("employmentType"),
            "description": value.get("description"),
            "published_at": value.get("publishedAt"),
            "canonical_url": value.get("canonicalUrl") or listing_item.get("detail_url") or page.final_url,
        }


ADAPTERS = {
    OfficialHtmlAdapter.adapter_name: OfficialHtmlAdapter,
    StandardAtsAdapter.adapter_name: StandardAtsAdapter,
    OfficialJsonAdapter.adapter_name: OfficialJsonAdapter,
}


def adapter_for_source(source: dict[str, Any]) -> BaseSourceAdapter:
    adapter_name = str(source.get("adapter_name", ""))
    adapter_type = ADAPTERS.get(adapter_name)
    if adapter_type is None:
        raise AdapterError(f"Unsupported adapter: {adapter_name}")
    adapter = adapter_type()
    adapter.validate_source_config(source)
    return adapter
