const DAY_MS = 24 * 60 * 60 * 1000;

type ResearchPost = {
  id: string;
  data: {
    date: Date;
    status: 'draft' | 'review' | 'published';
    paper_published_at?: Date;
    importance_score?: number;
    featured?: boolean;
  };
};

function publishedAt(post: ResearchPost): number {
  return (post.data.paper_published_at ?? post.data.date).getTime();
}

export function sortResearchByNewest<T extends ResearchPost>(posts: T[]): T[] {
  return [...posts].sort((a, b) => publishedAt(b) - publishedAt(a));
}

export function splitResearchFeed<T extends ResearchPost>(
  posts: T[],
  options: { featuredLimit?: number; featuredWindowDays?: number; now?: Date } = {},
): { recommended: T[]; latest: T[] } {
  const featuredLimit = options.featuredLimit ?? 3;
  const featuredWindowDays = options.featuredWindowDays ?? 7;
  const now = options.now ?? new Date();
  const published = posts.filter((post) => post.data.status === 'published');
  const windowStart = now.getTime() - featuredWindowDays * DAY_MS;

  const recommended = published
    .filter((post) => {
      const score = post.data.importance_score ?? 0;
      return publishedAt(post) >= windowStart && (post.data.featured || score > 0);
    })
    .sort((a, b) => {
      const featuredDelta = Number(Boolean(b.data.featured)) - Number(Boolean(a.data.featured));
      if (featuredDelta !== 0) return featuredDelta;

      const scoreDelta = (b.data.importance_score ?? 0) - (a.data.importance_score ?? 0);
      return scoreDelta !== 0 ? scoreDelta : publishedAt(b) - publishedAt(a);
    })
    .slice(0, featuredLimit);

  const recommendedIds = new Set(recommended.map((post) => post.id));
  const latest = sortResearchByNewest(published).filter((post) => !recommendedIds.has(post.id));

  return { recommended, latest };
}
