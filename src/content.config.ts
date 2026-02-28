import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

/**
 * Shared schema for automation-ready frontmatter.
 * Designed for AI Agent (OpenClaw) auto-generation compatibility.
 */
const articleSchema = z.object({
  title: z.string(),
  date: z.string().datetime({ offset: true }),
  updated: z.string().datetime({ offset: true }).optional(),
  author: z.string().default('Editorial Team'),
  tags: z.array(z.string()).default([]),
  industry_sector: z.enum([
    'humanoid',
    'industrial-arm',
    'amr',
    'agv',
    'surgical',
    'agri-robot',
    'drone',
    'components',
    'software',
    'general',
  ]),
  data_source: z.string().optional(),
  confidence_level: z.enum(['verified', 'estimated', 'speculative']).default('estimated'),
  status: z.enum(['draft', 'review', 'published']).default('draft'),
  summary: z.string().optional(),
  cover_image: z.string().optional(),
});

/** Career-specific schema extends base with mentorship fields */
const careerSchema = articleSchema.extend({
  career_level: z.enum(['intern', 'junior', 'mid', 'senior', 'lead', 'executive']).optional(),
  skill_domain: z.array(z.string()).default([]),
  salary_range: z.string().optional(),
  region: z.string().optional(),
});

// --- EN Collections ---
const enResearch = defineCollection({
  type: 'content',
  schema: articleSchema,
});

const enCareer = defineCollection({
  type: 'content',
  schema: careerSchema,
});

// --- CN Collections ---
const cnResearch = defineCollection({
  type: 'content',
  schema: articleSchema,
});

const cnCareer = defineCollection({
  type: 'content',
  schema: careerSchema,
});

// --- Top-level stubs (suppress Astro v5 auto-generation warning) ---
const en = defineCollection({
  loader: glob({ pattern: '_stub.md', base: './src/content/en' }),
});
const cn = defineCollection({
  loader: glob({ pattern: '_stub.md', base: './src/content/cn' }),
});

export const collections = {
  en,
  cn,
  'en/research': enResearch,
  'en/career': enCareer,
  'cn/research': cnResearch,
  'cn/career': cnCareer,
};
