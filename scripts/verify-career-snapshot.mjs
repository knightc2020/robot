import { createHash } from 'node:crypto';
import { lstat, readFile, readdir } from 'node:fs/promises';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const snapshotRoot = join(repositoryRoot, 'src/data/career-public');
const expectedFiles = [
  'companies.json',
  'jobs.json',
  'skills.json',
  'role-summary.json',
  'project-templates.json',
];

function fail(message) {
  throw new Error(`Career public snapshot check failed: ${message}`);
}

function inside(parent, candidate) {
  const pathFromParent = relative(parent, candidate);
  return pathFromParent === '' || (!pathFromParent.startsWith('..') && !isAbsolute(pathFromParent));
}

async function requireOrdinaryFile(path) {
  const metadata = await lstat(path);
  if (!metadata.isFile() || metadata.isSymbolicLink()) fail(`${path} is not an ordinary file`);
}

await requireOrdinaryFile(join(snapshotRoot, 'current.json'));
const current = JSON.parse(await readFile(join(snapshotRoot, 'current.json'), 'utf8'));
if (JSON.stringify(Object.keys(current).sort()) !== JSON.stringify(['manifest', 'version'])) {
  fail('current.json fields are invalid');
}
for (const value of Object.values(current)) {
  if (typeof value !== 'string' || isAbsolute(value) || value.split('/').includes('..')) {
    fail('current.json must contain safe repository-relative paths');
  }
}
const versionDirectory = resolve(snapshotRoot, current.version);
const manifestPath = resolve(snapshotRoot, current.manifest);
if (!inside(snapshotRoot, versionDirectory) || !inside(versionDirectory, manifestPath)) {
  fail('current.json escapes the repository snapshot root');
}
const versionMetadata = await lstat(versionDirectory);
if (!versionMetadata.isDirectory() || versionMetadata.isSymbolicLink()) fail('snapshot version is not an ordinary directory');
await requireOrdinaryFile(manifestPath);
const inventory = (await readdir(versionDirectory)).sort();
const expectedInventory = ['manifest.json', ...expectedFiles].sort();
if (JSON.stringify(inventory) !== JSON.stringify(expectedInventory)) fail('snapshot file inventory is invalid');

const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
if (manifest.format !== 'robotcareer-career-public-snapshot' || manifest.schemaVersion !== 1) {
  fail('manifest format or schema version is invalid');
}
if (JSON.stringify(Object.keys(manifest.files).sort()) !== JSON.stringify([...expectedFiles].sort())) {
  fail('manifest entity inventory is invalid');
}
for (const filename of expectedFiles) {
  const path = join(versionDirectory, filename);
  await requireOrdinaryFile(path);
  const content = await readFile(path);
  const rows = JSON.parse(content.toString('utf8'));
  if (!Array.isArray(rows) || rows.length !== manifest.files[filename].records) {
    fail(`${filename} record count is invalid`);
  }
  if (createHash('sha256').update(content).digest('hex') !== manifest.files[filename].sha256) {
    fail(`${filename} checksum is invalid`);
  }
}

console.log(`Career public snapshot check passed: ${current.version}, ${expectedFiles.length} entity files.`);
