"""Synchronous, low-frequency HTTP client with Phase 3A safety controls."""

from __future__ import annotations

import ipaddress
import json
import socket
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Mapping
from urllib.parse import urljoin, urlsplit


USER_AGENT = "RoboMatrix-Career-Source-Verification/1.0 (low-frequency; public recruitment pages only)"
ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/ld+json",
    "text/html",
    "text/plain",
}
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class HttpClientError(RuntimeError):
    """Base error for safe HTTP verification."""


class SsrfProtectionError(HttpClientError):
    pass


class AccessBlockedError(HttpClientError):
    pass


class AccessBarrierError(HttpClientError):
    pass


class NotFoundError(HttpClientError):
    pass


class RateLimitedError(HttpClientError):
    def __init__(self, message: str, retry_after: str | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ResponseTooLargeError(HttpClientError):
    pass


class ContentTypeError(HttpClientError):
    pass


@dataclass(frozen=True)
class RawHttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


@dataclass(frozen=True)
class HttpPage:
    requested_url: str
    final_url: str
    redirect_chain: list[str]
    fetched_at: str
    http_status: int
    content_type: str
    body: bytes
    etag: str | None = None
    last_modified: str | None = None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):  # type: ignore[no-untyped-def]
        return None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _header(headers: Mapping[str, str], name: str) -> str | None:
    """Read an HTTP header without relying on a server's capitalization."""

    expected = name.casefold()
    for key, value in headers.items():
        if key.casefold() == expected:
            return value
    return None


def _default_resolver(hostname: str) -> list[str]:
    addresses = {
        item[4][0]
        for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    }
    return sorted(addresses)


def _is_allowed_host(hostname: str, allowed_domains: list[str]) -> bool:
    normalized = hostname.rstrip(".").encode("idna").decode("ascii").lower()
    return any(
        normalized == allowed.rstrip(".").encode("idna").decode("ascii").lower()
        or normalized.endswith(f".{allowed.rstrip('.').encode('idna').decode('ascii').lower()}")
        for allowed in allowed_domains
    )


def validate_public_target(
    url: str,
    allowed_domains: list[str],
    resolver: Callable[[str], list[str]] = _default_resolver,
) -> None:
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise SsrfProtectionError("Only HTTP(S) URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise SsrfProtectionError("Credentials in URLs are forbidden")
    if not parsed.hostname:
        raise SsrfProtectionError("URL hostname is required")
    if not _is_allowed_host(parsed.hostname, allowed_domains):
        raise SsrfProtectionError(f"Hostname is outside the configured allowlist: {parsed.hostname}")
    try:
        addresses = resolver(parsed.hostname)
    except OSError as error:
        raise HttpClientError(f"DNS resolution failed for {parsed.hostname}") from error
    if not addresses:
        raise HttpClientError(f"DNS resolution returned no addresses for {parsed.hostname}")
    for address in addresses:
        try:
            parsed_address = ipaddress.ip_address(address)
        except ValueError as error:
            raise SsrfProtectionError(f"Resolver returned an invalid address: {address}") from error
        if not parsed_address.is_global:
            raise SsrfProtectionError(f"Non-public network address is forbidden: {address}")


def detect_access_barrier(content_type: str, body: bytes, final_url: str) -> str | None:
    if not (content_type.startswith("text/") or "json" in content_type):
        return None
    sample = body[:262144].decode("utf-8", errors="ignore").lower()
    if "json" in content_type:
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        else:
            if isinstance(payload, dict):
                sample = " ".join(
                    str(payload[key])
                    for key in ("error", "message", "detail", "error_description")
                    if payload.get(key) is not None
                ).lower()
    final_path = urlsplit(final_url).path.lower()
    signals = {
        "captcha": ("captcha", "hcaptcha", "recaptcha"),
        "human_verification": ("verify you are human", "are you a human", "challenge-platform"),
        "login": ("sign in", "log in", "login required", "authentication required"),
    }
    if any(token in final_path for token in ("/login", "/signin", "/auth/")):
        return "login"
    for barrier, tokens in signals.items():
        if any(token in sample for token in tokens):
            return barrier
    return None


class SafeHttpClient:
    """One-request-at-a-time client; redirects and every DNS target are revalidated."""

    def __init__(
        self,
        *,
        resolver: Callable[[str], list[str]] = _default_resolver,
        request_once: Callable[[str, Mapping[str, str], float, int], RawHttpResponse] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        max_redirects: int = 3,
        max_response_bytes: int = 2_000_000,
        max_server_retries: int = 1,
    ) -> None:
        self.resolver = resolver
        self.request_once = request_once or self._default_request_once
        self.sleep = sleep
        self.monotonic = monotonic
        self.max_redirects = max_redirects
        self.max_response_bytes = max_response_bytes
        self.max_server_retries = max_server_retries
        self._last_request_at: dict[str, float] = {}

    def _default_request_once(
        self,
        url: str,
        headers: Mapping[str, str],
        timeout: float,
        max_response_bytes: int,
    ) -> RawHttpResponse:
        request = urllib.request.Request(url, headers=dict(headers), method="GET")
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
            _NoRedirect(),
        )
        try:
            response = opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as error:
            response = error
        content_length = _header(response.headers, "Content-Length")
        if content_length and int(content_length) > max_response_bytes:
            response.close()
            raise ResponseTooLargeError("Response exceeds the configured size limit")
        body = response.read(max_response_bytes + 1)
        status = response.status
        headers_result = {key: value for key, value in response.headers.items()}
        response.close()
        if len(body) > max_response_bytes:
            raise ResponseTooLargeError("Response exceeds the configured size limit")
        return RawHttpResponse(status=status, headers=headers_result, body=body)

    def _wait_for_interval(self, hostname: str, request_interval_seconds: float) -> None:
        if request_interval_seconds < 3.0:
            raise HttpClientError("Request interval must be at least 3 seconds")
        now = self.monotonic()
        previous = self._last_request_at.get(hostname)
        if previous is not None:
            remaining = request_interval_seconds - (now - previous)
            if remaining > 0:
                self.sleep(remaining)
        self._last_request_at[hostname] = self.monotonic()

    def fetch(
        self,
        url: str,
        *,
        allowed_domains: list[str],
        request_interval_seconds: float = 3.0,
        timeout_seconds: float = 15.0,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> HttpPage:
        requested_url = url
        current_url = url
        redirect_chain: list[str] = []
        server_attempts = 0
        headers = {
            "Accept": "text/html, application/json;q=0.9, text/plain;q=0.5",
            "User-Agent": USER_AGENT,
        }
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        while True:
            validate_public_target(current_url, allowed_domains, self.resolver)
            hostname = urlsplit(current_url).hostname
            assert hostname is not None
            self._wait_for_interval(hostname, request_interval_seconds)
            response = self.request_once(current_url, headers, timeout_seconds, self.max_response_bytes)
            status = response.status
            if status in REDIRECT_STATUSES:
                location = _header(response.headers, "Location")
                if not location:
                    raise HttpClientError("Redirect response is missing Location")
                if len(redirect_chain) >= self.max_redirects:
                    raise HttpClientError("Redirect limit exceeded")
                redirect_chain.append(current_url)
                current_url = urljoin(current_url, location)
                continue
            if status == 401:
                raise AccessBlockedError("HTTP 401 requires authentication")
            if status == 403:
                raise AccessBlockedError("HTTP 403 blocks access")
            if status == 404:
                raise NotFoundError("HTTP 404 page not found")
            if status == 429:
                raise RateLimitedError(
                    "HTTP 429 rate limited", _header(response.headers, "Retry-After")
                )
            if 500 <= status <= 599:
                if server_attempts >= self.max_server_retries:
                    raise HttpClientError(f"HTTP {status} after bounded retry")
                server_attempts += 1
                self.sleep(float(server_attempts))
                continue
            if not (200 <= status <= 299 or status == 304):
                raise HttpClientError(f"Unexpected HTTP status: {status}")
            raw_content_type = (
                (_header(response.headers, "Content-Type") or "")
                .split(";", 1)[0]
                .strip()
                .lower()
            )
            if status != 304 and raw_content_type not in ALLOWED_CONTENT_TYPES:
                raise ContentTypeError(f"Unsupported content type: {raw_content_type or 'missing'}")
            barrier = detect_access_barrier(raw_content_type, response.body, current_url)
            if barrier:
                raise AccessBarrierError(f"Access barrier detected: {barrier}")
            return HttpPage(
                requested_url=requested_url,
                final_url=current_url,
                redirect_chain=redirect_chain,
                fetched_at=_utc_now(),
                http_status=status,
                content_type=raw_content_type,
                body=response.body,
                etag=_header(response.headers, "ETag"),
                last_modified=_header(response.headers, "Last-Modified"),
            )
