import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { extname, relative, resolve, sep } from 'node:path';
import { expectedRedirectSources, parseFrontmatter } from './content-check.mjs';

const root = process.cwd();
const dist = resolve(root, 'dist');
const issues = [];

function walk(directory) {
  if (!existsSync(directory)) return [];
  const files = [];
  for (const name of readdirSync(directory)) {
    const path = resolve(directory, name);
    if (statSync(path).isDirectory()) files.push(...walk(path));
    else files.push(path);
  }
  return files;
}

function routeOutput(route) {
  return resolve(dist, route.replace(/^\//, ''), 'index.html');
}

if (!existsSync(dist)) issues.push('dist/: build output is missing');

const contentFiles = walk(resolve(root, 'src/content')).filter((file) => ['.md', '.mdx'].includes(extname(file)));
const expectedRoutes = [];
for (const file of contentFiles) {
  const parsed = parseFrontmatter(readFileSync(file, 'utf8'));
  if (parsed.data.status !== 'published') continue;
  const rel = relative(resolve(root, 'src/content'), file).split(sep).join('/');
  const match = rel.match(/^(cn|en)\/(career|research)\/(.+)\.(?:md|mdx)$/);
  if (!match) continue;
  const [, lang, collection, slug] = match;
  expectedRoutes.push(`/${lang}/${collection}/${slug}`);
  if (collection === 'research') expectedRoutes.push(`/research-news/${lang}/${slug}`);
}

for (const route of expectedRoutes) {
  if (!existsSync(routeOutput(route))) issues.push(`${route}: published route was not generated`);
}

for (const source of expectedRedirectSources) {
  const oldRoute = source.replace(/\/:path\*$/, '');
  if (existsSync(routeOutput(oldRoute))) issues.push(`${oldRoute}: withdrawn content was still generated`);
}

const htmlFiles = walk(dist).filter((file) => extname(file) === '.html');
const forbiddenOutput = [
  ['legacy estimate label', /\bestimated\b/i],
  ['Chinese salary demo', /机器人行业 2025 校招薪资全景/],
  ['English salary demo', /Robotics Engineering Career Map: Skills, Salaries/],
  ['Chinese BOM demo', /人形机器人核心执行器 BOM 成本拆解/],
  ['English BOM demo', /Humanoid Robot Actuator BOM Teardown/],
  ['published payload demo', /具身智能最新进展：2026年人形机器人论文综述/],
  ['unsupported engineer sample', /340\s*\+\s*(?:一线工程师|Engineer Respondents)/i],
  ['unsupported supplier sample', /50\s*\+\s*(?:供应商|Supplier)/i],
];

for (const file of htmlFiles) {
  const text = readFileSync(file, 'utf8');
  for (const [label, pattern] of forbiddenOutput) {
    if (pattern.test(text)) issues.push(`${relative(root, file)}: contains ${label}`);
  }
}

if (issues.length > 0) {
  console.error(`Build content verification failed with ${issues.length} issue(s):`);
  for (const item of issues) console.error(`- ${item}`);
  process.exit(1);
}

console.log(`Build content verification passed: ${expectedRoutes.length} published detail routes, ${htmlFiles.length} HTML pages, no withdrawn-content output.`);
