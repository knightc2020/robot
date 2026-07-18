import currentPointer from '../data/career-public/current.json';

type SnapshotManifest = {
  format: string;
  schemaVersion: number;
  generatedAt: string;
  files: Record<string, { sha256: string; records: number }>;
};

const snapshotModules = import.meta.glob('../data/career-public/versions/*/*.json', {
  eager: true,
  import: 'default',
}) as Record<string, unknown>;

function snapshotFile<T>(filename: string): T {
  const key = `../data/career-public/${currentPointer.version}/${filename}`;
  const value = snapshotModules[key];
  if (value === undefined) {
    throw new Error(`Committed career snapshot file is missing: ${key}`);
  }
  return value as T;
}

export const careerPublicSnapshot = Object.freeze({
  manifest: snapshotFile<SnapshotManifest>('manifest.json'),
  companies: snapshotFile<Record<string, unknown>[]>('companies.json'),
  jobs: snapshotFile<Record<string, unknown>[]>('jobs.json'),
  skills: snapshotFile<Record<string, unknown>[]>('skills.json'),
  roleSummary: snapshotFile<Record<string, unknown>[]>('role-summary.json'),
  projectTemplates: snapshotFile<Record<string, unknown>[]>('project-templates.json'),
});
