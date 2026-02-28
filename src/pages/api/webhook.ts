export const prerender = false;
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import type { APIRoute } from 'astro';

function deriveSlug(sourceUrl?: string, title?: string): string {
  if (sourceUrl) {
    const arxivMatch = sourceUrl.match(/arxiv\.org\/abs\/([^\s/?#]+)/);
    if (arxivMatch) return `arxiv-${arxivMatch[1].replace(/[/.]/g, '-')}`;

    return createHash('sha256').update(sourceUrl).digest('hex').slice(0, 12);
  }
  if (title) {
    const ascii = title
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/[\s_]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 60);
    if (ascii.length >= 3) return ascii;
  }
  return `paper-${Date.now()}`;
}

export const POST: APIRoute = async ({ request }) => {
  try {
    const data = await request.json();
    const { title, original_title, source_url, content_markdown, industry_sector = "humanoid" } = data;

    if (!title) {
      return json({ error: '`title` is required' }, 400);
    }

    const slug = deriveSlug(source_url, title);
    const fileName = `${slug}.md`;

    const dirPath = path.resolve('src/content/cn/research');
    if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });

    const filePath = path.join(dirPath, fileName);
    if (fs.existsSync(filePath)) {
      return json({ duplicate: true, file: fileName, message: `Article already exists: ${fileName}` }, 409);
    }

    const isoDate = new Date().toISOString();
    const fileContent = `---
title: "${title.replace(/"/g, '\\"')}"
date: "${isoDate}"
industry_sector: "${industry_sector}"
status: "published"
confidence_level: "estimated"
author: "Editorial Team"
summary: "${title.slice(0, 100).replace(/"/g, '\\"')}..."
source_url: "${source_url ?? ''}"
---

> **原文链接:** [${original_title}](${source_url})

${content_markdown}
`;

    fs.writeFileSync(filePath, fileContent, 'utf-8');
    return json({ success: true, file: fileName, path: `src/content/cn/research/${fileName}` }, 201);
  } catch (error) {
    return json({ error: String(error) }, 500);
  }
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}