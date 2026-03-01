import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import mdx from '@astrojs/mdx';

export default defineConfig({
  integrations: [mdx()],

  vite: {
    plugins: [tailwindcss()],
  },

  i18n: {
    defaultLocale: 'cn',
    locales: ['cn', 'en'],
    routing: {
      prefixDefaultLocale: true,
    },
  },
});