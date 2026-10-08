/**
 * Runtime access to the design tokens in styles/tokens.css.
 *
 * Canvas (Cytoscape) and SVG chart props need concrete colour strings, so the
 * CSS custom properties stay the single source of truth and are read here.
 */
export type TokenName = `--${string}`;

const cache = new Map<TokenName, string>();

export function token(name: TokenName): string {
  const hit = cache.get(name);
  if (hit !== undefined) return hit;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  cache.set(name, value);
  return value;
}
