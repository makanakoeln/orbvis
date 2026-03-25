/** Sanitize a raw string into a valid board ID: spaces → hyphens, strip invalid chars. */
export function sanitizeBoardName(raw: string): string {
  return raw.replace(/ /g, '-').replace(/[^a-zA-Z0-9_-]/g, '');
}

/** Convert a hyphen/underscore-separated slug to Title Case display name. */
export function slugToTitleCase(slug: string): string {
  return slug.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
