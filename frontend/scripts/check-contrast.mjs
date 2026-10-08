#!/usr/bin/env node
// Resolves the custom properties in src/styles/tokens.css and checks WCAG 2.2 contrast for every
// colour pairing the UI relies on. Prints a markdown table; exits 1 if a required pair fails.
// Usage: node scripts/check-contrast.mjs [--markdown]
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const css = readFileSync(fileURLToPath(new URL("../src/styles/tokens.css", import.meta.url)), "utf8").replace(
  /\/\*[\s\S]*?\*\//g,
  "",
);

function block(selector) {
  const start = css.indexOf(`${selector} {`);
  if (start < 0) return {};
  const body = css.slice(start, css.indexOf("\n}", start));
  return Object.fromEntries([...body.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
}

const ROOT = block(":root");
const THEMES = { light: ROOT, dark: { ...ROOT, ...block('[data-theme="dark"]') } };

function resolve(value, table, depth = 0) {
  const ref = /^var\((--[\w-]+)\)$/.exec(value.trim());
  if (!ref) return value.trim();
  if (depth > 20 || !(ref[1] in table)) throw new Error(`Cannot resolve ${value}`);
  return resolve(table[ref[1]], table, depth + 1);
}

function rgb(color) {
  const hex = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(color);
  if (hex) {
    const h = hex[1].length === 3 ? [...hex[1]].map((c) => c + c).join("") : hex[1];
    return [0, 2, 4].map((i) => Number.parseInt(h.slice(i, i + 2), 16));
  }
  const fn = /^rgba?\(([^)]+)\)$/i.exec(color);
  if (fn) return fn[1].split(/[\s,/]+/).slice(0, 3).map(Number);
  throw new Error(`Unsupported colour ${color}`);
}

function luminance(color) {
  const [r, g, b] = rgb(color).map((v) => {
    const c = v / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(fg, bg) {
  const [a, b] = [luminance(fg), luminance(bg)].sort((x, y) => y - x);
  return (a + 0.05) / (b + 0.05);
}

const rows = [];
function check(theme, group, name, fg, bg, need) {
  const table = THEMES[theme];
  const f = resolve(table[fg] ?? fg, table);
  const b = resolve(table[bg] ?? bg, table);
  const r = ratio(f, b);
  rows.push({ theme, group, name, f, b, r, need, pass: r >= need - 1e-9 });
}

for (const theme of ["light", "dark"]) {
  const surfaces = ["--color-bg", "--color-surface", "--color-surface-sunken", "--color-surface-hover"];
  for (const text of ["--color-text", "--color-text-muted", "--color-text-subtle", "--color-link", "--color-brand-text"]) {
    for (const bg of surfaces) check(theme, "Text (4.5)", `${text.slice(8)} on ${bg.slice(8)}`, text, bg, 4.5);
  }
  check(theme, "Text (4.5)", "text on brand-subtle (selected row, chip on)", "--color-text", "--color-brand-subtle", 4.5);
  check(theme, "Text (4.5)", "brand-text (chip ✓) on brand-subtle", "--color-brand-text", "--color-brand-subtle", 4.5);
  check(theme, "Text (4.5)", "text-on-brand on brand (primary button)", "--color-text-on-brand", "--color-brand", 4.5);
  for (const bg of ["--color-bg", "--color-surface", "--color-surface-sunken"]) {
    check(theme, "UI (3)", `focus ring on ${bg.slice(8)}`, "--color-focus", bg, 3);
    check(theme, "UI (3)", `border-strong on ${bg.slice(8)}`, "--color-border-strong", bg, 3);
  }
  check(theme, "UI (3)", "brand-strong (nav underline, selection rule) on surface", "--color-brand-strong", "--color-surface", 3);
  check(theme, "UI (3)", "brand-strong (chip on border) on brand-subtle", "--color-brand-strong", "--color-brand-subtle", 3);
  for (const level of ["low", "medium", "high", "critical"]) {
    check(theme, "Risk", `risk-${level}-fg on risk-${level}-bg`, `--risk-${level}-fg`, `--risk-${level}-bg`, 4.5);
    check(theme, "Risk", `risk-${level}-border on risk-${level}-bg`, `--risk-${level}-border`, `--risk-${level}-bg`, 3);
    check(theme, "Risk", `risk-${level}-solid (graph ring) on surface`, `--risk-${level}-solid`, "--color-surface", 3);
  }
  check(theme, "Harm", "harm-fg on harm-bg", "--harm-fg", "--harm-bg", 4.5);
  check(theme, "Harm", "harm-solid (graph dot) on surface", "--harm-solid", "--color-surface", 3);
  for (const part of ["focus", "axis", "baseline", "comparison-line"]) {
    check(theme, "Chart", `chart-${part} on surface`, `--chart-${part}`, "--color-surface", 3);
  }
  check(theme, "Chart", "chart-label (tick text) on surface", "--chart-label", "--color-surface", 4.5);
}

for (const status of ["info", "success", "warning", "danger"]) {
  check("light", "Status", `${status}-fg on ${status}-bg`, `--color-${status}-fg`, `--color-${status}-bg`, 4.5);
  check("light", "Status", `${status}-border on ${status}-bg`, `--color-${status}-border`, `--color-${status}-bg`, 3);
}
for (let i = 1; i <= 5; i += 1) check("light", "Chart", `chart-${i} on surface`, `--chart-${i}`, "--color-surface", 3);
for (const type of ["provider", "owner", "facility", "address", "phone", "bank", "member"]) {
  check("light", "Graph", `${type} stroke on its fill`, `--graph-node-${type}-stroke`, `--graph-node-${type}-fill`, 3);
  check("light", "Graph", `${type} stroke on canvas`, `--graph-node-${type}-stroke`, "--graph-bg", 3);
}
check("light", "Graph", "node glyph on provider fill", "--graph-node-glyph", "--graph-node-provider-fill", 3);
check("light", "Graph", "subject glyph on subject fill", "--graph-subject-glyph", "--graph-subject-fill", 4.5);
check("light", "Graph", "in-case outline (text) on canvas", "--color-text", "--graph-bg", 3);
check("light", "Graph", "node label on label halo", "--color-text", "--graph-label-halo", 4.5);
for (const family of ["shared", "ownership", "referral"]) {
  check("light", "Graph", `edge ${family} on canvas`, `--graph-edge-${family}`, "--graph-bg", 3);
}

const header = "| Theme | Group | Pair | FG | BG | Ratio | Needs | Result |\n|---|---|---|---|---|---:|---:|---|";
const lines = rows.map(
  (r) => `| ${r.theme} | ${r.group} | ${r.name} | \`${r.f}\` | \`${r.b}\` | ${r.r.toFixed(2)} | ${r.need} | ${r.pass ? "PASS" : "FAIL"} |`,
);
const failed = rows.filter((r) => !r.pass);
if (process.argv.includes("--markdown")) console.log([header, ...lines].join("\n"));
console.log(`\n${rows.length} pairs checked, ${failed.length} failed.`);
for (const r of failed) console.log(`FAIL ${r.theme} ${r.name}: ${r.r.toFixed(2)} < ${r.need}`);
process.exit(failed.length > 0 ? 1 : 0);
