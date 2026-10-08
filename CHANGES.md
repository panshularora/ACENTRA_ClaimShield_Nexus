# ClaimShield Nexus frontend redesign — CHANGES

Branch `ui/acentra-green`, frontend only (`frontend/`). The backend was not touched. Landing page,
routes and page flow are unchanged; the three.js landing scene is untouched.

## 1. Theme: colours and fonts, with sources

The visual system is `/workspace/claimshield-review/DESIGN_SYSTEM.md`. `frontend/src/styles/tokens.css`
is a verbatim copy of its `tokens.css` (source comments kept); everything else reads those tokens.
Canvas and SVG code (Cytoscape, Recharts) resolve them at runtime through `src/lib/theme.ts`
`token()` so CSS stays the single source of truth.

Brand evidence: acentra.com HTML and its HubSpot CSS, fetched 2026-10-08 (`claimshield-review/brand-evidence/`,
`REFERENCES.md` §palette). ClaimShield Nexus is its own product; it borrows the green palette only.

| Token | Hex | Evidence on acentra.com (selector, file) | Role here |
|---|---|---|---|
| `--neutral-950` → `--color-text` | `#042126` | `body{color:#042126}` (template_theme-overrides.min.css), 242× | Text, button text on green |
| `--green-500` → `--color-brand` | `#2bbc2b` | `.hs-button{background-color:#2bbc2b}`, `.tabber_section … a.active{border-bottom:3px solid #2bbc2b}` (theme-overrides, child_v2), 142× | Brand bar, primary button fill. Never text on white (2.52:1) |
| `--green-600` → `--color-brand-strong` | `#209b47` | `h1{color:#209b47}`, nav depth-1 links (theme-overrides), 39× | Active nav underline, selection rule (3.60:1, non-text) |
| `--green-700` → `--color-focus` | `#1c873e` | `.team-testimonials … h6{color}` eyebrows (template_blog, child_v2), 10× | Focus ring, subject node fill (4.58:1) |
| `--acentra-teal-deep` → `--graph-edge-referral` | `#005f68` | `h2{color:#005f68}` (theme-overrides; computed Roboto 700 40px) | Referral edges, chart series |
| `--color-link` | `#15497e` | `a{color:#15497e}` (theme-overrides), 13× | Links, chart focus series |
| Sand / Pale teal | `#f2ece4` / `#e4f3f2` | child_v2.css, template_blog.css | Owner / facility node fills |

Fonts:
- **Inter** (body on acentra.com: Google Fonts `family=Inter`, plus the `'Inter_regular'` `@font-face`
  alias in `template_child_v2.css`; computed `body` 18px). Self-hosted as `@fontsource-variable/inter` 5.3.0,
  SIL OFL 1.1. Used for all app text, with tabular numerals in tables, KPIs and charts.
- **Roboto Mono** 400 (`@fontsource/roboto-mono` 5.3.0, Apache 2.0) for case IDs, NPIs and claim IDs.
- Roboto (acentra.com headings, served by `/_hcms/googlefonts/Roboto/700.woff2`) is deliberately not used:
  the design system keeps one UI family. The self-hosted Roboto 700 was removed as unused.
- Landing and login keep their original fonts and styles (scoped in `styles/public.css`).

Risk (low/medium/high/critical) and patient harm use their own token ramps, never the brand green, and
always pair colour with a glyph and a label (`○ ◐ ● ◆`, `✚ Harm 4`).

## 2. Libraries

| Need | Choice | Why |
|---|---|---|
| Charts | **Recharts 3.10.1** | React 19 support, built-in `accessibilityLayer` (keyboard + ARIA), mature, composable axes. Runner-up visx (more code per chart). Charts are kept out of `Suspense` (Recharts bug #7463). Animation off. Every chart sits in `ChartFrame` with a title, a one-line text summary and a data table. |
| Network | **Cytoscape.js 3.34.3 + cytoscape-fcose 2.2.0**, used directly (no `react-cytoscapejs`) | Canvas renderer copes with 50–130 edges; fcose supports constraints (subject pinned at the centre). A thin React wrapper (`CaseNetworkGraph.tsx`) owns the instance. Lazy-loaded with the graph (≈568 kB chunk incl. fcose). |
| Node glyphs | **lucide-static 1.53.0** (ISC) | One SVG per node type, imported per file as raw strings and turned into data-URIs (`nodeIcons.ts`). |
| Fonts | `@fontsource-variable/inter`, `@fontsource/roboto-mono` | Self-hosted; no third-party font requests. |

Not installed: Tremor (patterns only), react-cytoscapejs, d3-force.

## 3. Network panel

- **One adapter for old and new API shapes.** `components/network/graphModel.ts` `normalizeNetwork(pack, ctx)`
  turns today's `/cases/{id}/network` payload, or the newer one from `fix/backend-p0`, into one model.
  New fields are optional in `api/types.ts` (`is_subject`, `in_case`, `alert_ids`, `flagged_paid`/`flagged_dollars`,
  `n_flagged_lines`, `hop`, `harm`; edges `id`, `direction`, `count`, `evidence_ids`, `inferred`) and used when
  present. Otherwise they are derived from the case: `in_case` from `case.entity_ids` and flagged lines,
  `alert_ids` from `alerts[].entity_id` / `evidence.peer_ids`, flagged dollars/lines from `/claims`.
  Duplicate and reverse-duplicate edges are merged into one edge with a `count`. Address/contact/TIN hub
  node types (`address`, `phone`, `bank`) are mapped, styled and in the legend already.
  `NETWORK_API.md` had not been published when this was written; field names may need a one-line rename.
- **Layout.** A deterministic concentric seed by hop (subject centre, hop 1, hop 2+; ring order by type), refined
  by fcose with `randomize: false` and the subject pinned. Same input, same picture, and the hop structure
  stays readable. A "Rings by hop distance" toggle shows the seed alone. Why not fcose alone: random starts
  moved the subject's neighbours between reloads; why not concentric alone: shared-address cliques overlap.
- **Encoding (design system §7).** Shape + glyph + quiet tint per type; the subject is the large green node with
  a risk-coloured ring (severity → risk level) and a harm dot when harm ≥ 3; the case's own providers get a heavy
  ink outline and a permanent label. Edges are solid, coloured by family (claim, shared, ownership, referral),
  arrows on owns/referral, width by `count`; dashes only for `inferred`.
- **Interaction.** Hover or select a node to keep its 2-hop neighbourhood and dim the rest to 15%; with no
  selection the subject's 2-hop is the focus. Clicking a node or link opens the side card (type, ID, risk badge,
  harm flag, in-case/context, flagged paid and lines, alert count, connection counts by kind, neighbours as
  buttons). Selecting an entity filters the claims table, findings and brief citations to it, with buttons to
  jump there and to open the provider profile. Zoom in/out, fit, centre-on-subject controls; edge-kind filter chips
  above the graph (entities left with no enabled link drop out, with a "N entities hidden" caption, so
  "structural links only" shows the ring itself); caption legend below listing only types present.
- **Keyboard and screen readers.** The canvas is `role="img"` with a text summary; the linked-entity list beside
  it (grouped by hop, every entity a button with relations and flagged dollars) is the keyboard route and stays
  in sync with the graph selection.

## 4. Workspace hierarchy

One scrolling case page instead of tabs, in the order an investigator reads a case:
1 header (subject, risk, harm, lane, SLA, metrics, assign, unmask) → 2 evidence (rank factors, findings with
peer comparison and lineage) → 3 network → 4 claims (timeline chart + claim lines) → 5 brief (cited sentences)
→ 6 decision (human only). A sticky section menu links the sections; old tab hashes (`#overview`, `#findings`,
`#timeline`) still land in the right place.

`DecisionBar` reads its actions, hints, ladder steps, default action and reason minimum from
`features/workspace/decisionConfig.ts` and accepts them as props, so the backend's revised decision set
(state escalation, manager-approved suspension recommendation, `needs_evidence` follow-ups) is a config change.
No decision semantics were changed.

## 5. Required fixes

| Fix | Commit |
|---|---|
| Rules-of-hooks error at `ManagerQueuePage.tsx:198` (useMemo after early return): guards moved below all hooks, rows memoised | `fix(queue): call useMemo before the early returns…` |
| 404 page for unknown routes (inside the shell, links back to work lists) | `fix(routing): 404 page and a one-request not-found state…` |
| Unknown case: brief/claims/timeline/network wait for the case (`enabled: caseQuery.isSuccess`), and 4xx answers are not retried (global `retry` in `main.tsx`). An unknown case now costs **one** request (`404 /cases/CASE-…`), was about ten | same |
| three.js / React Three Fiber only with the public pages: every route is lazy (`lazyRouteComponent`) | `perf(router): lazy-load every route…` |

**Main chunk size** (`vite build`, measured on HEAD `e20263c` and after):

| | Main chunk | gzip |
|---|---:|---:|
| Before (HEAD `e20263c`) | 1,361.81 kB | 379.50 kB |
| After lazy routes (commit `7213883`, on the old UI) | 328.48 kB | 104.82 kB |
| After the full redesign | 331.42 kB | 105.74 kB |

three.js + R3F now ship in a 935 kB chunk loaded only by `/` and `/login` (the login page reuses the scene).
Splitting routes also stopped `landing.css` from being global; the login page relied on it for its brand
lockup, so `LoginPage` now imports it (`fix(login): restore the brand lockup…`).
Recharts (≈368 kB) loads with the first page that has a chart; Cytoscape + fcose (≈568 kB) loads only when a
case network renders. Vite still prints its 500 kB advisory for those lazy chunks.

## 6. Domain audit fixes

From `claimshield-review/AUDIT.md`, each in its own commit:
1. **Branding.** No more "Acentra Health SIU" or the "Accelerating better outcomes" tagline (`index.html`
   title, app bar, login and landing lockups). The product is ClaimShield Nexus, labelled an Acentra Health
   code-a-thon prototype; the green theme stays.
2. **eCAMS.** The landing page says the product is *designed to sit downstream* of a claims system such as eCAMS,
   and that no integration exists in the prototype.
3. **Neutral pattern names** replace guilt-implying labels: e.g. "Genetic-testing mill" → "High genetic-testing
   order volume", "Urban ambulance mileage padding" → "Ambulance mileage above urban norm", "Doctor shopping" →
   "Many prescribers for one member", "Clone billing" → "Repeated identical claim amounts", "Unbundling (PTP)" →
   "NCCI procedure-pair edit", "Impossible daily hours" → "Daily hours over plausible cap"
   (`lib/format.ts` `PATTERN_LABELS`; they override the API's labels in findings, decision evidence, claim
   signals and the case drawer). The brief text comes from the backend and still uses its labels.
4. **Capacity label.** KPI, desk settings hint, lane chart summary and policy notes report the hours today's desk
   actually fills against the capacity set (e.g. "60 h queued · 40 h capacity"), with a warning when over and
   the reason (harm-priority cases are always queued; only part of their hours count).
5. **"Survival" wording.** F30/F60/F90 are described as the cumulative probability that the escalation event has
   already happened by each horizon (it is a CDF), not "survival", "hazard" or "still burning". "AI recommends
   today's 20" became "The ranking proposes today's 20". P(confirm), the 30/60/90 maths and escalation logic are
   unchanged; all score wording lives in `lib/scoreLabels.ts` for the coming backend change.

## 7. Accessibility

- Semantic tables (`<th scope>`), labelled controls, visible `:focus-visible` rings (`--focus-ring`), skip
  link, live regions for notices; drawers move focus to Close on open, close on Escape, and return focus on close.
- Charts: Recharts `accessibilityLayer` with a title, a text summary and a data table for each chart.
- Network: text summary plus the keyboard-accessible linked-entity list (see §3).
- Motion: only opacity/transform transitions (hover colour changes are instant; the design system's
  background-colour transitions were dropped), all disabled under `prefers-reduced-motion`.
- axe-core (WCAG 2.0/2.1/2.2 A+AA tags) runs on every route in the screenshot pass; results in
  `claimshield-review/screens/after/report.json`.

### Contrast (WCAG 2.2 AA), checked by `npm run check:contrast`

`frontend/scripts/check-contrast.mjs` resolves `tokens.css` (light and dark) and checks every pairing the UI
uses. Result: **134 pairs checked, 0 failed.** Informational pairs below 3:1 by design (decorative only): brand
`#2bbc2b` on white 2.52:1 (fills, never text), claim edges `--graph-edge-claim` (most numerous, kept quiet; the
kind is also in the hover label and legend), gridlines, and dimmed context at 15% opacity.

<details><summary>All checked pairs</summary>

| Theme | Group | Pair | FG | BG | Ratio | Needs | Result |
|---|---|---|---|---|---:|---:|---|
| light | Text (4.5) | text on bg | `#042126` | `#f1f6f6` | 15.39 | 4.5 | PASS |
| light | Text (4.5) | text on surface | `#042126` | `#ffffff` | 16.79 | 4.5 | PASS |
| light | Text (4.5) | text on surface-sunken | `#042126` | `#e8efef` | 14.41 | 4.5 | PASS |
| light | Text (4.5) | text on surface-hover | `#042126` | `#f4f8f8` | 15.69 | 4.5 | PASS |
| light | Text (4.5) | text-muted on bg | `#495b5b` | `#f1f6f6` | 6.57 | 4.5 | PASS |
| light | Text (4.5) | text-muted on surface | `#495b5b` | `#ffffff` | 7.17 | 4.5 | PASS |
| light | Text (4.5) | text-muted on surface-sunken | `#495b5b` | `#e8efef` | 6.15 | 4.5 | PASS |
| light | Text (4.5) | text-muted on surface-hover | `#495b5b` | `#f4f8f8` | 6.70 | 4.5 | PASS |
| light | Text (4.5) | text-subtle on bg | `#5d6e6f` | `#f1f6f6` | 4.90 | 4.5 | PASS |
| light | Text (4.5) | text-subtle on surface | `#5d6e6f` | `#ffffff` | 5.35 | 4.5 | PASS |
| light | Text (4.5) | text-subtle on surface-sunken | `#5d6e6f` | `#e8efef` | 4.59 | 4.5 | PASS |
| light | Text (4.5) | text-subtle on surface-hover | `#5d6e6f` | `#f4f8f8` | 5.00 | 4.5 | PASS |
| light | Text (4.5) | link on bg | `#15497e` | `#f1f6f6` | 8.42 | 4.5 | PASS |
| light | Text (4.5) | link on surface | `#15497e` | `#ffffff` | 9.19 | 4.5 | PASS |
| light | Text (4.5) | link on surface-sunken | `#15497e` | `#e8efef` | 7.88 | 4.5 | PASS |
| light | Text (4.5) | link on surface-hover | `#15497e` | `#f4f8f8` | 8.59 | 4.5 | PASS |
| light | Text (4.5) | brand-text on bg | `#1e672d` | `#f1f6f6` | 6.35 | 4.5 | PASS |
| light | Text (4.5) | brand-text on surface | `#1e672d` | `#ffffff` | 6.92 | 4.5 | PASS |
| light | Text (4.5) | brand-text on surface-sunken | `#1e672d` | `#e8efef` | 5.94 | 4.5 | PASS |
| light | Text (4.5) | brand-text on surface-hover | `#1e672d` | `#f4f8f8` | 6.47 | 4.5 | PASS |
| light | Text (4.5) | text on brand-subtle (selected row, chip on) | `#042126` | `#ecfced` | 15.76 | 4.5 | PASS |
| light | Text (4.5) | brand-text (chip ✓) on brand-subtle | `#1e672d` | `#ecfced` | 6.50 | 4.5 | PASS |
| light | Text (4.5) | text-on-brand on brand (primary button) | `#042126` | `#2bbc2b` | 6.66 | 4.5 | PASS |
| light | UI (3) | focus ring on bg | `#1c873e` | `#f1f6f6` | 4.20 | 3 | PASS |
| light | UI (3) | border-strong on bg | `#748484` | `#f1f6f6` | 3.58 | 3 | PASS |
| light | UI (3) | focus ring on surface | `#1c873e` | `#ffffff` | 4.58 | 3 | PASS |
| light | UI (3) | border-strong on surface | `#748484` | `#ffffff` | 3.91 | 3 | PASS |
| light | UI (3) | focus ring on surface-sunken | `#1c873e` | `#e8efef` | 3.93 | 3 | PASS |
| light | UI (3) | border-strong on surface-sunken | `#748484` | `#e8efef` | 3.35 | 3 | PASS |
| light | UI (3) | brand-strong (nav underline, selection rule) on surface | `#209b47` | `#ffffff` | 3.60 | 3 | PASS |
| light | UI (3) | brand-strong (chip on border) on brand-subtle | `#209b47` | `#ecfced` | 3.38 | 3 | PASS |
| light | Risk | risk-low-fg on risk-low-bg | `#2f4a67` | `#eef4fb` | 8.26 | 4.5 | PASS |
| light | Risk | risk-low-border on risk-low-bg | `#7089a4` | `#eef4fb` | 3.27 | 3 | PASS |
| light | Risk | risk-low-solid (graph ring) on surface | `#597797` | `#ffffff` | 4.66 | 3 | PASS |
| light | Risk | risk-medium-fg on risk-medium-bg | `#71440c` | `#fef2d9` | 7.46 | 4.5 | PASS |
| light | Risk | risk-medium-border on risk-medium-bg | `#b37d24` | `#fef2d9` | 3.22 | 3 | PASS |
| light | Risk | risk-medium-solid (graph ring) on surface | `#bf8105` | `#ffffff` | 3.30 | 3 | PASS |
| light | Risk | risk-high-fg on risk-high-bg | `#883500` | `#ffece0` | 7.17 | 4.5 | PASS |
| light | Risk | risk-high-border on risk-high-bg | `#b85207` | `#ffece0` | 4.31 | 3 | PASS |
| light | Risk | risk-high-solid (graph ring) on surface | `#b14c03` | `#ffffff` | 5.38 | 3 | PASS |
| light | Risk | risk-critical-fg on risk-critical-bg | `#7c1117` | `#fee9e8` | 9.25 | 4.5 | PASS |
| light | Risk | risk-critical-border on risk-critical-bg | `#9e2225` | `#fee9e8` | 6.66 | 3 | PASS |
| light | Risk | risk-critical-solid (graph ring) on surface | `#90101a` | `#ffffff` | 9.23 | 3 | PASS |
| light | Harm | harm-fg on harm-bg | `#752257` | `#fdeaf4` | 8.60 | 4.5 | PASS |
| light | Harm | harm-solid (graph dot) on surface | `#94296f` | `#ffffff` | 7.48 | 3 | PASS |
| light | Chart | chart-focus on surface | `#15497e` | `#ffffff` | 9.19 | 3 | PASS |
| light | Chart | chart-axis on surface | `#748484` | `#ffffff` | 3.91 | 3 | PASS |
| light | Chart | chart-baseline on surface | `#495b5b` | `#ffffff` | 7.17 | 3 | PASS |
| light | Chart | chart-comparison-line on surface | `#748484` | `#ffffff` | 3.91 | 3 | PASS |
| light | Chart | chart-label (tick text) on surface | `#495b5b` | `#ffffff` | 7.17 | 4.5 | PASS |
| dark | Text (4.5) | text on bg | `#e8efef` | `#042126` | 14.41 | 4.5 | PASS |
| dark | Text (4.5) | text on surface | `#e8efef` | `#132b2e` | 12.76 | 4.5 | PASS |
| dark | Text (4.5) | text on surface-sunken | `#e8efef` | `#031a1e` | 15.40 | 4.5 | PASS |
| dark | Text (4.5) | text on surface-hover | `#e8efef` | `#1a3337` | 11.46 | 4.5 | PASS |
| dark | Text (4.5) | text-muted on bg | `#bbc7c7` | `#042126` | 9.68 | 4.5 | PASS |
| dark | Text (4.5) | text-muted on surface | `#bbc7c7` | `#132b2e` | 8.57 | 4.5 | PASS |
| dark | Text (4.5) | text-muted on surface-sunken | `#bbc7c7` | `#031a1e` | 10.34 | 4.5 | PASS |
| dark | Text (4.5) | text-muted on surface-hover | `#bbc7c7` | `#1a3337` | 7.70 | 4.5 | PASS |
| dark | Text (4.5) | text-subtle on bg | `#a0aeaf` | `#042126` | 7.33 | 4.5 | PASS |
| dark | Text (4.5) | text-subtle on surface | `#a0aeaf` | `#132b2e` | 6.49 | 4.5 | PASS |
| dark | Text (4.5) | text-subtle on surface-sunken | `#a0aeaf` | `#031a1e` | 7.83 | 4.5 | PASS |
| dark | Text (4.5) | text-subtle on surface-hover | `#a0aeaf` | `#1a3337` | 5.83 | 4.5 | PASS |
| dark | Text (4.5) | link on bg | `#97c2f0` | `#042126` | 9.03 | 4.5 | PASS |
| dark | Text (4.5) | link on surface | `#97c2f0` | `#132b2e` | 7.99 | 4.5 | PASS |
| dark | Text (4.5) | link on surface-sunken | `#97c2f0` | `#031a1e` | 9.65 | 4.5 | PASS |
| dark | Text (4.5) | link on surface-hover | `#97c2f0` | `#1a3337` | 7.18 | 4.5 | PASS |
| dark | Text (4.5) | brand-text on bg | `#90e39a` | `#042126` | 10.91 | 4.5 | PASS |
| dark | Text (4.5) | brand-text on surface | `#90e39a` | `#132b2e` | 9.66 | 4.5 | PASS |
| dark | Text (4.5) | brand-text on surface-sunken | `#90e39a` | `#031a1e` | 11.65 | 4.5 | PASS |
| dark | Text (4.5) | brand-text on surface-hover | `#90e39a` | `#1a3337` | 8.67 | 4.5 | PASS |
| dark | Text (4.5) | text on brand-subtle (selected row, chip on) | `#e8efef` | `#1f3a25` | 10.66 | 4.5 | PASS |
| dark | Text (4.5) | brand-text (chip ✓) on brand-subtle | `#90e39a` | `#1f3a25` | 8.07 | 4.5 | PASS |
| dark | Text (4.5) | text-on-brand on brand (primary button) | `#042126` | `#2bbc2b` | 6.66 | 4.5 | PASS |
| dark | UI (3) | focus ring on bg | `#5cd370` | `#042126` | 8.80 | 3 | PASS |
| dark | UI (3) | border-strong on bg | `#6d7e7f` | `#042126` | 3.95 | 3 | PASS |
| dark | UI (3) | focus ring on surface | `#5cd370` | `#132b2e` | 7.79 | 3 | PASS |
| dark | UI (3) | border-strong on surface | `#6d7e7f` | `#132b2e` | 3.50 | 3 | PASS |
| dark | UI (3) | focus ring on surface-sunken | `#5cd370` | `#031a1e` | 9.40 | 3 | PASS |
| dark | UI (3) | border-strong on surface-sunken | `#6d7e7f` | `#031a1e` | 4.22 | 3 | PASS |
| dark | UI (3) | brand-strong (nav underline, selection rule) on surface | `#2bbc2b` | `#132b2e` | 5.90 | 3 | PASS |
| dark | UI (3) | brand-strong (chip on border) on brand-subtle | `#2bbc2b` | `#1f3a25` | 4.93 | 3 | PASS |
| dark | Risk | risk-low-fg on risk-low-bg | `#badbfe` | `#1e2f41` | 9.53 | 4.5 | PASS |
| dark | Risk | risk-low-border on risk-low-bg | `#619dda` | `#1e2f41` | 4.77 | 3 | PASS |
| dark | Risk | risk-low-solid (graph ring) on surface | `#619dda` | `#132b2e` | 5.20 | 3 | PASS |
| dark | Risk | risk-medium-fg on risk-medium-bg | `#f3d2a4` | `#3a2b16` | 9.48 | 4.5 | PASS |
| dark | Risk | risk-medium-border on risk-medium-bg | `#c08e43` | `#3a2b16` | 4.68 | 3 | PASS |
| dark | Risk | risk-medium-solid (graph ring) on surface | `#c08e43` | `#132b2e` | 5.09 | 3 | PASS |
| dark | Risk | risk-high-fg on risk-high-bg | `#fecbaf` | `#3e281b` | 9.43 | 4.5 | PASS |
| dark | Risk | risk-high-border on risk-high-bg | `#cf8358` | `#3e281b` | 4.62 | 3 | PASS |
| dark | Risk | risk-high-solid (graph ring) on surface | `#cf8358` | `#132b2e` | 4.98 | 3 | PASS |
| dark | Risk | risk-critical-fg on risk-critical-bg | `#fec8c3` | `#402624` | 9.38 | 4.5 | PASS |
| dark | Risk | risk-critical-border on risk-critical-bg | `#d47c76` | `#402624` | 4.57 | 3 | PASS |
| dark | Risk | risk-critical-solid (graph ring) on surface | `#d47c76` | `#132b2e` | 4.92 | 3 | PASS |
| dark | Harm | harm-fg on harm-bg | `#fac6e2` | `#3c2632` | 9.40 | 4.5 | PASS |
| dark | Harm | harm-solid (graph dot) on surface | `#c87ca8` | `#132b2e` | 4.89 | 3 | PASS |
| dark | Chart | chart-focus on surface | `#97c2f0` | `#132b2e` | 7.99 | 3 | PASS |
| dark | Chart | chart-axis on surface | `#6d7e7f` | `#132b2e` | 3.50 | 3 | PASS |
| dark | Chart | chart-baseline on surface | `#bbc7c7` | `#132b2e` | 8.57 | 3 | PASS |
| dark | Chart | chart-comparison-line on surface | `#7f8f90` | `#132b2e` | 4.41 | 3 | PASS |
| dark | Chart | chart-label (tick text) on surface | `#bbc7c7` | `#132b2e` | 8.57 | 4.5 | PASS |
| light | Status | info-fg on info-bg | `#15497e` | `#ebf5fd` | 8.32 | 4.5 | PASS |
| light | Status | info-border on info-bg | `#557ea8` | `#ebf5fd` | 3.85 | 3 | PASS |
| light | Status | success-fg on success-bg | `#1e672d` | `#ecfced` | 6.50 | 4.5 | PASS |
| light | Status | success-border on success-bg | `#209b47` | `#ecfced` | 3.38 | 3 | PASS |
| light | Status | warning-fg on warning-bg | `#71440c` | `#fef2d9` | 7.46 | 4.5 | PASS |
| light | Status | warning-border on warning-bg | `#b37d24` | `#fef2d9` | 3.22 | 3 | PASS |
| light | Status | danger-fg on danger-bg | `#972622` | `#feebe9` | 6.98 | 4.5 | PASS |
| light | Status | danger-border on danger-bg | `#b33832` | `#feebe9` | 5.18 | 3 | PASS |
| light | Chart | chart-1 on surface | `#209b47` | `#ffffff` | 3.60 | 3 | PASS |
| light | Chart | chart-2 on surface | `#0072b2` | `#ffffff` | 5.19 | 3 | PASS |
| light | Chart | chart-3 on surface | `#1d3b70` | `#ffffff` | 10.98 | 3 | PASS |
| light | Chart | chart-4 on surface | `#005f68` | `#ffffff` | 7.40 | 3 | PASS |
| light | Chart | chart-5 on surface | `#8c5a2b` | `#ffffff` | 5.81 | 3 | PASS |
| light | Graph | provider stroke on its fill | `#495b5b` | `#e8efef` | 6.15 | 3 | PASS |
| light | Graph | provider stroke on canvas | `#495b5b` | `#ffffff` | 7.17 | 3 | PASS |
| light | Graph | owner stroke on its fill | `#71604a` | `#f2ece4` | 5.15 | 3 | PASS |
| light | Graph | owner stroke on canvas | `#71604a` | `#ffffff` | 6.04 | 3 | PASS |
| light | Graph | facility stroke on its fill | `#11615b` | `#e4f3f2` | 6.38 | 3 | PASS |
| light | Graph | facility stroke on canvas | `#11615b` | `#ffffff` | 7.28 | 3 | PASS |
| light | Graph | address stroke on its fill | `#5d6e6f` | `#f8fbfb` | 5.14 | 3 | PASS |
| light | Graph | address stroke on canvas | `#5d6e6f` | `#ffffff` | 5.35 | 3 | PASS |
| light | Graph | phone stroke on its fill | `#5d6e6f` | `#f8fbfb` | 5.14 | 3 | PASS |
| light | Graph | phone stroke on canvas | `#5d6e6f` | `#ffffff` | 5.35 | 3 | PASS |
| light | Graph | bank stroke on its fill | `#2f4445` | `#e8efef` | 8.86 | 3 | PASS |
| light | Graph | bank stroke on canvas | `#2f4445` | `#ffffff` | 10.33 | 3 | PASS |
| light | Graph | member stroke on its fill | `#748484` | `#ffffff` | 3.91 | 3 | PASS |
| light | Graph | member stroke on canvas | `#748484` | `#ffffff` | 3.91 | 3 | PASS |
| light | Graph | node glyph on provider fill | `#2f4445` | `#e8efef` | 8.86 | 3 | PASS |
| light | Graph | subject glyph on subject fill | `#ffffff` | `#1c873e` | 4.58 | 4.5 | PASS |
| light | Graph | in-case outline (text) on canvas | `#042126` | `#ffffff` | 16.79 | 3 | PASS |
| light | Graph | node label on label halo | `#042126` | `#ffffff` | 16.79 | 4.5 | PASS |
| light | Graph | edge shared on canvas | `#748484` | `#ffffff` | 3.91 | 3 | PASS |
| light | Graph | edge ownership on canvas | `#2f4445` | `#ffffff` | 10.33 | 3 | PASS |
| light | Graph | edge referral on canvas | `#005f68` | `#ffffff` | 7.40 | 3 | PASS |

</details>

## 8. Deviations from the design system

- The case's own providers get a 2.5px ink outline and a permanent label (§7 has no "in case" encoding; the audit
  lists case-vs-context as the main linkage gap).
- With nothing selected, the subject's 2-hop neighbourhood is the focus (§7.4 dims only on hover).
- Graph selection uses a `.picked` class instead of Cytoscape's `:selected`, because selection is driven from
  React state (list and graph stay in sync).
- The side card keeps the cross-filter buttons (claim lines, findings, brief citations, provider profile) in place
  of §7.8's "Open evidence" / "Center graph here"; centring is in the graph toolbar.

## 9. Verification

- `npm run build` (tsc -b + vite build): passes. `npm run lint` (oxlint): 0 errors, 1 warning
  (`react(only-export-components)` in `src/auth/AuthProvider.tsx`, untouched). `npm run typecheck`: passes.
  `npm run check:contrast`: 134/134 pass. The frontend has no unit-test suite.
- Headless Playwright + axe-core (`/workspace/csui-scratch/pw/screens-after.mjs`) logs in as manager,
  investigator, auditor and analyst and visits every route at 1440px (dashboards also at 390px). After login there
  are **no console errors** on any app route and **0 axe violations** (WCAG 2.0/2.1/2.2 A/AA tags) on every page
  checked, including drawers and both 404 states. The only console output comes from the public login page
  itself: the pre-login `401 /auth/me` and three.js's `THREE.Clock` deprecation warning (both pre-existing,
  audit (d)17). The unknown-case page logs its one expected `404`.
- Screens: `/workspace/claimshield-review/screens/after/`, named like `screens/baseline/` (01–62), plus
  `08_/09_manager_queue_*_390.png` and `12_/13_investigator_cases_*_390.png`, and `report.json`.
  Section shots (`*_findings`, `*_brief`, `*_claims`, `*_timeline`, `*_network*`, `*_decide`) are crops of the
  matching section on the single-page workspace. Landing and login are unchanged apart from the copy fixes in §6.

## 10. Known gaps

See `frontend/API_GAPS.md`. In short: no shared-contact/owner edges, clique addresses, undirected referrals and
no per-node case data in today's network API (the UI derives what it can); no claims or findings endpoint for
context entities; no graph evidence kinds in the brief; the harm reserve is not in the run payload; the decision
bar still locks after the first decision (backend change pending); `/auth/me` logs a 401 before login.
