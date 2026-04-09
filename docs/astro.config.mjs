import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// Local dev defaults to root path; production keeps GitHub Pages subpath.
const isProduction = process.env.NODE_ENV === 'production';
const docsBase = process.env.DOCS_BASE ?? '/';

// https://astro.build/config
export default defineConfig({
  site: 'https://hey-granth.github.io',
  base: docsBase,
  integrations: [
    starlight({
      title: 'codectx',
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/hey-granth/codectx' },
      ],
      sidebar: [
        {
          label: 'Introduction',
          items: [
            { label: 'What is codectx', link: '/introduction/what-is-codectx/' },
            { label: 'Why it exists', link: '/introduction/why-it-exists/' },
          ],
        },
        {
          label: 'Getting Started',
          items: [
            { label: 'Installation', link: '/getting-started/installation/' },
            { label: 'Quick Start', link: '/getting-started/quick-start/' },
            { label: 'Basic Usage', link: '/getting-started/basic-usage/' },
          ],
        },
        {
          label: 'Guides',
          items: [
            { label: 'Using CONTEXT.md effectively', link: '/guides/using-context-effectively/' },
            { label: 'Best Practices', link: '/guides/best-practices/' },
            { label: 'Configuration', link: '/guides/configuration/' },
            { label: 'Docker', link: '/guides/docker/' },
          ],
        },
        {
          label: 'Reference',
          items: [
            { label: 'CLI Reference', link: '/reference/cli-reference/' },
            { label: 'Architecture Overview', link: '/reference/architecture-overview/' },
          ],
        },
        {
          label: 'Advanced',
          items: [
            { label: 'How the ranking system works', link: '/advanced/ranking-system/' },
            { label: 'Token compression strategy', link: '/advanced/token-compression/' },
            { label: 'Dependency graph design', link: '/advanced/dependency-graph/' },
          ],
        },
        {
          label: 'Community',
          items: [
            { label: 'Contributing', link: '/community/contributing/' },
            { label: 'FAQ', link: '/community/faq/' },
          ],
        },
        {
          label: 'Comparison',
          items: [
            { label: 'codectx vs existing tools', link: '/comparison/' },
          ],
        },
      ],
    }),
  ],
});
