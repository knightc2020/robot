export const prerender = false;

import type { APIRoute } from 'astro';
import { writeFile, mkdir } from 'node:fs/promises';
import { join } from 'node:path';

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'Invalid JSON body' }, 400);
  }

  const {
    title,
    content = '',
    author = 'Editorial Team',
    tags = [],
    industry_sector = 'general',
    data_source,
    confidence_level = 'estimated',
    status = 'draft',
    summary = '',
    lang = 'en',
  } = body as {
    title?: string;
    content?: string;
    author?: string;
    tags?: string[];
    industry_sector?: string;
    data_source?: string;
    confidence_level?: string;
    status?: string;
    summary?: string;
    lang?: string;
  };

  if (!title) {
    return json({ error: '`title` is required' }, 400);
  }

  const validLangs = ['en', 'cn'];
  if (!validLangs.includes(lang)) {
    return json({ error: '`lang` must be "en" or "cn"' }, 400);
  }

  // --- Timestamp & filename ---
  const now = new Date();
  const isoDate = now.toISOString(); // e.g. 2026-02-28T07:30:00.000Z

  // Filename-safe timestamp: 2026-02-28T07-30-00
  const tsForFile = isoDate.slice(0, 19).replace(/:/g, '-');

  // Slug from title — keep ASCII word chars only for filename safety
  const asciiSlug = (title as string)
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')   // strip non-ASCII (Chinese etc.)
    .replace(/[\s_]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 50);

  // If title is all Chinese (asciiSlug too short), fall back to timestamp-only filename
  const filename = asciiSlug.length >= 3
    ? `${tsForFile}-${asciiSlug}.md`
    : `${tsForFile}.md`;

  // --- Target directory ---
  const targetDir = join(process.cwd(), 'src', 'content', lang, 'research');
  await mkdir(targetDir, { recursive: true });

  // --- Build frontmatter ---
  const tagsYaml = (tags as string[]).map((t) => `  - "${t}"`).join('\n');
  const frontmatter = [
    '---',
    `title: "${(title as string).replace(/"/g, '\\"')}"`,
    `date: "${isoDate}"`,
    `author: "${author}"`,
    `tags:`,
    tagsYaml || '  []',
    `industry_sector: ${industry_sector}`,
    `confidence_level: ${confidence_level}`,
    `status: ${status}`,
    summary ? `summary: "${(summary as string).replace(/"/g, '\\"')}"` : null,
    data_source ? `data_source: "${(data_source as string).replace(/"/g, '\\"')}"` : null,
    '---',
  ]
    .filter((line) => line !== null)
    .join('\n');

  const fileContent = `${frontmatter}\n\n${content}`;

  const filePath = join(targetDir, filename);
  await writeFile(filePath, fileContent, 'utf-8');

  return json(
    {
      success: true,
      file: filename,
      path: `src/content/${lang}/research/${filename}`,
      timestamp: isoDate,
    },
    201
  );
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
