/**
 * The single publication predicate for every public content entry point.
 * Missing and non-published states are deliberately private.
 */
export function isPublishableContent<T extends { data: { status?: string } }>(entry: T): boolean {
  return entry.data.status === 'published';
}
