"""Controlled Phase 3A recruitment-source verification helpers."""

from .adapters import (
    AdapterError,
    BaseSourceAdapter,
    IdentityError,
    SchemaDriftError,
    adapter_for_source,
)
from .http_client import (
    AccessBlockedError,
    AccessBarrierError,
    ContentTypeError,
    HttpClientError,
    HttpPage,
    NotFoundError,
    RateLimitedError,
    ResponseTooLargeError,
    SafeHttpClient,
    SsrfProtectionError,
)
from .models import StagingJob, build_job_key, normalize_detail_url
from .service import SourceServiceError, dry_run, register_company, register_source, verify_source
from .staging import StagingError, StagingRunWriter

__all__ = [
    "AccessBarrierError",
    "AccessBlockedError",
    "AdapterError",
    "BaseSourceAdapter",
    "ContentTypeError",
    "HttpClientError",
    "HttpPage",
    "IdentityError",
    "NotFoundError",
    "RateLimitedError",
    "ResponseTooLargeError",
    "SafeHttpClient",
    "SchemaDriftError",
    "SourceServiceError",
    "SsrfProtectionError",
    "StagingJob",
    "StagingError",
    "StagingRunWriter",
    "adapter_for_source",
    "build_job_key",
    "dry_run",
    "normalize_detail_url",
    "register_company",
    "register_source",
    "verify_source",
]
