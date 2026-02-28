import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import mdx from '@astrojs/mdx';
import node from '@astrojs/node';

export default defineConfig({
  // 1. 顶层 server 配置 (Astro 5 推荐做法)
  server: {
    host: true,
    port: 4321,
    allowedHosts: true // 👈 核心：允许所有外部域名（包括隧道域名）
  },

  output: 'server',
  adapter: node({
    mode: 'standalone',
  }),

  integrations: [mdx()],
  
  vite: {
    plugins: [tailwindcss()],
    server: {
      // 2. Vite 内部双重保险
      host: true,
      allowedHosts: true 
    }
  },
  
  i18n: {
    defaultLocale: 'cn',
    locales: ['cn', 'en'],
    routing: {
      prefixDefaultLocale: true,
    },
  },
});