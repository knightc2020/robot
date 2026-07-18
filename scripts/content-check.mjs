import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, extname, relative, resolve, sep } from 'node:path';

const CONTENT_EXTENSIONS = new Set(['.md', '.mdx']);
const VALID_STATUSES = new Set(['draft', 'review', 'published', 'archived']);
const SITE_HOSTS = new Set(['robotcareer.cloud', 'www.robotcareer.cloud']);
const PLACEHOLDER_HOSTS = new Set(['example.com', 'www.example.com', 'localhost', '127.0.0.1']);

const FORBIDDEN_PUBLIC_PATTERNS = [
  ['UNSUPPORTED_ENGINEER_SAMPLE', /340\s*\+\s*(?:(?:一线)?工程师|(?:front[ -]?line\s+)?engineer)/i],
  ['UNSUPPORTED_SUPPLIER_SAMPLE', /50\s*\+\s*(?:供应商|supplier)/i],
  ['UNSUPPORTED_CN_SURVEY', /340\s*份[^\n]{0,40}匿名问卷/i],
  ['UNSUPPORTED_EN_SURVEY', /210\s+(?:anonymous\s+survey|anonymous\s+(?:survey\s+)?responses?)/i],
  ['UNSUPPORTED_CN_INTERVIEWS', /12\s*家[^\n]{0,50}供应商[^\n]{0,30}访谈/i],
  ['UNSUPPORTED_EN_INTERVIEWS', /(?:interviews?\s+with\s+)?12\s+(?:core\s+)?suppliers?[^\n]{0,30}(?:interviews?)?/i],
  ['UNSUPPORTED_DATABASE_CLAIM', /所有反馈[^\n]{0,80}(?:交叉验证|数据库)|all submissions[^\n]{0,80}(?:cross[ -]?verified|database|integration)/i],
  ['LEGACY_ESTIMATE_LABEL', /\bestimated\b/i],
];

export const expectedRedirectSources = [
  '/cn/career/robotics-salary-2025/:path*',
  '/en/career/robotics-career-map-2025/:path*',
  '/cn/research/humanoid-actuator-bom-2025/:path*',
  '/en/research/humanoid-actuator-bom-2025/:path*',
  '/research-news/cn/humanoid-actuator-bom-2025/:path*',
  '/research-news/en/humanoid-actuator-bom-2025/:path*',
  '/cn/research/2026-02-28T16-48-38-2026/:path*',
  '/research-news/cn/2026-02-28T16-48-38-2026/:path*',
  '/cn/research/arxiv-1772334967/:path*',
  '/research-news/cn/arxiv-1772334967/:path*',
  '/cn/research/arxiv-1772335777/:path*',
  '/research-news/cn/arxiv-1772335777/:path*',
  '/cn/research/arxiv-1772336924/:path*',
  '/research-news/cn/arxiv-1772336924/:path*',
  '/cn/research/arxiv-1772356557/:path*',
  '/research-news/cn/arxiv-1772356557/:path*',
  '/cn/research/arxiv-1772399776/:path*',
  '/research-news/cn/arxiv-1772399776/:path*',
  '/cn/research/arxiv-1772442962/:path*',
  '/research-news/cn/arxiv-1772442962/:path*',
  '/cn/research/arxiv-1772638926/:path*',
  '/research-news/cn/arxiv-1772638926/:path*',
  '/cn/research/arxiv-1778211670/:path*',
  '/research-news/cn/arxiv-1778211670/:path*',
  '/cn/research/arxiv-1778254872/:path*',
  '/research-news/cn/arxiv-1778254872/:path*',
  '/cn/research/arxiv-1778384475/:path*',
  '/research-news/cn/arxiv-1778384475/:path*',
];

const governedRouteFiles = [
  'src/pages/cn/index.astro',
  'src/pages/en/index.astro',
  'src/pages/cn/career/index.astro',
  'src/pages/cn/career/[slug].astro',
  'src/pages/en/career/index.astro',
  'src/pages/en/career/[slug].astro',
  'src/pages/cn/research/index.astro',
  'src/pages/cn/research/[slug].astro',
  'src/pages/en/research/index.astro',
  'src/pages/en/research/[slug].astro',
  'src/pages/research-news/index.astro',
  'src/pages/research-news/[...slug].astro',
];

function walk(directory) {
  if (!existsSync(directory)) return [];
  const files = [];
  for (const name of readdirSync(directory)) {
    if (['.git', '.astro', 'dist', 'node_modules'].includes(name)) continue;
    const path = resolve(directory, name);
    if (statSync(path).isDirectory()) files.push(...walk(path));
    else files.push(path);
  }
  return files;
}

function parseValue(value) {
  const trimmed = value.trim();
  if (!trimmed) return '';
  if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
    try {
      return JSON.parse(trimmed.replaceAll("'", '"'));
    } catch {
      return trimmed;
    }
  }
  if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
    try {
      return JSON.parse(trimmed);
    } catch {
      return trimmed.slice(1, -1);
    }
  }
  if (trimmed.startsWith("'") && trimmed.endsWith("'")) return trimmed.slice(1, -1);
  if (trimmed === 'true') return true;
  if (trimmed === 'false') return false;
  return trimmed;
}

export function parseFrontmatter(text) {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
  if (!match) return { data: {}, raw: '', body: text, valid: false };
  const data = {};
  for (const line of match[1].split(/\r?\n/)) {
    const field = line.match(/^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$/);
    if (field) data[field[1]] = parseValue(field[2]);
  }
  return { data, raw: match[1], body: text.slice(match[0].length), valid: true };
}

function issue(rule, file, message) {
  return { rule, file, message };
}

function normalizedSource(urlString) {
  const url = new URL(urlString);
  const arxiv = url.pathname.match(/^\/(?:abs|pdf|e-print)\/(\d{4}\.\d{4,5})(?:v\d+)?(?:\.pdf)?$/i);
  if (url.hostname.toLowerCase() === 'arxiv.org' && arxiv) {
    return { kind: 'arxiv', value: arxiv[1] };
  }
  if (url.hostname.toLowerCase() === 'doi.org') {
    return { kind: 'doi', value: decodeURIComponent(url.pathname.replace(/^\//, '')).toLowerCase() };
  }
  url.hostname = url.hostname.toLowerCase().replace(/^www\./, '');
  url.hash = '';
  url.search = '';
  url.pathname = url.pathname.replace(/\/+$/, '') || '/';
  return { kind: 'url', value: url.toString() };
}

function languageFor(relativePath) {
  const parts = relativePath.split('/');
  const index = parts.indexOf('content');
  return index >= 0 ? parts[index + 1] : 'unknown';
}

export function inspectContentFile(file, root) {
  const relativePath = relative(root, file).split(sep).join('/');
  const text = readFileSync(file, 'utf8');
  const parsed = parseFrontmatter(text);
  const issues = [];

  if (!parsed.valid) {
    issues.push(issue('FRONTMATTER_REQUIRED', relativePath, 'content file has no valid frontmatter block'));
    return { issues, record: null };
  }

  const status = parsed.data.status;
  if (!status) issues.push(issue('STATUS_REQUIRED', relativePath, 'status must be explicitly declared'));
  else if (!VALID_STATUSES.has(status)) issues.push(issue('STATUS_INVALID', relativePath, `unsupported status: ${status}`));

  if (/(?:^|\/)(?:fixture|demo|test[-_]?payload|synthetic)(?:[._/-]|$)/i.test(relativePath)
    || parsed.data.fixture === true
    || parsed.data.synthetic === true
    || /^(?:\[)?(?:fixture|demo|synthetic)(?:\]|:|-)/i.test(String(parsed.data.title ?? ''))) {
    issues.push(issue('TEST_CONTENT_IN_PUBLIC_COLLECTION', relativePath, 'fixture/demo/synthetic content must stay outside public collections'));
  }

  if (status !== 'published') return { issues, record: null };

  for (const [rule, pattern] of FORBIDDEN_PUBLIC_PATTERNS) {
    if (pattern.test(text)) issues.push(issue(rule, relativePath, 'forbidden legacy/demo statement appears in published content'));
  }

  if (!parsed.data.title) issues.push(issue('TITLE_REQUIRED', relativePath, 'published content requires title'));
  const publishedDate = parsed.data.publishedAt || parsed.data.date;
  if (!publishedDate || Number.isNaN(Date.parse(String(publishedDate)))) {
    issues.push(issue('PUBLISHED_DATE_REQUIRED', relativePath, 'published content requires a valid publishedAt or legacy date'));
  }
  if (!parsed.data.updatedAt || Number.isNaN(Date.parse(String(parsed.data.updatedAt)))) {
    issues.push(issue('UPDATED_DATE_REQUIRED', relativePath, 'published content requires a valid governance updatedAt'));
  }
  if (!parsed.data.reviewStatus) issues.push(issue('REVIEW_STATUS_REQUIRED', relativePath, 'published content requires reviewStatus'));
  if (!parsed.data.sourceType) issues.push(issue('SOURCE_TYPE_REQUIRED', relativePath, 'published content requires sourceType'));

  const sourceUrls = Array.isArray(parsed.data.sourceUrls) ? parsed.data.sourceUrls : [];
  if (sourceUrls.length === 0) {
    issues.push(issue('SOURCE_URL_REQUIRED', relativePath, 'published content requires a non-empty sourceUrls array'));
  }

  const identities = [];
  let externalSourceCount = 0;
  for (const sourceUrl of sourceUrls) {
    try {
      const url = new URL(sourceUrl);
      if (!['http:', 'https:'].includes(url.protocol)) throw new Error('URL must use http(s)');
      const host = url.hostname.toLowerCase();
      if (PLACEHOLDER_HOSTS.has(host) || host.endsWith('.example')) {
        issues.push(issue('PLACEHOLDER_SOURCE', relativePath, `placeholder source URL: ${sourceUrl}`));
      }
      if (!SITE_HOSTS.has(host)) externalSourceCount += 1;
      identities.push(normalizedSource(sourceUrl));
    } catch {
      issues.push(issue('SOURCE_URL_INVALID', relativePath, `invalid source URL: ${sourceUrl}`));
    }
  }
  if (sourceUrls.length > 0 && externalSourceCount === 0) {
    issues.push(issue('SELF_SOURCE_ONLY', relativePath, 'the site itself cannot be the only factual source'));
  }

  return {
    issues,
    record: {
      file: relativePath,
      language: languageFor(relativePath),
      identities,
      status,
    },
  };
}

function inspectPublicSurfaces(root) {
  const issues = [];
  for (const directory of ['src/pages', 'src/components', 'src/layouts']) {
    for (const file of walk(resolve(root, directory))) {
      const text = readFileSync(file, 'utf8');
      const relativePath = relative(root, file).split(sep).join('/');
      for (const [rule, pattern] of FORBIDDEN_PUBLIC_PATTERNS) {
        if (pattern.test(text)) issues.push(issue(rule, relativePath, 'forbidden legacy/demo statement appears in a public surface'));
      }
    }
  }
  return issues;
}

function inspectDuplicateSources(records) {
  const issues = [];
  const seen = new Map();
  for (const record of records) {
    const uniqueIdentities = new Set(record.identities.map(({ kind, value }) => `${kind}:${value}`));
    for (const identity of uniqueIdentities) {
      const key = `${record.language}:${identity}`;
      if (seen.has(key)) {
        issues.push(issue('DUPLICATE_SOURCE', record.file, `same-language canonical source also used by ${seen.get(key)} (${identity})`));
      } else {
        seen.set(key, record.file);
      }
    }
  }
  return { issues, identityCount: seen.size };
}

function inspectRepositoryRules(root) {
  const issues = [];
  const schemaPath = resolve(root, 'src/content.config.ts');
  const schema = existsSync(schemaPath) ? readFileSync(schemaPath, 'utf8') : '';
  if (!schema.includes("status: z.enum(['draft', 'review', 'published', 'archived']),")) {
    issues.push(issue('SCHEMA_STATUS_GOVERNANCE', 'src/content.config.ts', 'status must be required and include draft/review/published/archived'));
  }
  for (const field of ['sourceType', 'sourceUrls', 'publishedAt', 'updatedAt', 'reviewStatus']) {
    if (!schema.includes(`${field}:`)) issues.push(issue('SCHEMA_PROVENANCE_FIELD', 'src/content.config.ts', `missing schema field: ${field}`));
  }

  for (const route of governedRouteFiles) {
    const path = resolve(root, route);
    if (!existsSync(path) || !readFileSync(path, 'utf8').includes('isPublishableContent')) {
      issues.push(issue('ROUTE_PUBLICATION_FILTER', route, 'public content entry point must reuse isPublishableContent'));
    }
  }

  if (existsSync(resolve(root, 'test-payload.json'))) {
    issues.push(issue('LEGACY_TEST_PAYLOAD', 'test-payload.json', 'legacy published test payload must not remain at repository root'));
  }

  const vercelPath = resolve(root, 'vercel.json');
  if (!existsSync(vercelPath)) {
    issues.push(issue('REDIRECT_CONFIG_REQUIRED', 'vercel.json', 'withdrawn URLs require permanent redirects'));
  } else {
    try {
      const config = JSON.parse(readFileSync(vercelPath, 'utf8'));
      const redirects = Array.isArray(config.redirects) ? config.redirects : [];
      const sources = new Set();
      for (const redirect of redirects) {
        if (sources.has(redirect.source)) issues.push(issue('REDIRECT_DUPLICATE', 'vercel.json', `duplicate redirect source: ${redirect.source}`));
        sources.add(redirect.source);
        if (redirect.permanent !== true) issues.push(issue('REDIRECT_NOT_PERMANENT', 'vercel.json', `redirect must be permanent: ${redirect.source}`));
        if (!String(redirect.destination ?? '').startsWith('/')) issues.push(issue('REDIRECT_DESTINATION_INVALID', 'vercel.json', `redirect must stay on-site: ${redirect.source}`));
      }
      for (const source of expectedRedirectSources) {
        if (!sources.has(source)) issues.push(issue('REDIRECT_MISSING', 'vercel.json', `missing redirect: ${source}`));
      }
    } catch (error) {
      issues.push(issue('REDIRECT_CONFIG_INVALID', 'vercel.json', `invalid JSON: ${error.message}`));
    }
  }
  return issues;
}

export function runContentChecks({ root = process.cwd(), includeRepositoryRules = true } = {}) {
  const resolvedRoot = resolve(root);
  const contentRoot = resolve(resolvedRoot, 'src/content');
  const contentFiles = walk(contentRoot).filter((file) => CONTENT_EXTENSIONS.has(extname(file)));
  const issues = [];
  const records = [];

  for (const file of contentFiles) {
    const result = inspectContentFile(file, resolvedRoot);
    issues.push(...result.issues);
    if (result.record) records.push(result.record);
  }

  issues.push(...inspectPublicSurfaces(resolvedRoot));
  const duplicates = inspectDuplicateSources(records);
  issues.push(...duplicates.issues);
  if (includeRepositoryRules) issues.push(...inspectRepositoryRules(resolvedRoot));

  return {
    issues,
    publishedCount: records.length,
    sourceIdentityCount: duplicates.identityCount,
    contentFileCount: contentFiles.length,
  };
}

function main() {
  const root = resolve(process.env.CONTENT_CHECK_ROOT || process.cwd());
  const result = runContentChecks({ root });
  if (result.issues.length > 0) {
    console.error(`Content quality check failed with ${result.issues.length} issue(s):`);
    for (const item of result.issues) console.error(`- [${item.rule}] ${item.file}: ${item.message}`);
    process.exitCode = 1;
    return;
  }
  console.log(`Content quality check passed: ${result.publishedCount} published entries, ${result.sourceIdentityCount} language-scoped source identities, ${result.contentFileCount} content files.`);
}

const isDirectRun = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isDirectRun) main();
