#!/usr/bin/env python3
"""CLI for Phase 3A recruitment-source registration and bounded dry-runs."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import career_db
from career_sources.adapters import ADAPTERS, AdapterError
from career_sources.http_client import HttpClientError
from career_sources.service import (
    SourceServiceError,
    dry_run,
    list_sources,
    register_company,
    register_source,
    verify_source,
)
from career_sources.staging import StagingError


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 3A official recruitment source verification CLI."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    company = commands.add_parser("register-company", help="Register a candidate company")
    company.add_argument("--db", required=True)
    company.add_argument("--company-id", required=True)
    company.add_argument("--display-name", required=True)
    company.add_argument("--official-website-url", required=True)
    company.add_argument("--official-career-url", required=True)

    source = commands.add_parser("register", help="Register a disabled candidate source")
    source.add_argument("--db", required=True)
    source.add_argument("--source-id", required=True)
    source.add_argument("--company-id", required=True)
    source.add_argument("--source-name", required=True)
    source.add_argument("--official-careers-url", required=True)
    source.add_argument("--listing-url", required=True)
    source.add_argument(
        "--source-type",
        required=True,
        choices=("official_html", "standard_ats", "official_json"),
    )
    source.add_argument("--ats-vendor")
    source.add_argument("--allowed-domain", action="append", required=True)
    source.add_argument("--adapter-name", choices=sorted(ADAPTERS), required=True)
    source.add_argument(
        "--external-id-strategy",
        choices=("native_job_id", "normalized_detail_url", "review_required"),
        required=True,
    )
    source.add_argument("--owner", required=True)
    source.add_argument("--official-evidence-url")
    source.add_argument("--evidence-checked", action="store_true")
    source.add_argument(
        "--robots-status",
        choices=("not_checked", "allowed", "disallowed", "not_found", "unclear"),
        default="not_checked",
    )
    source.add_argument(
        "--terms-status",
        choices=("not_checked", "reviewed_no_obvious_restriction", "restricted", "unclear"),
        default="not_checked",
    )
    source.add_argument("--login-required", action="store_true")
    source.add_argument("--captcha-detected", action="store_true")
    source.add_argument("--notes")

    listing = commands.add_parser("list", help="List registered sources and disabled controls")
    listing.add_argument("--db", required=True)

    run = commands.add_parser("dry-run", help="Run fixture or explicitly confirmed live smoke")
    run.add_argument("--db", required=True)
    run.add_argument("--staging-dir", required=True)
    run.add_argument("--source-id", required=True)
    run.add_argument("--mode", required=True, choices=("fixture", "live-smoke"))
    run.add_argument("--confirm-live", action="store_true")

    verify = commands.add_parser("verify", help="Manually mark a fully checked source verified")
    verify.add_argument("--db", required=True)
    verify.add_argument("--source-id", required=True)
    verify.add_argument("--actor", required=True)
    verify.add_argument("--confirm", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "register-company":
            result = register_company(
                args.db,
                company_id=args.company_id,
                display_name=args.display_name,
                official_website_url=args.official_website_url,
                official_career_url=args.official_career_url,
            )
        elif args.command == "register":
            result = register_source(
                args.db,
                source_id=args.source_id,
                company_id=args.company_id,
                source_name=args.source_name,
                official_careers_url=args.official_careers_url,
                listing_url=args.listing_url,
                source_type=args.source_type,
                ats_vendor=args.ats_vendor,
                allowed_domains=args.allowed_domain,
                adapter_name=args.adapter_name,
                external_id_strategy=args.external_id_strategy,
                owner=args.owner,
                official_evidence_url=args.official_evidence_url,
                evidence_checked=args.evidence_checked,
                robots_status=args.robots_status,
                terms_status=args.terms_status,
                login_required=args.login_required,
                captcha_detected=args.captcha_detected,
                notes=args.notes,
            )
        elif args.command == "list":
            result = list_sources(args.db)
        elif args.command == "dry-run":
            result = dry_run(
                args.db,
                args.staging_dir,
                source_id=args.source_id,
                mode=args.mode,
                confirm_live=args.confirm_live,
            )
        elif args.command == "verify":
            result = verify_source(
                args.db,
                source_id=args.source_id,
                actor=args.actor,
                confirm=args.confirm,
            )
        else:  # pragma: no cover - argparse enforces the command.
            raise AssertionError(args.command)
        _print_json(result)
        return 0
    except (
        AdapterError,
        career_db.CareerDataError,
        HttpClientError,
        SourceServiceError,
        StagingError,
        ValueError,
    ) as error:
        print(f"career-sources: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
