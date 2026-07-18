import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { runContentChecks } from './content-check.mjs';

const fixtureRoot = mkdtempSync(join(tmpdir(), 'robomatrix-content-check-'));
const contentRoot = join(fixtureRoot, 'src/content/cn/research');
mkdirSync(contentRoot, { recursive: true });

const badFixture = join(contentRoot, 'fixture-demo.md');
writeFileSync(badFixture, `---
title: "Fixture demo"
date: "2026-07-18"
updatedAt: "2026-07-18"
industry_sector: "general"
status: "published"
sourceType: "other"
sourceUrls: ["https://example.com/source"]
reviewStatus: "pending_review"
---

340+ 一线工程师
`);

try {
  const failing = runContentChecks({ root: fixtureRoot, includeRepositoryRules: false });
  const failingRules = new Set(failing.issues.map((item) => item.rule));
  for (const expected of ['TEST_CONTENT_IN_PUBLIC_COLLECTION', 'UNSUPPORTED_ENGINEER_SAMPLE', 'PLACEHOLDER_SOURCE']) {
    if (!failingRules.has(expected)) throw new Error(`negative fixture did not trigger ${expected}`);
  }

  rmSync(badFixture);
  writeFileSync(join(contentRoot, 'valid.md'), `---
title: "Valid fixture control"
date: "2026-07-18"
updatedAt: "2026-07-18"
industry_sector: "general"
status: "published"
sourceType: "academic_paper"
sourceUrls: ["https://arxiv.org/abs/2607.14183"]
reviewStatus: "pending_review"
---

Deterministic test content.
`);

  const passing = runContentChecks({ root: fixtureRoot, includeRepositoryRules: false });
  if (passing.issues.length > 0) {
    throw new Error(`clean fixture did not recover: ${JSON.stringify(passing.issues)}`);
  }
  console.log('Content quality negative test passed: violation blocked, removal restored a clean result.');
} finally {
  rmSync(fixtureRoot, { recursive: true, force: true });
}
