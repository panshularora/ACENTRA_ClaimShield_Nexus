# ClaimShield Nexus: frontend redesign references

Research date: Thursday 8 Oct 2026 (IST). No code was changed anywhere. This file is the only output.

How to read the tags:
- **Confirmed**: I saw it on the live page, docs, npm registry, GitHub API or a screenshot I took of the live page. The link is given.
- **Inferred**: my own reasoning from visuals or indirect evidence.
- **Unknown**: I could not verify it.

npm timestamps are UTC as returned by the registry. Where the date is different in IST, the IST date is given too.

---

## Summary

1. **Charts: Recharts 3.10.1** (MIT, published 2026-07-25 UTC). SVG, `accessibilityLayer` (keyboard navigation and ARIA) is on by default since v3, peer deps include React 19, and it is what shadcn/ui charts are built on.
2. **Graph: Cytoscape.js 3.34.3** (MIT, published 2026-09-07 UTC), used directly through a small `useEffect` wrapper, not `react-cytoscapejs`. It has a typed stylesheet with node shapes and edge line styles per type, a built-in `concentric` layout that fits a 2-hop ego view, `closedNeighborhood()` for highlighting, and only 17 open issues.
3. **Runners-up:** visx 4.0.0 for charts, if bundle size beats build speed. Sigma.js plus graphology for the graph, if the graph grows past a few thousand nodes or once `@react-sigma/core` supports sigma v4 (released today, 8 Oct 2026).
4. **Patterns to borrow:** SAS Visual Investigator's score breakdown next to the alert queue; Linkurious's hidden-neighbour count badge and selective expand; Bloom's legend-driven filtering that greys out filtered items; Grafana's legend-as-table with Mean and Max columns.
5. **Palette:** the Acentra site CSS uses a deep teal-ink `#042126` with greens `#2BBC2B`, `#209B47` and `#1C873E` (all Confirmed). For green text on white, use `#1C873E` (4.58:1). Use `#2BBC2B` only for fills, accents or on dark backgrounds.

---

## Part 1: Reference dashboards

| # | Name | Exact URL visited | What makes it read as professional | One idea to borrow | ClaimShield screen |
|---|---|---|---|---|---|
| 1 | SAS Visual Investigator (alert triage) | https://www.sas.com/en_us/software/intelligence-analytics-visual-investigator.html | The product screenshot on the page (Confirmed, my capture) shows: a dense alert grid sorted by Score descending; mono-style IDs; right-aligned score; small status icons; a split view below with **Scorecard / Alert Information / Network** panels; a "1 - 10 of 10 items" pager. A second shot shows "Results by Rule" with Records and Distinct Entities counts, and a "Personal Metrics" donut (7 alerts; avg time per alert 18 min). The palette is restrained: white, grey rules and one blue accent (Inferred from the screenshot). | **Scorecard that breaks the total score into named scenario contributions.** The screenshot shows 1,150 = "Too Many Claims From Same IP Address" 600 + "Abnormally Large Reserve" 550. | Investigator workspace: queue row, then the case brief "Why ranked" block. "Results by Rule" maps to the policy-analyst rules page. |
| 2 | Unit21 Case Management | https://www.unit21.ai/products/case-management | The page copy (Confirmed) describes dashboards for "alert-to-case-to-SAR conversion, case closure rates, and time spent per investigation", "precision-based sampling" for QA, and "All actions are logged with a complete audit trail". The hero visuals are stylised mock cards ("Actions: Close Alert / Confirm Suspicious Activity / Create Case / Escalate"), not a real product screenshot (Confirmed, my capture). | **A conversion funnel as the headline metric** (alerts → cases → referrals), plus a fixed set of decision verbs. | Outcomes/metrics page (funnel). Decision bar (verbs). Auditor log (every action logged). |
| 3 | Grafana Play: "Risk & Fraud Posture" and "Grafana Bank: Executive Overview" | https://play.grafana.org/d/appenv-banking-risk-fraud/risk-and-fraud-posture and https://play.grafana.org/d/appenv-banking-exec-overview/banking-executive-overview | Live public dashboards (Confirmed, my capture). They use a 12-column grid of equal-height panels; unit-aware number formatting (`$41.7K`, `4.75 s`, `97.3%`); stat tiles with sparklines; stacked bars split by risk tier (high, low, medium); and a **legend rendered as a table with Mean and Max columns**. One global time-range picker ("Last 6 hours") drives every panel. Saturated full-colour stat backgrounds are a pattern to *avoid* for a calm investigator tool (Inferred). | **Legend-as-table with Mean and Max values, and one global time-range control.** | Outcomes/metrics page: the precision/hit-rate-over-time chart and the dollars-recovered trend. |
| 4 | shadcn/ui Dashboard example | https://ui.shadcn.com/examples/dashboard | Live demo (Confirmed, my capture). It has 4 KPI cards (label, big tabular number, small delta chip like "+12.5%" or "-20%", one-line explanation); an area chart with a segmented range switch (3 months, 30 days, 7 days); and a data table with status chips (Done / In Process), right-aligned numeric columns (Target, Limit), inline "Assign reviewer" select, "Customize Columns", "0 of 68 row(s) selected", and "Page 1 of 7". It is neutral greyscale with one accent. Its charts are "Built using Recharts", now Recharts v3 (Confirmed: https://ui.shadcn.com/docs/components/chart), and its tables are "built using TanStack Table" (Confirmed: https://ui.shadcn.com/docs/components/data-table). | **KPI card anatomy: label, number, delta chip, one-line "so what".** Same stack as ClaimShield (TanStack Table plus Recharts). | Outcomes page header row ($ recovered, FP rate in top-K, hit rate, open cases). SIU manager page. |
| 5 | shadcn/ui Tasks example | https://ui.shadcn.com/examples/tasks | Live demo (Confirmed, my capture). Filter input plus faceted filter buttons (Status, Priority); a "View" column toggle; sortable headers with sort glyphs; a type chip before the title (Bug, Feature, Documentation); status with an icon plus text (not colour alone); priority shown with arrows. | **Faceted filter toolbar (status, priority, rule) above a TanStack table**, with status shown as icon plus text for a11y. | SIU manager queue page and the left ranked queue. Auditor log page (filter by actor, action, case). |
| 6 | Tabler (open-source admin dashboard) | https://preview.tabler.io/ | Live demo (Confirmed, my capture). Uppercase small-caps metric labels; large numbers with coloured delta and arrow ("2% ↑", "-1% ↓"); a per-card "Last 7 days" period selector; sparklines inside KPI cards; a thin progress bar under metrics. Some cards are decorative (illustration, social tiles); skip those (Inferred). | **Sparkline inside the KPI card** to show trend without a full chart. | Outcomes page KPIs. SIU manager capacity summary. |
| 7 | Tremor | https://tremor.so/ | Live page (Confirmed, my capture). Headline value above the chart ("$328,505.10"); a small inline legend at top right; light gridlines; tabbed bar chart (Europe / North America) with a breakdown list beneath ("Successful 263 / Refunded 18 / Fraudulent 9"). The site says it is "Built on Recharts and Radix UI" (Confirmed). The npm package `@tremor/react` 3.18.7 has peer `react: ^18.0.0` and was last published 2025-01-13 (Confirmed, npm), so do **not** install it in a React 19 app. Copy the patterns, not the package (Inferred). | **Chart card with the headline number on top and a categorical breakdown list under the chart.** | Outcomes page: dollars-recovered card with a breakdown by scheme type. |

Checked but not used as references:
- **Palantir Gotham** (https://www.palantir.com/platforms/gotham/): the fetch returned only the page title. I saw no public UI images. Unknown.
- **Quantexa** (https://www.quantexa.com/): the homepage was fetched (Confirmed: positioning on entity resolution and graph context for fraud, including Zurich claims). No usable product UI screenshot came through. Unknown.
- **Sardine, Alloy, Hummingbird, Sift, Datadog**: not checked within the time spent. Unknown.

Notes common to the strong examples (Inferred, from the screenshots above):
- They use one typeface, tabular numbers, right-aligned numeric columns and left-aligned text.
- There is one accent colour. Red, amber and green are kept for status and risk only, and status always has an icon or text label as well as the colour.
- Numbers are formatted to the reader's precision ($41.7K, not $41,712.38) in tiles. Full precision goes in tables and tooltips.
- The table footer always shows the selection count, page position and rows-per-page control.
- Detail panes sit next to or below the list (SAS VI split view), so triage happens without page navigation.

---

## Part 2: Link-analysis graph UIs

### 2.1 Linkurious Enterprise (user manual v4.3.13)
URL: https://doc.linkurious.com/user-manual/latest/page.html (Confirmed, fetched)

Does well (all Confirmed from the manual):
- A circular **badge on each node with the number of undisplayed relationships**.
- Double-click a node to expand it. **Selective Expand** filters by category and edge type, offers "Most connected" and "Least connected", and caps the number of neighbours. "Super nodes" get a plus badge.
- A **radial layout** places nodes around a chosen root by shortest-path distance.
- Shift+click selects all direct neighbours. Repeating it extends to the next level, which is a manual 2-hop.
- Clicking a row in the property-panel table **highlights that node with a pulsing halo** on the graph.
- **Edge grouping** collapses parallel edges of one type into one edge with a count. The side panel then shows aggregated Sum, Average, Min and Max of numeric properties, plus FIRST DATE and LAST DATE.
- Keyboard shortcuts: arrows pan; + and − zoom; ctrl/cmd+z undo.

Patterns to copy:
- **Node badge = hidden neighbour count.** Click it to expand to hop 2.
- **Edge aggregation**: collapse multiple `billed` edges between provider and member into one edge labelled "×37 claims, $48.2K". The side panel shows sum, average, first and last date.
- **Table-to-graph highlight**: clicking a claim in the timeline strip pulses the matching node.
- **Radial or concentric layout around the case subject.**

### 2.2 Neo4j Bloom (Scene interactions docs)
URL: https://neo4j.com/docs/bloom-user-guide/current/bloom-visual-tour/bloom-scene-interactions/ (Confirmed, fetched). Overview: https://neo4j.com/docs/bloom-user-guide/current/bloom-visual-tour/bloom-overview/

Does well (Confirmed):
- A **Legend panel** lists every category and relationship type and is also where you set styles (colour, icon, caption, with rule-based styles).
- Hover shows the label and chosen properties. Double-click opens the **Inspector**.
- Expand can follow "a specific relationship type and direction", with a node limit.
- **Shortest path** between two selected nodes.
- **Filtering greys out** filtered elements instead of removing them, with an option to dismiss. Numeric filters show a histogram with a slider.
- A minimap and a "fit to screen" control.

Patterns to copy:
- **The legend doubles as the filter.** Click an edge type (for example `shares-address`) to toggle it, and grey out rather than remove, so the layout stays stable.
- **Typed expand**: right-click a provider and choose "Expand via owns" or "Expand via shares-address".
- **Histogram filter** on the node risk score.

### 2.3 Cambridge Intelligence KeyLines / ReGraph
URLs: https://cambridge-intelligence.com/keylines/ and https://cambridge-intelligence.com/regraph/ (Confirmed, fetched and captured)

Does well (Confirmed from the page copy): "Combo decluttering" groups nodes and lets you drill into them; centrality and traversal algorithms are used for highlighting "through styling, sizing, foregrounding and filtering"; there is an anti-money-laundering demo; ReGraph is "The React SDK for state-driven graph visualization". The interactive demos sit behind a trial request ("Explore these interactive demos in your browser when you request a trial"; Confirmed), so I could not inspect them. KeyLines is commercial and "licensed on a per-application basis" (Confirmed), so it is out of scope for a hackathon (Inferred).

Patterns to copy (Inferred from the feature list):
- **Foregrounding**: dim everything except the selected path or neighbourhood.
- **Combos**: group all claims under their member node, collapsed by default, with a count.
- **State-driven rendering**: graph state comes from the same React state or query data as the other panels. This matches ClaimShield's shared `caseId`.

### 2.4 Sigma.js "Hover and search highlight" example
URL: https://www.sigmajs.org/how-to/interactivity/hover-search/ (Confirmed, captured live)

Does well: hovering a node highlights it and its neighbours, and a search box filters nodes by label (Confirmed, page text and live render). The v4 docs also show built-in node shapes (circle, square, triangle, diamond), edge paths (line, curved, step), arrow extremities, **dashed and dotted edges via `layerDashed`**, and `renderEdgeLabels` (Confirmed: https://www.sigmajs.org/how-to/edges/types-colors/ and https://www.sigmajs.org/how-to/technical/migration-v3-v4/).

Patterns to copy:
- **Hover neighbourhood highlight**, the lowest-effort way to read a dense ego graph.
- **Search-to-focus**: typing an NPI or a name centres and highlights the node.
- **Edge colour follows the source node colour** (`{ node: "source" }`), a cheap way to show who initiated a `referred` edge.

### 2.5 Cytoscape.js demos
URLs: https://js.cytoscape.org/demos/edge-types/ and https://js.cytoscape.org/demos/concentric-layout/ (Confirmed, captured). API docs: https://js.cytoscape.org/

Does well (Confirmed from the docs and demos):
- Edge `curve-style` covers bezier, unbundled-bezier, straight, haystack, segments, round-segments, taxi, round-taxi and loop.
- `line-style` is solid, dotted or dashed.
- Arrow shapes include triangle, tee, vee, diamond, circle, square, chevron and more.
- There are many node `shape`s, `background-image` for icons, and `source-label`/`target-label` text.
- The concentric layout places nodes in rings by a metric you supply.
- `eles.closedNeighborhood()` returns a node plus its neighbours.

Patterns to copy:
- **Concentric rings = hop distance** (centre = case subject, ring 1 = hop 1, ring 2 = hop 2). It is deterministic, so positions don't jump between renders.
- **One stylesheet rule per type**, using selectors like `node[type = "provider"]` and `edge[type = "shares-address"]`. Shape and line style carry the type, so it never depends on colour alone.
- **`closedNeighborhood()` plus a `.faded` class** for click focus.

### Graph design spec distilled for ClaimShield (Inferred)
| Element | Encoding |
|---|---|
| provider | round-rectangle, brand green fill, NPI label |
| member | ellipse, navy `#15497E` |
| facility | hexagon, grey |
| owner | diamond, grey |
| address | triangle, grey, small |
| claim | small square. Collapse into the member/provider edge as a count by default (Linkurious edge grouping) |
| referred | solid line with arrow, warm accent (the only coloured edge) |
| billed | solid thin grey with arrow. Aggregate parallel edges, label "×N, $X" |
| owns | thick solid, no colour change |
| shares-address | dashed, no arrow (symmetric) |
| treated-at | dotted with arrow |
| Focus | case subject has a thick dark border. Click = fade everything outside `closedNeighborhood()` |
| Legend | always visible, clickable to toggle types (Bloom) |
| Expansion | badge with hidden-neighbour count (Linkurious). Capped expand per type |
| Accessibility | a parallel entity table (same data) with keyboard focus. Selecting a row selects the node and vice versa |

---

## Part 3: Library pick for React 19 + TypeScript

Method:
- Versions, licences, peer deps and timestamps: `npm view <pkg> version license peerDependencies time` on 2026-10-08 (Confirmed, registry).
- Stars and open counts: GitHub REST API (`/repos/...`, `/search/issues?q=is:issue+is:open`) on the same day (Confirmed).
- "Full package" sizes: bundlephobia API (Confirmed).
- "Realistic import" sizes: I measured these myself (Confirmed, local measurement). I bundled with esbuild 0.28.2 using `--bundle --minify --format=esm`, with react and react-dom external and `NODE_ENV=production`, then ran `gzip -9`. The imports measured are listed in each row.

### 3a. Charting libraries

| | Recharts | visx (@visx/xychart) | Apache ECharts (+ echarts-for-react) | Nivo (@nivo/line) |
|---|---|---|---|---|
| Latest version (npm `latest`) | **3.10.1** | **4.0.0** | **6.1.0** / wrapper **3.0.6** | **0.99.0** |
| Published (UTC) | 2026-07-25 | 2026-06-11 (IST: 12 Jun) | 2026-05-19 / wrapper 2026-01-21 | 2025-05-23 |
| Release cadence (last stable releases) | 3.7.0 Jan, 3.8.0 Mar, 3.9.0 Jun, 3.10.0 and 3.10.1 Jul 2026. Canary 3.11.0-canary.5 on 2026-10-03 | 3.12.0 Nov 2024, then 4.0.0 Jun 2026 (19-month gap) | 6.0.0 Jul 2025, 6.1.0 May 2026 | 0.92 to 0.99 all Apr–May 2025. Nothing since (about 16 months) |
| License | MIT | MIT | Apache-2.0 / wrapper MIT | MIT |
| React 19 peer | `react ^16.8 \|\| ^17 \|\| ^18 \|\| ^19` (Confirmed) | `react ^18 \|\| ^19` (Confirmed) | echarts has no React peer. Wrapper: `react ^15 \|\| >=16`, `echarts ^3–^6` (Confirmed) | `react ^16.14 \|\| ^17 \|\| ^18 \|\| ^19` (Confirmed) |
| Known React 19 issues | #7463 (open, 2026-06-16): "Maximum update depth exceeded when chart unmounts behind Suspense boundary (React 19)". #6316 (open): `createSlice` error in Next 15 + React 19 (Confirmed) | Unknown (v4 shipped React 19 support; issue #1883 "React 19 support" closed) (Confirmed: closed) | None found specific to React 19 (search was noisy). Unknown | #2801 (open): missing key warning in Choropleth legends with React 19 (Confirmed) |
| Full package min+gz (bundlephobia) | 151.5 KB | 49.9 KB | echarts 368.0 KB; wrapper 3.6 KB | 96.0 KB |
| Realistic import, min+gz (local) | **115.4 KB** (ComposedChart, LineChart, Line, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine) | **61.8 KB** (XYChart, AnimatedLineSeries, GlyphSeries, Axis, Grid, Tooltip; react-spring included) | **183.2 KB** tree-shaken via `echarts/core` (Line, Scatter, Grid, Tooltip, Legend, Aria, SVGRenderer). Full import 379.6 KB | **95.2 KB** (ResponsiveLine) |
| Tree-shaking | Partial. Internal Redux Toolkit, immer and reselect are always pulled in (deps Confirmed in npm) | Good. Separate `@visx/*` packages | Good, but only with manual `echarts.use([...])` registration (Confirmed, ECharts aria docs show this pattern) | Per-chart packages, but a heavy shared core |
| Rendering | SVG | SVG | Canvas default. SVG renderer optional | SVG (some charts have canvas variants) |
| Accessibility | `accessibilityLayer` adds a11y attributes and keyboard controls. **Default true in 3.0** (Confirmed: https://github.com/recharts/recharts/wiki/3.0-migration-guide) | Nothing built in. You write ARIA yourself (Inferred from it being low-level primitives) | `aria.show: true` generates an `aria-label` description from the data. Decal patterns help colour-blind users. Off by default; AriaComponent must be imported (Confirmed: https://echarts.apache.org/handbook/en/best-practices/aria/). No keyboard nav per point (Inferred) | Unknown in detail (not verified) |
| Calibration / precision charts fit | ComposedChart with Scatter plus a diagonal ReferenceLine; Line with dots for precision over time (Inferred) | Very flexible; more code (Inferred) | Very capable, built for large data (Inferred) | Line and scatter available (Inferred) |
| GitHub | 27,618 stars, 409 open issues | 21,075 stars, 116 open issues | 67,465 stars, 1,292 open issues / wrapper 5,004 stars | 14,106 stars, 36 open issues |

Note on echarts-for-react: the registry `time` field also lists 3.0.7, 3.1.7 and 3.2.7 (all 2026-05-19), but `latest` is still 3.0.6 and `npm view echarts-for-react@3.2.7` returns 404 (Confirmed). Treat 3.0.6 as current.

Tremor: `@tremor/react` 3.18.7 has peer `react ^18.0.0` and was last published 2025-01-13 (Confirmed), so it is not React 19-ready as a package. Its site now pushes copy-paste components built on Recharts (Confirmed).

### 3b. Network-graph libraries

| | Cytoscape.js (+ cytoscape-fcose, react-cytoscapejs) | Sigma.js + graphology (+ @react-sigma/core) | react-force-graph (react-force-graph-2d) |
|---|---|---|---|
| Latest version | **cytoscape 3.34.3**; cytoscape-fcose 2.2.0; react-cytoscapejs 2.0.0; @types/react-cytoscapejs 1.2.6 | **sigma 4.0.0** (released today); sigma 3.0.3 (last v3); graphology 0.26.0; **@react-sigma/core 5.0.6** | react-force-graph 1.48.3; **react-force-graph-2d 1.29.2** |
| Published (UTC) | cytoscape 2026-09-07; fcose 2023-01-17; react-cytoscapejs 2022-09-02 (IST: 3 Sep) | sigma 4.0.0 2026-10-08T11:09Z (16:39 IST); sigma 3.0.3 2026-04-30; graphology 2025-01-26; @react-sigma/core 2025-12-01 | 2026-09-29 (IST: 30 Sep) |
| Release cadence | 3.33.2 Apr, 3.33.3 Apr, 3.33.4 May, 3.34.0 Jun, 3.34.1 Aug, 3.34.2 Aug, 3.34.3 Sep 2026 (Confirmed, GitHub releases and npm) | v4 had alphas and betas through 2026 (beta.8 on 2026-10-05), with GA today. The React wrapper has not followed yet | 1.28.0 Jul 2025, 1.29.0 Sep 2025, 1.29.1 Feb 2026, 1.29.2 Sep 2026 |
| License | MIT (all three) | MIT (all) | MIT |
| React 19 compatibility | Core is framework-agnostic (no React peer). react-cytoscapejs peer `react >=15.0.0` (loose, unmaintained since 2022). **Recommend direct use** | @react-sigma/core peer `react ^18 \|\| ^19`, **but `sigma ^3.0.2`**, so it does not support sigma 4.0.0 yet (Confirmed) | peer `react: "*"` (Confirmed) |
| TypeScript | Types ship in the package (`index.d.ts`; Confirmed in the installed package) | Written in TS (Inferred from package `types` files) | Types included (Inferred; not checked) |
| Full package min+gz (bundlephobia) | cytoscape 137.0 KB; react-cytoscapejs 1.7 KB; fcose figure (0.7 KB) is unreliable because of how bundlephobia counts its deps | sigma 4.0.0 96.5 KB; sigma 3.0.2 25.8 KB; sigma 3.0.3 26.0 KB; graphology 12.8 KB; @react-sigma/core Unknown (bundlephobia rate-limited me) | 59.8 KB |
| Realistic import, min+gz (local) | cytoscape alone **141.5 KB**; cytoscape + fcose **175.8 KB**; + react-cytoscapejs 177.6 KB | graphology + sigma 3.0.3 + @react-sigma/core **38.9 KB**; graphology + sigma 4.0.0 **112.8 KB** | **61.8 KB** |
| Rendering | Canvas (Confirmed, docs) | WebGL (Confirmed, sigmajs.org) | Canvas (2D) |
| Typed nodes | ~20 built-in shapes, `background-image` icons, selectors on data (`node[type="provider"]`) (Confirmed) | v3: shapes and icons need extra program packages. v4: built-in `sdfCircle`, `sdfSquare`, `sdfTriangle`, `sdfDiamond` plus `@sigma/node-image` (Confirmed, v4 docs) | Custom canvas paint callback per node (Inferred) |
| Typed edges and labels | `line-style` solid, dotted or dashed; many arrow shapes; many curve styles; edge labels with autorotate (Confirmed) | v4: line, curved and step paths; arrow extremities; `layerDashed` dashed or dotted; `renderEdgeLabels` (Confirmed). v3: fewer built-ins | Colour, width, directional arrows and particles; labels via custom paint (Inferred) |
| Click/hover events for a side panel | `cy.on('tap', 'node', …)`, plus `mouseover`/`mouseout` on nodes and edges (Confirmed; snippet below type-checks) | `enterNode`, `clickNode` and similar events; `useRegisterEvents` hook (Confirmed, docs and wrapper API names) | `onNodeClick`, `onNodeHover`, `onLinkClick` props (Inferred; not checked in docs) |
| 2-hop helpers | `closedNeighborhood()`, `bfs`, `dijkstra`, built-in concentric/breadthfirst layouts (Confirmed) | graphology standard library has neighbours and traversal (Confirmed on sigmajs.org) | None built in; compute yourself (Inferred) |
| Accessibility | Canvas, so no per-node DOM, ARIA or keyboard focus out of the box (Inferred from canvas rendering). Needs a parallel accessible table | WebGL, same limitation (Inferred) | Canvas, same limitation (Inferred) |
| GitHub | cytoscape.js 11,236 stars, **17 open issues**; fcose 184 stars; react-cytoscapejs 534 stars, 41 open issues, last push 2025-01-27 | sigma.js 12,182 stars, **6 open issues**; react-sigma 238 stars, 3 open issues; graphology 1,759 stars | 3,318 stars, 218 open issues+PRs |

### Recommendation

**Charting: Recharts 3.10.1.**
- **A11y scoring:** keyboard navigation and ARIA are on by default in v3 (Confirmed). It is SVG, so text stays crisp and selectable. ECharts' default canvas and Nivo are weaker or unverified here.
- **Code quality:** declarative JSX composition, typed props and custom components all fit TanStack-style React code. It is what shadcn/ui charts use (Confirmed), so examples and copy-paste patterns already exist for this stack.
- **ClaimShield's charts are small** (precision/hit-rate over time, calibration scatter plus diagonal, dollars by month). There is no need for ECharts' large-data engine.
- **Cost:** ~115 KB min+gz for the components we need (measured). That is about twice visx. Mitigate by lazy-loading the outcomes route with TanStack Router code-splitting (Inferred).
- **Watch:** open issue #7463 (React 19 + Suspense unmount loop). Don't put charts inside a Suspense boundary that can re-suspend, or test that path (Inferred).
- **Runner-up: visx 4.0.0** (61.8 KB measured, React 19 peer). Switch if the bundle budget is strict, or if we need bespoke visuals (a reliability diagram with confidence bands). The trade-off is that you build axes, tooltips and all ARIA yourself.

**Graph: Cytoscape.js 3.34.3, used directly (no `react-cytoscapejs`).**
- **Typed nodes and edges out of the box:** one stylesheet rule per type, shapes per node type, dashed, dotted or solid lines and arrow shapes per edge type, and edge labels (Confirmed). Type is shown by shape and line style, not colour only, which helps a11y.
- **The 2-hop ego view is built in:** the concentric layout with `concentric = 2 - hop` gives stable rings, and `closedNeighborhood()` handles click focus (Confirmed API). fcose is not needed, which saves ~34 KB.
- **Maintenance:** releases in Apr, May, Jun, Aug and Sep 2026, and 17 open issues (Confirmed). It is zero-dependency and ships its own TS types.
- **Scale fits:** tens to a few hundred nodes is well within canvas rendering (Inferred).
- **Why not Sigma right now:** sigma 4.0.0 went GA today and `@react-sigma/core` 5.0.6 still peers on `sigma ^3.0.2` (Confirmed). Adopting today means either v3 (with a migration ahead) or v4 without the React wrapper. v3's typed-edge styling (dashed lines, shapes) also needs extra programs.
- **Cost:** ~141 KB min+gz for the core (measured). It is the biggest item. Lazy-load the graph panel (`React.lazy` / route-level split) so the queue and brief render first (Inferred).
- **Accessibility caveat (all candidates):** canvas or WebGL graphs are not screen-reader accessible. Ship an "Entities in this network" table with the same nodes and edges, keyboard-selectable, synced both ways with the graph selection. Give the container `role="img"` and an `aria-label` pointing to that table (Inferred).
- **Runner-up: Sigma.js + graphology** (sigma 3.0.3 + @react-sigma/core 5.0.6 = 38.9 KB min+gz measured, the smallest option). Switch when (a) the graph needs thousands of nodes, or (b) `@react-sigma/core` publishes sigma 4 support, since v4 has built-in shapes, dashed edges and a declarative state/styles API.

### Illustrative snippet (not committed anywhere)
Type-checked locally with TypeScript in strict mode against cytoscape 3.34.3 and @types/react 19. This is illustrative only.

```tsx
import { useEffect, useLayoutEffect, useRef } from "react";
import cytoscape, { type Core, type ElementDefinition, type StylesheetJson } from "cytoscape";

export type NodeType = "provider" | "member" | "facility" | "owner" | "address" | "claim";
export type EdgeType = "referred" | "billed" | "owns" | "shares-address" | "treated-at";

export interface GraphNode { id: string; type: NodeType; label: string; hop: 0 | 1 | 2; riskScore?: number }
export interface GraphEdge { id: string; source: string; target: string; type: EdgeType }

const style: StylesheetJson = [
  { selector: "node", style: { label: "data(label)", "font-size": 10, "text-valign": "bottom", "text-margin-y": 4, width: 22, height: 22, "background-color": "#5b6b70", color: "#042126" } },
  { selector: 'node[type = "provider"]', style: { shape: "round-rectangle", "background-color": "#1c873e" } },
  { selector: 'node[type = "member"]', style: { shape: "ellipse", "background-color": "#15497e" } },
  { selector: 'node[type = "facility"]', style: { shape: "hexagon" } },
  { selector: 'node[type = "owner"]', style: { shape: "diamond" } },
  { selector: 'node[type = "address"]', style: { shape: "triangle" } },
  { selector: 'node[type = "claim"]', style: { shape: "rectangle", width: 14, height: 14 } },
  { selector: "node[hop = 0]", style: { "border-width": 3, "border-color": "#042126", width: 32, height: 32 } },
  { selector: "edge", style: { width: 1.5, "curve-style": "bezier", "target-arrow-shape": "triangle", "line-color": "#9aa5a8", "target-arrow-color": "#9aa5a8", label: "data(type)", "font-size": 8, "text-rotation": "autorotate", "text-background-color": "#ffffff", "text-background-opacity": 1 } },
  { selector: 'edge[type = "shares-address"]', style: { "line-style": "dashed", "target-arrow-shape": "none" } },
  { selector: 'edge[type = "owns"]', style: { "line-style": "solid", width: 2.5 } },
  { selector: 'edge[type = "referred"]', style: { "line-color": "#c2410c", "target-arrow-color": "#c2410c" } },
  { selector: 'edge[type = "treated-at"]', style: { "line-style": "dotted" } },
  { selector: ".faded", style: { opacity: 0.15 } },
  { selector: "node:selected", style: { "border-width": 3, "border-color": "#2bbc2b" } },
];

export function ProviderGraph(props: { nodes: GraphNode[]; edges: GraphEdge[]; onSelect: (id: string, type: NodeType) => void }) {
  const { nodes, edges, onSelect } = props;
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const onSelectRef = useRef(onSelect);
  useLayoutEffect(() => { onSelectRef.current = onSelect; }); // keep latest callback without re-creating the graph

  useEffect(() => {
    if (!containerRef.current) return;
    const elements: ElementDefinition[] = [
      ...nodes.map((n) => ({ group: "nodes" as const, data: { ...n } })),
      ...edges.map((e) => ({ group: "edges" as const, data: { ...e } })),
    ];
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style,
      // Built-in concentric layout: case subject in the centre, hop-1 ring, hop-2 ring.
      layout: { name: "concentric", concentric: (n) => 2 - Number(n.data("hop")), levelWidth: () => 1, animate: false },
    });
    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      cy.elements().addClass("faded");
      node.closedNeighborhood().removeClass("faded"); // highlight direct ties
      onSelectRef.current(node.id(), node.data("type") as NodeType);
    });
    cy.on("tap", (evt) => { if (evt.target === cy) cy.elements().removeClass("faded"); });
    cyRef.current = cy;
    return () => { cy.destroy(); cyRef.current = null; };
  }, [nodes, edges]);

  return <div ref={containerRef} role="img" aria-label="Provider network, two hops from the case subject. The same entities are listed in the table below." style={{ width: "100%", height: 420 }} />;
}
```

Notes: memoise `nodes` and `edges` (for example via TanStack Query `select`) so the graph is not rebuilt on every render. Pair the component with an accessible entity table that calls the same `onSelect`. The snippet deliberately does not set `wheelSensitivity`. Cytoscape 3.34.3 logs a console warning whenever that option is set (Confirmed, in `dist/cytoscape.esm.mjs`), and a clean console helps code-quality scoring.

---

## Acentra palette note

Source: https://www.acentra.com homepage HTML and its linked HubSpot CSS (`template_main.min.css`, `template_theme-overrides.min.css`, `template_child_v2.css`, module CSS), fetched with curl on 2026-10-08. Hex counts are occurrences across that CSS.

| Hex | Where it is used in their CSS | Status | Contrast vs #FFFFFF | Suggested ClaimShield role |
|---|---|---|---|---|
| `#042126` | Most-used colour (188×). Dark panel background in the solutions tabber and body text colour | **Confirmed** | 16.79:1 | Primary text, dark header/sidebar |
| `#2BBC2B` | 135×. Active tab indicator bar, h3 colour on the dark panel, button backgrounds and outlines | **Confirmed** | 2.52:1 (fails for text on white); 6.66:1 on `#042126` | Brand accent: selected states, focus ring on dark, chart fill. Not text on white |
| `#209B47` | 37×. Link and heading text colour | **Confirmed** | 3.60:1 (passes only for large text, ≥3:1) | Large headings, icons |
| `#1C873E` | 9×. Eyebrow headings ("letter-spacing 3px, uppercase"), outline buttons | **Confirmed** | 4.58:1 (passes AA for body text) | **Green for text, links and primary buttons on white** |
| `#1C8B38` | 2× | **Confirmed** | 4.38:1 | Avoid (near-duplicate of #1C873E) |
| `#B4EA54` | 30×. Lime backgrounds, buttons, borders | **Confirmed** | 1.42:1 | Highlight chip background only, with dark text |
| `#ACF2E5` | 42×. Mint backgrounds, carousel dots | **Confirmed** | 1.27:1 | Subtle selected-row or tag background |
| `#E4F3F2` | 2×. Section backgrounds | **Confirmed** | 1.14:1 | Panel or page tint |
| `#F2FCFF` | 3×. Header alert bar background | **Confirmed** | 1.04:1 | Alternate surface |
| `#15497E` | 14×. Text colour in some modules | **Confirmed** | 9.19:1 | Secondary/info colour (member nodes) |
| `#EF6B51` | 4× | **Confirmed** | 3.05:1 | Possible warm accent; check before using for risk |
| Roboto, Inter | `font-family` declarations (Roboto 20+×, Inter_regular 19×) | **Confirmed** | n/a | Inter with tabular numbers for UI |

Inferred guidance:
- The brand reads as deep teal-ink plus a bright green. For an investigator UI, use neutral greys for 90% of surfaces, `#042126` for text and chrome, `#1C873E` for actions, and `#2BBC2B` for selection and focus accents.
- Keep red, amber and green for risk/status only, and always add an icon or label as well as the colour.
- I did not confirm logo colours. The main logo is a PNG and the footer SVG had no hex fills I could read (Unknown).

---

## Sources

Part 1 (visited):
- https://www.sas.com/en_us/software/intelligence-analytics-visual-investigator.html
- https://www.unit21.ai/products/case-management
- https://play.grafana.org/
- https://play.grafana.org/d/appenv-banking-risk-fraud/risk-and-fraud-posture
- https://play.grafana.org/d/appenv-banking-exec-overview/banking-executive-overview
- https://play.grafana.org/api/search?query=fraud&type=dash-db (to find the dashboards)
- https://ui.shadcn.com/examples/dashboard
- https://ui.shadcn.com/examples/tasks
- https://ui.shadcn.com/docs/components/chart
- https://ui.shadcn.com/docs/components/data-table
- https://preview.tabler.io/
- https://tremor.so/
- https://www.palantir.com/platforms/gotham/ (title only)
- https://www.quantexa.com/

Part 2 (visited):
- https://doc.linkurious.com/user-manual/latest/page.html
- https://linkurious.com/decision-intelligence-platform-graph-visualization/ (seen via search result only)
- https://neo4j.com/docs/bloom-user-guide/current/bloom-visual-tour/bloom-scene-interactions/
- https://neo4j.com/docs/bloom-user-guide/current/bloom-visual-tour/bloom-overview/ (seen via search result only)
- https://cambridge-intelligence.com/keylines/
- https://cambridge-intelligence.com/regraph/
- https://www.sigmajs.org/
- https://www.sigmajs.org/storybook/ (now the sigma v4 examples index)
- https://www.sigmajs.org/how-to/interactivity/hover-search/
- https://www.sigmajs.org/how-to/edges/types-colors/
- https://www.sigmajs.org/how-to/technical/migration-v3-v4/
- https://js.cytoscape.org/
- https://js.cytoscape.org/demos/edge-types/
- https://js.cytoscape.org/demos/concentric-layout/
- https://www.graphistry.com/ (looked at; not used as a reference)

Part 3:
- npm registry via `npm view`: recharts, @visx/xychart, @visx/shape, echarts, echarts-for-react, @nivo/core, @nivo/line, @tremor/react, cytoscape, cytoscape-fcose, react-cytoscapejs, @types/react-cytoscapejs, sigma, graphology, @react-sigma/core, react-force-graph, react-force-graph-2d
- https://bundlephobia.com/api/size?package=<pkg>@<version> (per package)
- GitHub API: https://api.github.com/repos/{recharts/recharts, airbnb/visx, apache/echarts, hustcc/echarts-for-react, plouc/nivo, cytoscape/cytoscape.js, iVis-at-Bilkent/cytoscape.js-fcose, plotly/react-cytoscapejs, jacomyal/sigma.js, sim51/react-sigma, vasturiano/react-force-graph, graphology/graphology, tremorlabs/tremor-npm}
- https://github.com/cytoscape/cytoscape.js/releases
- https://github.com/jacomyal/sigma.js/releases
- https://github.com/sim51/react-sigma/issues
- https://github.com/recharts/recharts/wiki/3.0-migration-guide
- https://github.com/recharts/recharts/issues/7463
- https://github.com/recharts/recharts/issues/6316
- https://github.com/plouc/nivo/issues/2801
- https://echarts.apache.org/handbook/en/best-practices/aria/

Palette:
- https://www.acentra.com
- https://acentra.com/hubfs/hub_generated/template_assets/1/184273342061/1791304272562/template_main.min.css
- https://acentra.com/hubfs/hub_generated/template_assets/1/184274071100/1791304273528/template_theme-overrides.min.css
- https://acentra.com/hubfs/hub_generated/template_assets/1/192307331385/1791304275583/template_child_v2.css

---

## Limitations / Unknowns

- **Visual observations** come from headless-Chrome screenshots I took of the live pages on 2026-10-08. Charts that need JS or WebGL sometimes did not fully render (the shadcn area chart rendered empty in headless mode).
- **Palantir Gotham/Foundry, Quantexa, KeyLines/ReGraph demos:** I saw no public product UI. The demos are gated behind a trial or a sales request. Those claims are limited to marketing copy.
- **Not checked:** Sardine, Alloy, Hummingbird, Sift, Datadog, Memgraph Lab, Graphistry's investigation UI, Refine.
- **Bundle sizes:**
  - My local numbers depend on the exact imports listed and on esbuild 0.28.2. Vite/Rollup output will differ slightly.
  - bundlephobia rate-limited me for `@react-sigma/core` (Unknown there; the local measurement covers it).
  - bundlephobia's cytoscape-fcose figure (0.7 KB gz) looks wrong and was not used.
- **Open issue counts** are from the GitHub search API (issues only) on 2026-10-08 and change daily. The `open_issues_count` from the repos API includes PRs.
- **React 19 issue search** used a keyword query that also matched unrelated issues. I only cite issues I opened and read.
- **Unverified items:**
  - Nivo's accessibility features.
  - react-force-graph's event prop names (listed as Inferred).
  - Whether sigma v4 or Cytoscape offer any built-in keyboard navigation (I found none; Inferred none).
- **Timing:** sigma 4.0.0 was published today (2026-10-08 11:09 UTC). Its ecosystem (React wrapper, plugins) may update within days, which could change the graph runner-up advice.
- **Acentra palette:** colours come from the marketing site's CSS, not an official brand guide (none found). The logo colours are Unknown.
