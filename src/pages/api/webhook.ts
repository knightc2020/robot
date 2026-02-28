export const prerender = false;
import fs from 'node:fs';
import path from 'node:path';
import type { APIRoute } from 'astro';

export const POST: APIRoute = async ({ request }) => {
  try {
    const data = await request.json();
    const { title, original_title, source_url, content_markdown, industry_sector = "humanoid" } = data;

    const now = new Date();
    const isoDate = now.toISOString();
    const fileName = `arxiv-${now.getTime()}.md`;

    const fileContent = `---
title: "${title}"
date: "${isoDate}"
industry_sector: "${industry_sector}"
status: "published"
confidence_level: "estimated"
author: "Editorial Team"
summary: "${title.slice(0, 100)}..."
---

> **原文链接:** [${original_title}](${source_url})

${content_markdown}
`;

    const dirPath = path.resolve('src/content/cn/research'); 
    if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });
    fs.writeFileSync(path.join(dirPath, fileName), fileContent, 'utf-8');

    return new Response(JSON.stringify({ message: "Success!" }), { status: 200 });
  } catch (error) {
    return new Response(JSON.stringify({ error: String(error) }), { status: 500 });
  }
};