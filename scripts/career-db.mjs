#!/usr/bin/env node

import { parseArgs } from 'node:util';
import {
  assertExternalAbsolutePath,
  backupDatabase,
  migrateDatabase,
  publishPublicSnapshot,
  setSafetyControls,
  validatePublicSnapshot,
  verifyDatabase,
} from './lib/career-db.mjs';

const usage = `Usage:
  npm run career:db -- migrate --database /absolute/outside/repo.sqlite3
  npm run career:db -- verify  --database /absolute/outside/repo.sqlite3
  npm run career:db -- backup  --database /absolute/outside/repo.sqlite3 --output /absolute/new-backup.sqlite3
  npm run career:db -- controls --database /absolute/outside/repo.sqlite3 [--collection enabled|disabled] [--publication enabled|disabled] --reason "..."
  npm run career:db -- snapshot --database /absolute/outside/repo.sqlite3 --output /absolute/snapshot-root [--replace]
  npm run career:db -- snapshot-validate --database /absolute/outside/repo.sqlite3 --output /absolute/snapshot-root`;

const { positionals, values } = parseArgs({
  allowPositionals: true,
  strict: true,
  options: {
    database: { type: 'string' },
    output: { type: 'string' },
    collection: { type: 'string' },
    publication: { type: 'string' },
    reason: { type: 'string' },
    replace: { type: 'boolean', default: false },
  },
});

const [command] = positionals;
if (!['migrate', 'verify', 'backup', 'controls', 'snapshot', 'snapshot-validate'].includes(command) || !values.database) {
  throw new Error(usage);
}

const databasePath = assertExternalAbsolutePath(values.database, 'Database path');
let result;

if (command === 'migrate') {
  result = await migrateDatabase(databasePath);
} else if (command === 'verify') {
  result = await verifyDatabase(databasePath);
} else if (command === 'controls') {
  const parseControl = (value, name) => {
    if (value === undefined) return undefined;
    if (!['enabled', 'disabled'].includes(value)) throw new Error(`${name} must be enabled or disabled`);
    return value === 'enabled';
  };
  if (!values.reason) throw new Error(usage);
  result = await setSafetyControls(databasePath, {
    collectionEnabled: parseControl(values.collection, 'collection'),
    publicationEnabled: parseControl(values.publication, 'publication'),
    reason: values.reason,
    updatedBy: 'career-db-cli',
  });
} else {
  if (!values.output) throw new Error(usage);
  const outputPath = assertExternalAbsolutePath(values.output, 'Output path');
  if (command === 'backup') result = await backupDatabase(databasePath, outputPath);
  if (command === 'snapshot') {
    result = await publishPublicSnapshot(databasePath, outputPath, { replace: values.replace });
  }
  if (command === 'snapshot-validate') result = await validatePublicSnapshot(outputPath);
}

console.log(JSON.stringify(result, null, 2));
