import { backup as sqliteBackup, DatabaseSync } from 'node:sqlite';
import { createHash } from 'node:crypto';
import {
  access,
  chmod,
  link,
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  rename,
  rm,
  rmdir,
  symlink,
  writeFile,
} from 'node:fs/promises';
import { constants as fsConstants } from 'node:fs';
import { basename, dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const REQUIRED_ENTITIES = Object.freeze([
  'companies',
  'career_sources',
  'job_postings',
  'skills',
  'job_skill_relations',
  'job_changes',
  'project_templates',
]);

export const SUPPORTING_TABLES = Object.freeze([
  'skill_aliases',
  'project_template_job_families',
  'project_template_skills',
  'pipeline_runs',
  'review_queue',
  'system_controls',
]);

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const defaultMigrationsDirectory = resolve(repositoryRoot, 'career-intelligence/migrations');
const migrationPattern = /^(\d{4})_([a-z0-9_]+)\.sql$/;

function isInside(parent, candidate) {
  const pathFromParent = relative(parent, candidate);
  return pathFromParent === '' || (!pathFromParent.startsWith('..') && !isAbsolute(pathFromParent));
}

export function assertExternalAbsolutePath(candidate, label) {
  if (!candidate || !isAbsolute(candidate)) {
    throw new Error(`${label} must be an explicit absolute path`);
  }
  const resolvedCandidate = resolve(candidate);
  const forbiddenExactPaths = new Set(['/', '/root', '/tmp']);
  if (forbiddenExactPaths.has(resolvedCandidate)) {
    throw new Error(`${label} must not target a broad system/workspace directory`);
  }
  if (isInside(repositoryRoot, resolvedCandidate)) {
    throw new Error(`${label} must be outside the Git worktree`);
  }
  for (const protectedRoot of ['/root/robot', '/root/.hermes', '/root/hermes-workspace']) {
    if (isInside(protectedRoot, resolvedCandidate)) {
      throw new Error(`${label} must not target a protected production or Hermes path`);
    }
  }
  return resolvedCandidate;
}

async function pathExists(path) {
  try {
    await access(path, fsConstants.F_OK);
    return true;
  } catch (error) {
    if (error.code === 'ENOENT') return false;
    throw error;
  }
}

async function removeDirectoryIfEmpty(path) {
  try {
    await rmdir(path);
  } catch (error) {
    if (!['ENOENT', 'ENOTEMPTY'].includes(error.code)) throw error;
  }
}

async function loadMigrations(migrationsDirectory = defaultMigrationsDirectory) {
  const names = (await readdir(migrationsDirectory))
    .filter((name) => name.endsWith('.sql'))
    .sort();
  if (names.length === 0) throw new Error('No career database migrations found');

  const migrations = [];
  for (const name of names) {
    const match = name.match(migrationPattern);
    if (!match) throw new Error(`Invalid migration filename: ${name}`);
    const version = Number(match[1]);
    const sql = await readFile(resolve(migrationsDirectory, name), 'utf8');
    migrations.push({
      version,
      name,
      sql,
      checksum: createHash('sha256').update(sql).digest('hex'),
    });
  }

  for (let index = 1; index < migrations.length; index += 1) {
    if (migrations[index - 1].version >= migrations[index].version) {
      throw new Error('Migration versions must be unique and strictly increasing');
    }
  }
  return migrations;
}

function configureConnection(db) {
  db.exec(`
    PRAGMA foreign_keys = ON;
    PRAGMA busy_timeout = 5000;
    PRAGMA synchronous = FULL;
  `);
}

function ensureMigrationTable(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version INTEGER PRIMARY KEY,
      name TEXT NOT NULL UNIQUE,
      checksum TEXT NOT NULL CHECK(length(checksum) = 64),
      applied_at TEXT NOT NULL
    ) STRICT;
  `);
}

export function openDatabase(databasePath) {
  const db = new DatabaseSync(databasePath);
  configureConnection(db);
  return db;
}

export async function migrateDatabase(databasePath, options = {}) {
  await mkdir(dirname(databasePath), { recursive: true, mode: 0o700 });
  const migrations = await loadMigrations(options.migrationsDirectory);
  const db = openDatabase(databasePath);

  try {
    db.exec('PRAGMA journal_mode = WAL;');
    ensureMigrationTable(db);
    const appliedRows = db.prepare(
      'SELECT version, name, checksum FROM schema_migrations ORDER BY version',
    ).all();
    const appliedByVersion = new Map(appliedRows.map((row) => [row.version, row]));
    const appliedNow = [];

    for (const migration of migrations) {
      const applied = appliedByVersion.get(migration.version);
      if (applied) {
        if (applied.name !== migration.name || applied.checksum !== migration.checksum) {
          throw new Error(`Applied migration ${migration.version} does not match repository checksum`);
        }
        continue;
      }

      db.exec('BEGIN IMMEDIATE;');
      try {
        db.exec(migration.sql);
        db.prepare(
          'INSERT INTO schema_migrations(version, name, checksum, applied_at) VALUES (?, ?, ?, ?)',
        ).run(migration.version, migration.name, migration.checksum, new Date().toISOString());
        db.exec('COMMIT;');
        appliedNow.push(migration.version);
      } catch (error) {
        db.exec('ROLLBACK;');
        throw error;
      }
    }
    return { applied: appliedNow, currentVersion: migrations.at(-1).version };
  } finally {
    db.close();
  }
}

export async function verifyDatabase(databasePath, options = {}) {
  const migrations = await loadMigrations(options.migrationsDirectory);
  const db = openDatabase(databasePath);
  try {
    const integrity = db.prepare('PRAGMA integrity_check').get();
    if (integrity.integrity_check !== 'ok') {
      throw new Error(`SQLite integrity check failed: ${integrity.integrity_check}`);
    }
    if (db.prepare('PRAGMA foreign_key_check').all().length > 0) {
      throw new Error('SQLite foreign key check failed');
    }

    const tables = new Set(db.prepare(
      "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'",
    ).all().map((row) => row.name));
    for (const name of [...REQUIRED_ENTITIES, ...SUPPORTING_TABLES, 'schema_migrations']) {
      if (!tables.has(name)) throw new Error(`Required table is missing: ${name}`);
    }

    const controls = db.prepare(
      'SELECT collection_enabled, publication_enabled FROM system_controls WHERE singleton = 1',
    ).get();
    if (!controls || ![0, 1].includes(controls.collection_enabled) || ![0, 1].includes(controls.publication_enabled)) {
      throw new Error('Collection/publication controls are invalid');
    }

    const applied = db.prepare(
      'SELECT version, name, checksum FROM schema_migrations ORDER BY version',
    ).all();
    if (applied.length !== migrations.length) throw new Error('Not all repository migrations are applied');
    for (const migration of migrations) {
      const row = applied.find((candidate) => candidate.version === migration.version);
      if (!row || row.name !== migration.name || row.checksum !== migration.checksum) {
        throw new Error(`Migration verification failed for version ${migration.version}`);
      }
    }

    return {
      integrity: 'ok',
      currentVersion: migrations.at(-1).version,
      collectionEnabled: controls.collection_enabled === 1,
      publicationEnabled: controls.publication_enabled === 1,
    };
  } finally {
    db.close();
  }
}

export async function setSafetyControls(databasePath, changes) {
  const hasCollectionChange = typeof changes.collectionEnabled === 'boolean';
  const hasPublicationChange = typeof changes.publicationEnabled === 'boolean';
  if (!hasCollectionChange && !hasPublicationChange) {
    throw new Error('At least one safety control must be explicitly specified');
  }
  if (!changes.reason || !changes.updatedBy) {
    throw new Error('Safety control changes require a reason and updatedBy');
  }

  await verifyDatabase(databasePath);
  const db = openDatabase(databasePath);
  try {
    const current = db.prepare(
      'SELECT collection_enabled, publication_enabled FROM system_controls WHERE singleton = 1',
    ).get();
    db.prepare(`
      UPDATE system_controls
      SET collection_enabled = ?, publication_enabled = ?, change_reason = ?,
          updated_by = ?, updated_at = ?
      WHERE singleton = 1
    `).run(
      hasCollectionChange ? Number(changes.collectionEnabled) : current.collection_enabled,
      hasPublicationChange ? Number(changes.publicationEnabled) : current.publication_enabled,
      changes.reason,
      changes.updatedBy,
      new Date().toISOString(),
    );
  } finally {
    db.close();
  }
  return verifyDatabase(databasePath);
}

export async function backupDatabase(databasePath, destinationPath) {
  if (await pathExists(destinationPath)) throw new Error('Backup destination already exists');
  await mkdir(dirname(destinationPath), { recursive: true, mode: 0o700 });
  const temporaryDirectory = await mkdtemp(join(dirname(destinationPath), '.backup-tmp-'));
  const temporaryPath = join(temporaryDirectory, 'backup.sqlite3');
  try {
    const db = openDatabase(databasePath);
    try {
      await sqliteBackup(db, temporaryPath);
    } finally {
      db.close();
    }
    await chmod(temporaryPath, 0o600);
    const validation = await verifyDatabase(temporaryPath);
    try {
      await link(temporaryPath, destinationPath);
    } catch (error) {
      if (error.code === 'EEXIST') throw new Error('Backup destination already exists');
      throw error;
    }
    return validation;
  } finally {
    await rm(temporaryDirectory, { recursive: true, force: true });
  }
}

const publicSnapshotQueries = Object.freeze({
  companies: `
    SELECT DISTINCT c.* FROM companies c
    JOIN job_postings j ON j.company_id = c.company_id
    WHERE j.publication_status = 'published' AND j.quality_status = 'published'
      AND j.review_status = 'approved' AND c.verification_status = 'verified'`,
  career_sources: `
    SELECT DISTINCT s.* FROM career_sources s
    JOIN job_postings j ON j.source_id = s.source_id
    WHERE j.publication_status = 'published' AND j.quality_status = 'published'
      AND j.review_status = 'approved' AND s.verified_at IS NOT NULL`,
  job_postings: `
    SELECT * FROM job_postings
    WHERE publication_status = 'published' AND quality_status = 'published'
      AND review_status = 'approved'`,
  skills: `
    SELECT DISTINCT s.* FROM skills s
    JOIN job_skill_relations r ON r.skill_id = s.skill_id
    JOIN job_postings j ON j.job_id = r.job_id
    WHERE j.publication_status = 'published' AND j.quality_status = 'published'
      AND j.review_status = 'approved' AND r.review_status = 'approved'
      AND s.lifecycle_status = 'active' AND s.review_status = 'approved'`,
  job_skill_relations: `
    SELECT r.* FROM job_skill_relations r
    JOIN job_postings j ON j.job_id = r.job_id
    JOIN skills s ON s.skill_id = r.skill_id
    WHERE j.publication_status = 'published' AND j.quality_status = 'published'
      AND j.review_status = 'approved' AND r.review_status = 'approved'
      AND s.lifecycle_status = 'active' AND s.review_status = 'approved'`,
  job_changes: `
    SELECT c.* FROM job_changes c
    JOIN job_postings j ON j.job_id = c.job_id
    WHERE j.publication_status = 'published' AND j.quality_status = 'published'
      AND j.review_status = 'approved'`,
  project_templates: `
    SELECT * FROM project_templates
    WHERE lifecycle_status = 'approved' AND review_status = 'approved'`,
});

function decodeRow(table, row) {
  const decoded = {};
  for (const [key, value] of Object.entries(row)) {
    if (key.endsWith('_json')) {
      decoded[key.slice(0, -5)] = JSON.parse(value);
    } else if (table === 'career_sources' && key === 'enabled') {
      decoded[key] = value === 1;
    } else {
      decoded[key] = value;
    }
  }
  return decoded;
}

export async function readConsistentPublicSnapshot(databasePath, options = {}) {
  await verifyDatabase(databasePath);
  const db = openDatabase(databasePath);
  try {
    db.exec('BEGIN;');
    const controls = db.prepare(
      'SELECT publication_enabled FROM system_controls WHERE singleton = 1',
    ).get();
    if (controls.publication_enabled !== 1) {
      throw new Error('Public snapshot publication is disabled');
    }

    // These reads establish one WAL snapshot before any optional concurrent writer runs.
    const migrationState = db.prepare('SELECT max(version) AS current_version FROM schema_migrations').get();
    if (options.onSnapshotEstablished) await options.onSnapshotEstablished();

    const entities = {};
    for (const table of REQUIRED_ENTITIES) {
      entities[table] = db.prepare(`${publicSnapshotQueries[table]} ORDER BY 1`).all()
        .map((row) => decodeRow(table, row));
    }
    db.exec('COMMIT;');
    return {
      format: 'robotcareer-career-intelligence-public-snapshot',
      schemaVersion: migrationState.current_version,
      entities,
    };
  } catch (error) {
    try { db.exec('ROLLBACK;'); } catch {}
    throw error;
  } finally {
    db.close();
  }
}

function sha256(content) {
  return createHash('sha256').update(content).digest('hex');
}

async function validateSnapshotDirectory(snapshotDirectory) {
  const manifest = JSON.parse(await readFile(join(snapshotDirectory, 'manifest.json'), 'utf8'));
  if (manifest.format !== 'robotcareer-career-intelligence-public-snapshot') {
    throw new Error('Snapshot manifest format is invalid');
  }
  if (!Number.isInteger(manifest.schemaVersion) || manifest.schemaVersion < 1) {
    throw new Error('Snapshot schema version is invalid');
  }
  const expectedFiles = REQUIRED_ENTITIES.map((table) => `entities/${table}.json`).sort();
  if (JSON.stringify(Object.keys(manifest.files).sort()) !== JSON.stringify(expectedFiles)) {
    throw new Error('Snapshot manifest entity inventory is incomplete');
  }
  const actualEntityFiles = (await readdir(join(snapshotDirectory, 'entities')))
    .map((name) => `entities/${name}`)
    .sort();
  if (JSON.stringify(actualEntityFiles) !== JSON.stringify(expectedFiles)) {
    throw new Error('Snapshot entity directory inventory is incomplete');
  }
  for (const table of REQUIRED_ENTITIES) {
    const filename = `entities/${table}.json`;
    const content = await readFile(join(snapshotDirectory, filename), 'utf8');
    if (sha256(content) !== manifest.files[filename].sha256) {
      throw new Error(`Snapshot checksum failed for ${filename}`);
    }
    const rows = JSON.parse(content);
    if (!Array.isArray(rows) || rows.length !== manifest.files[filename].records) {
      throw new Error(`Snapshot record count failed for ${filename}`);
    }
    if (rows.some((row) => row.schema_version !== manifest.schemaVersion)) {
      throw new Error(`Snapshot schema contract failed for ${filename}`);
    }
  }
  return manifest;
}

export async function validatePublicSnapshot(snapshotRoot) {
  return validateSnapshotDirectory(join(snapshotRoot, 'current'));
}

export async function publishPublicSnapshot(databasePath, snapshotRoot, options = {}) {
  const snapshotRootExisted = await pathExists(snapshotRoot);
  const currentPath = join(snapshotRoot, 'current');
  const currentExists = await pathExists(currentPath);
  if (currentExists && options.replace !== true) {
    throw new Error('Public snapshot already exists; pass replace explicitly to update it');
  }

  const versionsDirectory = join(snapshotRoot, 'versions');
  await mkdir(versionsDirectory, { recursive: true, mode: 0o700 });
  const temporaryDirectory = await mkdtemp(join(versionsDirectory, '.snapshot-tmp-'));
  let finalDirectory;
  let pointerSwitched = false;
  let temporaryLink;

  try {
    const snapshot = await readConsistentPublicSnapshot(databasePath, options);
    const entitiesDirectory = join(temporaryDirectory, 'entities');
    await mkdir(entitiesDirectory, { mode: 0o700 });
    const files = {};
    for (const table of REQUIRED_ENTITIES) {
      const filename = `entities/${table}.json`;
      const content = `${JSON.stringify(snapshot.entities[table], null, 2)}\n`;
      await writeFile(join(temporaryDirectory, filename), content, { mode: 0o600, flag: 'wx' });
      files[filename] = { sha256: sha256(content), records: snapshot.entities[table].length };
    }
    const manifest = {
      format: snapshot.format,
      schemaVersion: snapshot.schemaVersion,
      generatedAt: new Date().toISOString(),
      files,
    };
    await writeFile(join(temporaryDirectory, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, {
      mode: 0o600,
      flag: 'wx',
    });
    await validateSnapshotDirectory(temporaryDirectory);

    const suffix = basename(temporaryDirectory).slice('.snapshot-tmp-'.length);
    const versionName = `snapshot-${Date.now()}-${suffix}`;
    finalDirectory = join(versionsDirectory, versionName);
    await rename(temporaryDirectory, finalDirectory);
    const relativeTarget = join('versions', versionName);

    if (currentExists) {
      temporaryLink = join(snapshotRoot, `.current-${suffix}`);
      await symlink(relativeTarget, temporaryLink, 'dir');
      await rename(temporaryLink, currentPath);
    } else {
      await symlink(relativeTarget, currentPath, 'dir');
    }
    pointerSwitched = true;
    const validated = await validatePublicSnapshot(snapshotRoot);
    return { version: versionName, current: currentPath, manifest: validated };
  } finally {
    await rm(temporaryDirectory, { recursive: true, force: true });
    if (temporaryLink) await rm(temporaryLink, { force: true });
    if (finalDirectory && !pointerSwitched) await rm(finalDirectory, { recursive: true, force: true });
    if (!snapshotRootExisted && !pointerSwitched) {
      await removeDirectoryIfEmpty(versionsDirectory);
      await removeDirectoryIfEmpty(snapshotRoot);
    }
  }
}
