"""Non-overwriting, repository-external output for source dry-runs."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

import career_db

from .http_client import HttpPage
from .models import StagingJob, content_sha256


SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class StagingError(RuntimeError):
    pass


def _validate_component(value: str, label: str) -> str:
    if not SAFE_COMPONENT.fullmatch(value):
        raise StagingError(f"{label} contains unsafe path characters")
    return value


class StagingRunWriter:
    def __init__(self, staging_dir: str | Path, source_id: str, run_id: str) -> None:
        original = Path(staging_dir)
        if original.is_symlink():
            raise StagingError("Staging directory must not be a symlink")
        self.staging_root = career_db.assert_external_path(original, "Staging directory")
        self.source_id = _validate_component(source_id, "source_id")
        self.run_id = _validate_component(run_id, "run_id")
        self.staging_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self.staging_root.is_dir() or self.staging_root.is_symlink():
            raise StagingError("Staging root must be an ordinary directory")
        source_directory = self.staging_root / self.source_id
        if source_directory.is_symlink():
            raise StagingError("Staging source directory must not be a symlink")
        source_directory.mkdir(exist_ok=True, mode=0o700)
        if not source_directory.is_dir():
            raise StagingError("Staging source path must be a directory")
        self.run_directory = source_directory / self.run_id
        try:
            self.run_directory.mkdir(mode=0o700)
        except FileExistsError as error:
            raise StagingError(f"Staging run already exists: {self.run_directory}") from error
        self.pages: list[dict[str, Any]] = []

    def _write_bytes(self, filename: str, content: bytes) -> Path:
        path = self.run_directory / filename
        try:
            with path.open("xb") as output:
                output.write(content)
        except FileExistsError as error:
            raise StagingError(f"Staging file already exists: {path}") from error
        os.chmod(path, 0o600)
        return path

    def _write_json(self, filename: str, value: Any) -> Path:
        content = (
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        return self._write_bytes(filename, content)

    def write_page(self, kind: str, page: HttpPage, detail_number: int | None = None) -> Path:
        if kind not in {"listing", "detail"}:
            raise StagingError(f"Unsupported page kind: {kind}")
        if kind == "detail" and (detail_number is None or not 1 <= detail_number <= 2):
            raise StagingError("Detail page number must be 1 or 2")
        extension = "json" if "json" in page.content_type else "html"
        stem = "listing" if kind == "listing" else f"detail_{detail_number:03d}"
        path = self._write_bytes(f"{stem}.{extension}", page.body)
        self.pages.append({
            "kind": kind,
            "sequence": detail_number if detail_number is not None else 0,
            "file": path.name,
            "requested_url": page.requested_url,
            "final_url": page.final_url,
            "redirect_chain": page.redirect_chain,
            "http_status": page.http_status,
            "content_type": page.content_type,
            "fetched_at": page.fetched_at,
            "raw_sha256": content_sha256(page.body),
            "bytes": len(page.body),
        })
        return path

    def write_parsed_jobs(self, jobs: Iterable[StagingJob]) -> Path:
        lines = [
            json.dumps(job.as_dict(), ensure_ascii=False, sort_keys=True)
            for job in jobs
        ]
        content = (("\n".join(lines) + "\n") if lines else "").encode("utf-8")
        return self._write_bytes("parsed_jobs.jsonl", content)

    def write_summary(self, summary: dict[str, Any]) -> Path:
        return self._write_json("run_summary.json", {**summary, "pages": self.pages})
