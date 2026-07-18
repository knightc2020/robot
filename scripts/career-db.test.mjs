import assert from 'node:assert/strict';
import { once } from 'node:events';
import { mkdtemp, readFile, readdir, readlink, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import test from 'node:test';
import { Worker } from 'node:worker_threads';
import {
  REQUIRED_ENTITIES,
  SUPPORTING_TABLES,
  assertExternalAbsolutePath,
  backupDatabase,
  migrateDatabase,
  openDatabase,
  publishPublicSnapshot,
  setSafetyControls,
  validatePublicSnapshot,
  verifyDatabase,
} from './lib/career-db.mjs';

const fixedTime = '2026-07-18T05:00:00.000Z';

function insertCompany(db, companyId, displayName) {
  db.prepare(`
    INSERT INTO companies(company_id, legal_name, display_name, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?)
  `).run(companyId, displayName, displayName, fixedTime, fixedTime);
}

test('Phase 2 career database is physical, recoverable, concurrent, and fail-closed', async (t) => {
  const testDirectory = await mkdtemp(join(tmpdir(), 'career-db-phase2-'));
  const databasePath = join(testDirectory, 'staging.sqlite3');
  const concurrencyPath = join(testDirectory, 'concurrency.sqlite3');
  const backupPath = join(testDirectory, 'backup.sqlite3');
  const snapshotRoot = join(testDirectory, 'public-snapshot');

  t.after(async () => {
    await rm(testDirectory, { recursive: true, force: true });
  });

  await t.test('requires explicit paths outside the repository', () => {
    assert.throws(() => assertExternalAbsolutePath('relative.sqlite3', 'Database path'), /absolute path/);
    assert.throws(
      () => assertExternalAbsolutePath(resolve('career-intelligence/local.sqlite3'), 'Database path'),
      /outside the Git worktree/,
    );
    assert.throws(() => assertExternalAbsolutePath('/root', 'Output path'), /broad system/);
    assert.throws(
      () => assertExternalAbsolutePath('/root/robot/data/career.sqlite3', 'Database path'),
      /protected production/,
    );
    assert.equal(assertExternalAbsolutePath(databasePath, 'Database path'), databasePath);
  });

  await t.test('creates every physical table once and defaults both safety switches off', async () => {
    assert.deepEqual(await migrateDatabase(databasePath), { applied: [1], currentVersion: 1 });
    assert.deepEqual(await migrateDatabase(databasePath), { applied: [], currentVersion: 1 });
    assert.deepEqual(await verifyDatabase(databasePath), {
      integrity: 'ok', currentVersion: 1, collectionEnabled: false, publicationEnabled: false,
    });

    const requiredPhysicalTables = [
      'schema_migrations', 'companies', 'career_sources', 'job_postings', 'skills',
      'skill_aliases', 'job_skill_relations', 'job_changes', 'project_templates',
      'pipeline_runs', 'review_queue', 'system_controls',
      'project_template_job_families', 'project_template_skills',
    ];
    const db = openDatabase(databasePath);
    try {
      const actual = new Set(db.prepare(
        "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'",
      ).all().map((row) => row.name));
      for (const table of requiredPhysicalTables) assert.ok(actual.has(table), table);
      for (const table of [...REQUIRED_ENTITIES, ...SUPPORTING_TABLES].filter((name) => name !== 'system_controls')) {
        assert.equal(db.prepare(`SELECT count(*) AS count FROM "${table}"`).get().count, 0);
      }
      assert.equal(db.prepare('SELECT count(*) AS count FROM system_controls').get().count, 1);
      assert.equal(db.prepare('PRAGMA journal_mode').get().journal_mode, 'wal');
      assert.equal(db.prepare('PRAGMA foreign_keys').get().foreign_keys, 1);
      assert.equal(db.prepare('PRAGMA busy_timeout').get().timeout, 5000);
    } finally {
      db.close();
    }
    await assert.rejects(
      () => publishPublicSnapshot(databasePath, snapshotRoot),
      /publication is disabled/,
    );
  });

  await t.test('allows explicit, independent, audited safety-switch changes', async () => {
    assert.deepEqual(await setSafetyControls(databasePath, {
      collectionEnabled: true,
      reason: 'Test independent collection switch without running collection',
      updatedBy: 'career-db.test',
    }), {
      integrity: 'ok', currentVersion: 1, collectionEnabled: true, publicationEnabled: false,
    });
    assert.deepEqual(await setSafetyControls(databasePath, {
      collectionEnabled: false,
      publicationEnabled: true,
      reason: 'Test public snapshot path with collection kept disabled',
      updatedBy: 'career-db.test',
    }), {
      integrity: 'ok', currentVersion: 1, collectionEnabled: false, publicationEnabled: true,
    });
  });

  await t.test('enforces provenance, aliases, review relations, and append-only history', () => {
    const db = openDatabase(databasePath);
    try {
      insertCompany(db, 'test-company', 'Reserved Test Company');
      db.prepare(`
        INSERT INTO career_sources(
          source_id, company_id, source_url, source_type, collection_method,
          owner, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `).run(
        'test-source', 'test-company', 'https://jobs.example.invalid/',
        'official_career_page', 'fixture-adapter', 'test-suite', fixedTime, fixedTime,
      );
      db.prepare(`
        INSERT INTO job_postings(
          job_id, company_id, source_id, source_native_id, source_url, source_title,
          first_collected_at, last_collected_at, content_hash, raw_snapshot_ref,
          parser_version, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).run(
        'test-job', 'test-company', 'test-source', 'native-test-job',
        'https://jobs.example.invalid/test-job', 'Fixture robotics role', fixedTime,
        fixedTime, 'a'.repeat(64), 'fixtures/raw/test-job.html', 'fixture-parser-v1',
        fixedTime, fixedTime,
      );
      db.prepare(`
        INSERT INTO skills(
          skill_id, canonical_name, category, definition, evidence_expectations,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
      `).run(
        'test-skill', 'Reserved Test Skill', 'test-category', 'Test-only definition',
        'Test-only evidence', fixedTime, fixedTime,
      );
      db.prepare(`
        INSERT INTO skill_aliases(skill_id, alias, language_code, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
      `).run('test-skill', 'Reserved test alias', 'en', fixedTime, fixedTime);
      db.prepare(`
        INSERT INTO job_skill_relations(
          job_id, skill_id, requirement_strength, evidence_excerpt, parser_confidence,
          extraction_method, extraction_version, first_observed_at, last_observed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).run(
        'test-job', 'test-skill', 'required', 'Test-only excerpt', 1,
        'deterministic', 'fixture-parser-v1', fixedTime, fixedTime,
      );
      db.prepare(`
        INSERT INTO job_changes(
          change_id, job_id, source_id, change_type, new_content_hash,
          observed_at, source_url, collected_at, raw_snapshot_ref,
          retrieval_result, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).run(
        'test-change', 'test-job', 'test-source', 'first_observed', 'a'.repeat(64),
        fixedTime, 'https://jobs.example.invalid/test-job', fixedTime,
        'fixtures/raw/test-job.html', 'success', fixedTime,
      );
      db.prepare(`
        INSERT INTO pipeline_runs(
          run_id, pipeline_name, pipeline_stage, environment, status,
          code_version, started_at, finished_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).run(
        'test-run', 'fixture-pipeline', 'validation', 'test', 'succeeded',
        'test-version', fixedTime, fixedTime, fixedTime,
      );
      db.prepare(`
        INSERT INTO review_queue(
          review_id, entity_type, entity_id, reason_code, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
      `).run('test-review', 'job_posting', 'test-job', 'fixture-review', fixedTime, fixedTime);

      assert.throws(
        () => db.exec("UPDATE job_changes SET change_type = 'closed' WHERE change_id = 'test-change'"),
        /append-only/,
      );
      assert.throws(
        () => db.prepare(`
          INSERT INTO job_postings(
            job_id, company_id, source_id, source_native_id, source_url, source_title,
            first_collected_at, last_collected_at, content_hash, raw_snapshot_ref,
            parser_version, created_at, updated_at
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `).run(
          'invalid-job', 'unknown-company', 'test-source', 'invalid',
          'https://jobs.example.invalid/invalid', 'Invalid fixture', fixedTime,
          fixedTime, 'b'.repeat(64), 'fixtures/raw/invalid.html', 'fixture-parser-v1',
          fixedTime, fixedTime,
        ),
        /FOREIGN KEY constraint failed/,
      );
    } finally {
      db.close();
    }
  });

  await t.test('supports two readers during writes and applies the configured busy timeout', async () => {
    await migrateDatabase(concurrencyPath);
    const readerOne = openDatabase(concurrencyPath);
    const readerTwo = openDatabase(concurrencyPath);
    const writer = openDatabase(concurrencyPath);
    try {
      assert.equal(readerOne.prepare('SELECT count(*) AS count FROM companies').get().count, 0);
      assert.equal(readerTwo.prepare('SELECT count(*) AS count FROM companies').get().count, 0);
      writer.exec('BEGIN IMMEDIATE;');
      insertCompany(writer, 'uncommitted-writer', 'Uncommitted Writer');
      assert.equal(readerOne.prepare('SELECT count(*) AS count FROM companies').get().count, 0);
      assert.equal(readerTwo.prepare('SELECT count(*) AS count FROM companies').get().count, 0);
      writer.exec('COMMIT;');
      assert.equal(readerOne.prepare('SELECT count(*) AS count FROM companies').get().count, 1);
      assert.equal(readerTwo.prepare('SELECT count(*) AS count FROM companies').get().count, 1);
    } finally {
      writer.close();
      readerTwo.close();
      readerOne.close();
    }

    const workerCode = `
      const { parentPort } = require('node:worker_threads');
      const { DatabaseSync } = require('node:sqlite');
      const db = new DatabaseSync(${JSON.stringify(concurrencyPath)});
      db.exec('PRAGMA busy_timeout = 5000; BEGIN IMMEDIATE;');
      db.prepare('INSERT INTO companies(company_id, legal_name, display_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)')
        .run('writer-one', 'Writer One', 'Writer One', ${JSON.stringify(fixedTime)}, ${JSON.stringify(fixedTime)});
      parentPort.postMessage('LOCKED');
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 300);
      db.exec('COMMIT;');
      db.close();
    `;
    const worker = new Worker(workerCode, { eval: true });
    const exitPromise = once(worker, 'exit');
    assert.equal((await once(worker, 'message'))[0], 'LOCKED');
    const waitingWriter = openDatabase(concurrencyPath);
    const waitStarted = Date.now();
    try {
      assert.equal(waitingWriter.prepare('PRAGMA busy_timeout').get().timeout, 5000);
      insertCompany(waitingWriter, 'writer-two', 'Writer Two');
    } finally {
      waitingWriter.close();
    }
    assert.ok(Date.now() - waitStarted >= 150, 'second writer should wait for the lock');
    const [exitCode] = await exitPromise;
    assert.equal(exitCode, 0);
  });

  await t.test('migration transaction mode prohibits concurrent writes', () => {
    const migrationConnection = openDatabase(concurrencyPath);
    const competingWriter = openDatabase(concurrencyPath);
    try {
      migrationConnection.exec('BEGIN IMMEDIATE;');
      competingWriter.exec('PRAGMA busy_timeout = 50;');
      assert.throws(
        () => insertCompany(competingWriter, 'blocked-during-migration', 'Blocked During Migration'),
        /database is locked/,
      );
      migrationConnection.exec('ROLLBACK;');
    } finally {
      competingWriter.close();
      migrationConnection.close();
    }
  });

  await t.test('creates a consistent, validated snapshot and atomically updates current', async () => {
    const db = openDatabase(databasePath);
    try {
      db.prepare(`
        INSERT INTO project_templates(
          project_template_id, slug, title, summary, difficulty, deliverables_json,
          acceptance_evidence_json, lifecycle_status, review_status, reviewed_by,
          reviewed_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).run(
        'public-test-project', 'public-test-project', 'Snapshot Before Concurrent Write',
        'Ephemeral approved test fixture', 'introductory', '["fixture deliverable"]',
        '["fixture evidence"]', 'approved', 'approved', 'test-reviewer', fixedTime,
        fixedTime, fixedTime,
      );
    } finally {
      db.close();
    }

    const first = await publishPublicSnapshot(databasePath, snapshotRoot, {
      onSnapshotEstablished: async () => {
        const concurrentWriter = openDatabase(databasePath);
        try {
          concurrentWriter.prepare(`
            UPDATE project_templates SET title = ?, updated_at = ?
            WHERE project_template_id = ?
          `).run('Snapshot After Concurrent Write', '2026-07-18T05:01:00.000Z', 'public-test-project');
        } finally {
          concurrentWriter.close();
        }
      },
    });
    assert.equal((await validatePublicSnapshot(snapshotRoot)).schemaVersion, 1);
    const firstProjects = JSON.parse(await readFile(
      join(snapshotRoot, 'current/entities/project_templates.json'), 'utf8',
    ));
    assert.equal(firstProjects[0].title, 'Snapshot Before Concurrent Write');
    const firstPointer = await readlink(join(snapshotRoot, 'current'));
    assert.equal(first.version, firstPointer.split('/').at(-1));

    await assert.rejects(
      () => publishPublicSnapshot(databasePath, snapshotRoot),
      /pass replace explicitly/,
    );
    const second = await publishPublicSnapshot(databasePath, snapshotRoot, { replace: true });
    const secondPointer = await readlink(join(snapshotRoot, 'current'));
    assert.notEqual(secondPointer, firstPointer);
    assert.equal(second.version, secondPointer.split('/').at(-1));
    const secondProjects = JSON.parse(await readFile(
      join(snapshotRoot, 'current/entities/project_templates.json'), 'utf8',
    ));
    assert.equal(secondProjects[0].title, 'Snapshot After Concurrent Write');
    const versionEntries = await readdir(join(snapshotRoot, 'versions'));
    assert.equal(versionEntries.filter((name) => name.startsWith('snapshot-')).length, 2);
    assert.equal(versionEntries.some((name) => name.startsWith('.snapshot-tmp-')), false);
  });

  await t.test('refuses backup overwrite and restores through full validation', async () => {
    const openSource = openDatabase(databasePath);
    try {
      const restoredValidation = await backupDatabase(databasePath, backupPath);
      assert.equal(restoredValidation.integrity, 'ok');
      assert.equal(restoredValidation.publicationEnabled, true);
    } finally {
      openSource.close();
    }
    assert.equal((await stat(backupPath)).mode & 0o777, 0o600);
    assert.deepEqual(await verifyDatabase(backupPath), {
      integrity: 'ok', currentVersion: 1, collectionEnabled: false, publicationEnabled: true,
    });
    await assert.rejects(() => backupDatabase(databasePath, backupPath), /already exists/);
  });

  await t.test('publishes one versioned logical contract containing all seven entities', async () => {
    const schema = JSON.parse(await readFile(
      resolve('career-intelligence/schema/v1/entities.schema.json'), 'utf8',
    ));
    assert.equal(schema.$schema, 'https://json-schema.org/draft/2020-12/schema');
    const entityDefinitions = [
      'company', 'career_source', 'job_posting', 'skill',
      'job_skill_relation', 'job_change', 'project_template',
    ];
    for (const entity of entityDefinitions) {
      assert.equal(schema.$defs[entity].additionalProperties, false);
      assert.ok(schema.$defs[entity].required.length > 0);
    }
    assert.equal(schema.oneOf.length, REQUIRED_ENTITIES.length);
  });
});
