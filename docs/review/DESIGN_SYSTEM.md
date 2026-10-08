# ClaimShield Nexus: Design System

**Version 1.0 · 08 Oct 2026 · Panshul Arora, Acentra code-a-thon PS3**

Libraries targeted: **Recharts 3** (charts) and **Cytoscape.js 3.34 + fcose** (network graph). Both were added to the repo in commit `e20263c`. Fonts come from fontsource: Inter Variable and Roboto Mono.

Scope: visual styling only, for the authenticated SIU app (`/manager/queue`, `/investigator/cases`, `/investigator/workspace/:caseId`, `/wiki/*`, `/audit`). The landing page (`/`), login and page flow stay exactly as they are.

Files:
- `tokens.css`: every custom property, annotated with its source.
- `brand-evidence/`: raw CSS, `colors_sampled.csv`, `notes.md`, computed styles, screenshots, `palette.html` and `palette.png`.
- `scripts/`: the extractor, palette builder, contrast checker and CSS validator. Re-run them after any change.

---

## 0. Principles

1. **Data first, chrome second.** Neutrals carry about 90% of the UI. Colour appears only where it means something.
2. **Green is the brand, not the verdict.** Acentra green marks primary actions, active navigation, focus, selection and the 3px brand bar. It never means "low risk" or "safe", and it is not a default data colour.
3. **Risk and harm are two axes.** Financial risk is an ordered slate → amber → orange → red scale. Patient harm is a separate plum flag. Neither relies on colour alone: every level has a label and a shape.
4. **Flat and bordered.** Cards use a 1px border and a 4–6px radius. Shadows are for overlays only (menus, tooltips, drawers). No gradients, glass, glow, neon, purple or particles.
5. **Numbers are tabular and honest.** Use `tabular-nums` everywhere. Right-align numbers, abbreviate on charts ($1.2M), and print the exact value in tables and tooltips.
6. **Calm motion.** 120/200/320ms with a single easing curve, no decorative animation, and everything collapses to 0ms under `prefers-reduced-motion`.
7. **Measured, not eyeballed.** Every contrast ratio in this document was computed from `tokens.css` by `scripts/contrast_from_tokens.py` (146 pairs, 0 failures).

---

## 1. Brand evidence (acentra.com, sampled 08 Oct 2026)

**Method.** `curl` with a desktop Chrome UA fetched `https://www.acentra.com/` (redirects to `https://acentra.com/`, HTTP 200), plus `/about-us`, `/solutions/` and `/solutions/claims-and-encounters`. I downloaded all 29 linked stylesheets, 2 runtime stylesheets, every inline `<style>` and `style=""` attribute, and the logo assets. Headless Chrome then rendered home and about-us for computed styles, font requests and screenshots. The CMS is **HubSpot**: `/wp-json/` and `/theme.json` both return 404, and the site defines no brand CSS custom properties. The site did not block curl, so the Wayback Machine was not needed. Full method and caveats: `brand-evidence/notes.md`.

### 1.1 The colours that matter (curated from the evidence)

| Swatch | Hex | Role on acentra.com | Evidence (selector, file) | Count | Used in ClaimShield as |
|---|---|---|---|---:|---|
| Acentra Green | `#2bbc2b` | Primary brand: logo, all primary buttons, active tab underline, active nav | Logo pixels (footer-logo.svg embedded PNG, logo-retina.png). `.hs-button{background-color:#2bbc2b;color:#042126}`. `header .hs-button`, `footer .hs-button`. `.tabber_section ul.tabnav li a.active{border-bottom:3px solid #2bbc2b}`. `.nav … .active>a{color:#2bbc2b}` (theme-overrides.min.css, child_v2.css, module CSS) | 142 | `--green-500` → `--color-brand` (primary button fill, brand bar) |
| Acentra Ink | `#042126` | Body text, button text on green, logo wordmark, hero background | `body{color:#042126;font-size:18px}` (theme-overrides). Logo pixels. `hero-bg.jpg` dominant `#042125` | 242 | `--neutral-950` → `--color-text`, `--color-text-on-brand` |
| Acentra Dark Green | `#209b47` | h1, h5, desktop nav links, date-picker selection | `.h1,h1{color:#209b47}`, `.h5,h5{color:#209b47}`, `.nav>nav>ul .header__menu-item--depth-1>a{color:#209b47}` | 39 | `--green-600` → `--color-brand-strong` (state bars), `--chart-1` |
| Eyebrow Green | `#1c873e` | Section eyebrows ("OUR SOLUTIONS", computed) | `.team-testimonials .top_content h6{color:#1c873e}`; computed h6 `rgb(28,135,62)` | 10 | `--green-700` → `--color-focus`, `--graph-subject-fill` |
| Lime | `#b4ea54` | Button hover, symbol gradient end | `.hs-button:hover{background-color:#b4ea54}`; Symbol-retina.png | 33 | Primitive only (too loud for UI). Hover uses `--green-400` instead |
| Deep Teal | `#005f68` | h2 headings | `.h2,h2{color:#005f68}`; computed h2 Roboto 700 40px | 1 rule (every h2) | `--chart-4`, `--graph-edge-referral` |
| Link Blue | `#15497e` | Body links, footer links | `a,a:active,a:focus,a:hover{color:#15497e}` | 13 | `--color-link`, `--color-info-fg`, `--chart-focus` |
| Mint | `#acf2e5` | Header bottom border, `<hr>`, slider dots | `.header .primary-section{border-bottom-color:#acf2e5}` | 58 | Primitive only |
| Sand / Sand 2 | `#f2ece4` / `#e8e0d6` | Form/search block bg, tab marker bars | child_v2.css, module_solutions-tabber | 5 / 3 | Owner node fill (`--graph-node-owner-fill`) |
| Pale Teal / Shadow Teal | `#e4f3f2` / `#11615b` | Blog featured panel; teal drop-shadows (alpha) | template_blog.css, child_v2.css | 2 / 8 | Facility node fill / stroke |

### 1.2 Every colour sampled (generated from `brand-evidence/colors_sampled.csv`)

Counts are occurrences in non-vendor CSS, inline `<style>` blocks and `style=""` attributes across the 4 pages. "pixel" means the colour was sampled from images or the rendered page, not from CSS.

| # | Hex | Swatch name | Where used on acentra.com (top selectors / element) | Source file(s) | CSS count |
|---:|---|---|---|---|---:|
| 1 | `#042126` | Acentra Ink | logo wordmark text fill (logo-retina.png, footer-logo.svg embedded PNG) / CSS: h6[style] {color} x7; .footer.footer_section__2 .footer-section-1 .flex_row.primary_font {color} x4; .footer.footer_section__2 .footer-section-2 .flex_row.primary_font {color} x4 _( | template_theme-overrides.min.css x86; template_child_v2.css x83; template_blog.css x17; https://acentra.com/solutions/claims-and-encounters  | 242 |
| 2 | `#ffffff` | White | .header-search-inner .header-search-close svg path {fill} x2; header.header .hs-sec-btn {background-color} x2; header.header .hs-sec-btn {border-color} x2 _(alphas: 1.0: 167, 0.1: 1)_ | template_theme-overrides.min.css x67; template_child_v2.css x34; https://acentra.com/solutions/ (inline <style>) x17; template_main.min.css  | 168 |
| 3 | `#2bbc2b` | Acentra Green (primary) | logo fill (dominant, logo-retina.png / footer-logo.svg embedded PNG / Symbol-retina.png) / CSS: header.header .nav {background-color} x2; .home_banner .Cm_search_wrap .hs-search-field__input:focus {outline} x1; .cm_our_sol_wrap .tabber_wrap .left_content .titl | template_theme-overrides.min.css x99; template_child_v2.css x31; https://acentra.com/solutions/claims-and-encounters (inline <style>) x4; te | 142 |
| 4 | `#c6c6c6` | Editor highlight gray (content artefact) | span[style] {background-color} x115 | https://acentra.com/solutions/ (style attr) x110; https://acentra.com/solutions/claims-and-encounters (style attr) x5 | 115 |
| 5 | `#000000` | Black (mostly as rgba shadows) | span[style] {text-decoration-color} x18; .img_wrap_inner img {background} x3; .hs-search-field__suggestions a:focus,.hs-search-field__suggestions a:hover {background-color} x1 _(alphas: 0.1: 2, 0.16: 5, 0.3: 4, 1.0: 31, 0.25: 3, 0.06: 3, 0.8: 2, 0.2: 3, 0.15:  | template_child_v2.css x17; https://acentra.com/solutions/ (style attr) x16; template_theme-overrides.min.css x5; https://acentra.com/solutio | 61 |
| 6 | `#acf2e5` | Mint | .main_area-row-2-background-layers {background-image} x2; .team-testimonials ul.slick-dots li button {background} x1; .bnr_wrp .pg_number_item:not(.glide__bullet--active) .cm_dots {color} x1 | template_theme-overrides.min.css x36; https://acentra.com/solutions/claims-and-encounters (inline <style>) x8; template_child_v2.css x5; htt | 58 |
| 7 | `#209b47` | Acentra Dark Green | .social_share_inner ul>li>a span.clipborad_text:after {border-color} x2; .custom-feature-cards .page-center .top_content h2 {color} x1; .h1,h1 {color} x1 _(alphas: 1.0: 38, 0.5: 1)_ | template_theme-overrides.min.css x34; template_child_v2.css x3; module_custom-feature-cards.min.css x1; template_blog.css x1 | 39 |
| 8 | `#b4ea54` | Lime (hover / symbol gradient) | symbol gradient light end (Symbol-retina.png) / CSS: footer.footer.footer_section__2.cst-footer .footer-section-1 .col-section.num2 {background} x2; .timeline_slider_wrap .item:after {background} x1; .timeline_slider_wrap .item h2 {background} x1 | template_child_v2.css x13; template_theme-overrides.min.css x11; template_blog.css x6; module_timeline-slider.min.css x2 | 33 |
| 9 | `#15497e` | Link Blue | a,a:active,a:focus,a:hover {color} x1; .footer a:not([class]),.footer a:not([class]):hover {color} x1; .blog-card__tag-link:active,.blog-card__tag-link:focus,.blog-card__tag-link:hover,.blog-ca {color} x1 | template_theme-overrides.min.css x8; template_child_v2.css x5 | 13 |
| 10 | `#1c873e` | Eyebrow Green | .team-testimonials .top_content.page-center h6 {color} x1; .post-share-wrapper ul.sharing-btns li a {color} x1; .custom-resource-filter .all-categories-menu .hs-menu-wrapper ul li a {border} x1 | template_blog.css x4; template_child_v2.css x4; module_team-testimonials.min.css x1; https://acentra.com/ (style attr) x1 | 10 |
| 11 | `#11615b` | Shadow Teal | .timeline_slider_wrap .item h2 {filter} x1; .content-with-form.formLogo {box-shadow} x1; .cnt-wit-tp-img-wrp.beneficiaries .page-center.theme_center .cnt-col h2 {filter} x1 _(alphas: 0.15: 2, 0.1: 5, 0.3: 1)_ | template_child_v2.css x6; module_timeline-slider.min.css x1; template_blog.css x1 | 8 |
| 12 | `#f2ece4` | Sand | .hs-search-field__bar,.hs_cos_wrapper_type_email_subscriptions,.hs_cos_wrapper_type_member {background-color} x1; .cmCntWithForm.two-col-content .flex_row .cont-inner {background-color} x1; .cnt-wit-bg-wrp.cmCntWithBg .content_widget {background} x1 _(alphas:  | template_child_v2.css x2; template_theme-overrides.min.css x1; https://acentra.com/solutions/claims-and-encounters (inline <style>) x1; http | 5 |
| 13 | `#026780` | Teal-blue (alpha tints only) | .header .social-share ul li>a,header.header .section-icon {background-color} x1; .nav>nav>ul .header__menu-item--depth-1 ul>li a,.nav>nav>ul .header__menu-item--depth-1 ul {background-color} x1; .blog-header__author-social-links>a,.social_share_inner ul>li>a { | template_theme-overrides.min.css x3; https://acentra.com/solutions/ (inline <style>) x1; https://acentra.com/solutions/ (style attr) x1 | 5 |
| 14 | `#161616` | Near-black (shadow) | .feat-wrap .feat-item-wrp.shadowadd .featitem .outer_wrap {-webkit-box-shadow} x1; .feat-wrap .feat-item-wrp.shadowadd .featitem .outer_wrap {box-shadow} x1; .accordion_wrap .acc-item .acc-content {box-shadow} x1 _(alphas: 0.1: 4)_ | module_features.min.css x2; module_accordion.min.css x2 | 4 |
| 15 | `#ef6b51` | Form error coral | .hs-form-required {color} x1; .hs-input.invalid.error {border-color} x1; .hs-error-msg {color} x1 | template_main.min.css x4 | 4 |
| 16 | `#333333` | Charcoal (shadow/pagination) | .doc-main-sec .hs_cos_wrapper_type_linked_image {box-shadow} x1; .resources-listing-item.custom-blog-listing nav.blog-pagination a {background-color} x1; ::selection {background-color} x1 | template_child_v2.css x2; template_main.min.css x1; template_blog.css x1 | 4 |
| 17 | `#e8e0d6` | Sand 2 | .cm_our_sol_wrap .tabber_wrap .left_content .title_item:before {background} x1; .cm_our_sol_wrap .tabber_wrap .right_content>.content_panel .mobile-tab-title:before {background} x1; .mbAccordionWrap .accd_btn .title-btn:before {background} x1 | module_solutions-tabber.min.css x2; module_two-column-tabber.min.css x1 | 3 |
| 18 | `#bdbdbd` | Gray rule | .tabber_section ul.tabnav {border-bottom} x1; .cnt-wit-bg-wrp.testimonial.announcement tr {border-top} x1; .cnt-wit-bg-wrp.testimonial.announcement tbody:last-child {border-bottom} x1 | template_child_v2.css x2; module_two-column-tabber.min.css x1 | 3 |
| 19 | `#e6e6e6` | Gray disabled text / rules | button:disabled, .button:disabled {color} x1; .post-share-wrapper {border-top} x1; .post-share-wrapper {border-bottom} x1 | template_blog.css x2; template_main.min.css x1 | 3 |
| 20 | `#f2fcff` | Alert bar pale | .header .alert-section {background} x1; header.header .section-icon {background} x1; .header .alert-section {background-color} x1 | template_main.min.css x2; template_theme-overrides.min.css x1 | 3 |
| 21 | `#999999` | Gray error text | footer form .hs-error-msg,footer form .hs_error_rollup label {color} x1; .hs-error-msg,.hs_error_rollup label,.systems-page ul.no-list.hs-error-msgs label {color} x1; .error_content_wrap #search_input-input:focus {border} x1 | template_theme-overrides.min.css x2; template_child_v2.css x1 | 3 |
| 22 | `#cdcdcd` | Search suggest border | .hs-search-field--open .hs-search-field__suggestions,.inpage-editor-active-field .hs-searc {border} x1; .hs-search-field--open .hs-search-field__suggestions, .inpage-editor-active-field .hs-sear {border} x1 | module_search_input.min.css x1; module_home-banner.css x1 | 2 |
| 23 | `#cccccc` | hr gray | hr {background-color} x1; hr {color} x1 | template_main.min.css x2 | 2 |
| 24 | `#d0d0d0` | Disabled button gray | button:disabled, .button:disabled {background-color} x1; button:disabled, .button:disabled {border-color} x1 | template_main.min.css x2 | 2 |
| 25 | `#94b4d9` | Desktop menu divider blue | header.header .nav .header__menu.header__menu--desktop> ul >li:first-child {border-top} x1; header.header .nav .header__menu.header__menu--desktop ul >li:not(:last-child) {border-bottom} x1 | template_main.min.css x2 | 2 |
| 26 | `#f5cd3e` | Rating star yellow | .rating .fill svg path {fill} x1; .rating svg path {stroke} x1 | template_main.min.css x2 | 2 |
| 27 | `#15c0ea` | Cyan (10% overlays) | .blog-feedV2 .overlay_bg.bg_primary,.blog-index__post-inner-card .overlay_bg.bg_primary {background} x1; .blog-feedV2 .overlay_bg.bg_secondary,.blog-index__post-inner-card .overlay_bg.bg_secondar {background} x1 _(alphas: 0.1: 2)_ | template_theme-overrides.min.css x2 | 2 |
| 28 | `#e4f3f2` | Pale Teal | .post-featured-image-wrapper div#featured-blog-panel {background} x1; .blog-wit-sidbr .blog-index__post-image.hs-featured-wrp {background} x1 | template_blog.css x2 | 2 |
| 29 | `#dcdcde` | Divider gray | .custom-related-post-content .related-post-group > h3 em::before {border-top} x1; .team-member .top_sec .title:before {border-top} x1 | template_blog.css x1; template_child_v2.css x1 | 2 |
| 30 | `#767676` | Form legend gray | form legend {color} x1; footer.footer.footer_section__2.cst-footer form legend {color} x1 | template_child_v2.css x2 | 2 |
| 31 | `#c02b0a` | Form error red | .hs-error-msg, .hs_error_rollup label, .systems-page ul.no-list.hs-error-msgs label {color} x1; footer.footer.footer_section__2.cst-footer form .hs-error-msg, footer.footer.footer_sectio {color} x1 | template_child_v2.css x2 | 2 |
| 32 | `#1c8b38` | Menu link green | .cst-header-menu .hs-menu-wrapper>ul>li.solutions>ul>li>a {color} x1; .mobile_menu .hs-menu-wrapper>ul>li.solutions>ul>li>a {color} x1 | template_child_v2.css x2 | 2 |
| 33 | `#eeeeee` | Table rule gray | .cnt-wit-tp-img-wrp.full-width-content table tbody {border-bottom} x1; .cnt-wit-tp-img-wrp.full-width-content table tbody tr {border-top} x1 | template_child_v2.css x2 | 2 |
| 34 | `#467886` | Inline text teal (content) | span[style] {color} x2 | https://acentra.com/solutions/ (style attr) x2 | 2 |
| 35 | `#7a7a7a` | Shadow gray | .hs-search-field--open .hs-search-field__suggestions, .inpage-editor-active-field .hs-sear {box-shadow} x1 _(alphas: 0.75: 1)_ | module_home-banner.css x1 | 1 |
| 36 | `#fff9fc` | Social icon bg | .header .social-share ul>li>a {background} x1 | template_main.min.css x1 | 1 |
| 37 | `#ff1515` | Close-icon text-shadow red | .header .close-icon {text-shadow} x1 | template_main.min.css x1 | 1 |
| 38 | `#005f68` | Deep Teal (h2) | .h2,h2 {color} x1 | template_theme-overrides.min.css x1 | 1 |
| 39 | `#495057` | Alert link gray | .header .alert-section a {color} x1 | template_theme-overrides.min.css x1 | 1 |
| 40 | `#12153f` | Blog panel navy | .post-featured-image-wrapper div#featured-blog-panel h1::After {background} x1 | template_blog.css x1 | 1 |
| 41 | `#801700` | Required-field red | span.hs-form-required {color} x1 | template_child_v2.css x1 | 1 |
| 42 | `#d9d9d9` | Menu divider gray | .cst-header-menu .hs-menu-wrapper>ul>li.solutions>ul>li:nth-child(4):before {background} x1 | template_child_v2.css x1 | 1 |
| 43 | `#d7d7d7` | 404 glyph gray | .error-page:before {color} x1 | template_child_v2.css x1 | 1 |
| 44 | `#00d082` | Search hover green | .cst-header .search-wrapper ul.hs-search-field__suggestions li a:hover {color} x1 | template_child_v2.css x1 | 1 |
| 45 | `#042125` | Hero Ink (image) | home hero background (dominant pixel of hero-bg.jpg; = #042126 ink within JPEG rounding) (pixel-sampled, not in CSS) | hero-bg.jpg | pixel |
| 46 | `#1e373c` | Hero watermark teal (image) | home hero large "A" watermark shape (2nd pixel colour of hero-bg.jpg) (pixel-sampled, not in CSS) | hero-bg.jpg | pixel |
| 47 | `#028202` | Announcement bar green (HubSpot CTA) | top announcement bar "Acentra Health Welcomes FEI Systems" (HubSpot CTA iframe, pixel-sampled from headless-Chrome render; not in site CSS, third-party embed) (pixel-sampled, not in CSS) | https://acentra.com/ (rendered screenshot acentra_home.png) | pixel |

### 1.3 Fonts, spacing, radius found

| Item | Found on acentra.com | Source |
|---|---|---|
| Body font | **Inter** 400/700 from Google Fonts. Also aliased via `@font-face{font-family:"'Inter_regular', sans-serif"; src: fonts.gstatic.com/s/inter/v12/…}`. Computed `body` is 18px, line-height 33.84px (1.88), `#042126` | `<link href="https://fonts.googleapis.com/css2?family=Inter:…">`, template_child_v2.css, computed_styles.json |
| Heading font | **Roboto** 700/400 via HubSpot's Google-font proxy (`/_hcms/googlefonts/Roboto/700.woff2`). Computed h1 is 65px (home) / 50px (about), lh 1.2. h2 is 40px/48px `#005f68`. Eyebrow h6 is 17px, uppercase, letter-spacing 3px, `#1c873e` / `#209b47` | fonts_network.json, computed_probe.json |
| Other fonts | Oswald (proxy-loaded, little use), Lato 400 (HubSpot widgets), Mulish (named in blog CSS, never loaded), Font Awesome 6.2.1 | fonts_network.json |
| Base size / line height | 18px / 1.88 (marketing). Theme heading line-height 1.2 | theme-overrides.min.css |
| Weights in use | 700 (74 rules), 400 (50), 500 (12), 600 (1) | typography_spacing_sampled.json |
| Container | `.page-center{max-width:1210px}` (theme). Computed max-width **1500px** (child theme) | theme-overrides, computed |
| Spacing | 10/15/20/30/40/50/90px, a 5px rhythm. Sections padded 90px top and bottom | typography_spacing_sampled.json |
| Radius | Buttons are 40px pills (header 25px). Cards and accordions are **4px**. Most blocks are 0. Also seen: 5, 6, 10px | theme-overrides, child_v2 |
| Shadows | `rgba(0,0,0,.1–.16)` soft card shadows and teal `rgba(17,97,91,.1–.3)` | child_v2, module_features |

**Unverifiable or caveated:**
- I found no official brand book. "Primary green = `#2bbc2b`" is inferred from the logo pixels and 142 CSS uses.
- `#028202` (announcement bar) comes from a third-party HubSpot CTA iframe and is pixel-only, so it is not adopted.
- `#c6c6c6` (115 uses) is a content-editor highlight inside body copy, not a brand colour.
- The hero `#042125` equals ink `#042126` within JPEG rounding.
- No licensed font is involved: Inter (SIL OFL) and Roboto (Apache 2.0) are both free.

**Deliberate deviations from acentra.com:**
- 4px spacing base instead of 5px, because data UI needs finer steps.
- 4/6px radius instead of 40px pill buttons. Pills read as marketing and waste horizontal space in toolbars and tables.
- One UI family (Inter) instead of Inter + Roboto. A single family is calmer at small sizes, and Inter has proper `tnum`.

---

## 2. Colour tokens and rationale

Two layers live in `tokens.css`. **Primitives** (`--green-*`, `--neutral-*`, `--slate-*`, `--amber-*`, `--orange-*`, `--red-*`, `--plum-*`, `--acentra-*`) are never referenced by components. **Semantic aliases** (`--color-*`, `--risk-*`, `--harm-*`, `--chart-*`, `--graph-*`) are the only thing components use.

### 2.1 The green ramp
The ramp is built in OKLCH at hue ~147 and anchored on the three sampled Acentra greens, which keep their exact hex at the step where their lightness lands:

| Step | Hex | Note |
|---|---|---|
| 50 | `#ecfced` | `--color-brand-subtle` (selected row/card bg) |
| 100–300 | `#d9f8db` `#b8f1bd` `#90e39a` | Rarely used; 300 is dark-theme brand text |
| 400 | `#5cd370` | `--color-brand-hover` (lighter on hover, like Acentra's lime hover, but calmer) |
| **500** | **`#2bbc2b`** | **Acentra Green.** `--color-brand`, `--color-brand-bar` |
| **600** | **`#209b47`** | **Acentra Dark Green.** `--color-brand-active`, `--color-brand-strong`, `--chart-1` |
| **700** | **`#1c873e`** | **Acentra Eyebrow Green.** `--color-focus`, graph subject fill |
| 800 | `#1e672d` | `--color-brand-text` (green text, 6.92:1) |
| 900–950 | `#174c21` `#103216` | Reserve |

**Why the primary button uses ink text, not white:** white on `#2bbc2b` is **2.52:1**, which fails. Acentra itself pairs `#042126` ink on `#2bbc2b` (`.hs-button{color:#042126}`), which gives **6.66:1**. We keep Acentra's exact pairing.

### 2.2 Neutrals: teal-tinted, from the ink
The neutrals are OKLCH hue 200 with chroma 0.003–0.03, sitting between Acentra ink (`#042126`, hue 211) and the Acentra teals (`#11615b` / `#e4f3f2`, hue ~190). `--neutral-950` **is** the Acentra ink. The result is a very slightly green-blue gray that belongs to the brand. It is not Tailwind slate (hue ~257, visibly bluish-purple), and it is not a dead `#888` gray.

| Semantic | Value | Use |
|---|---|---|
| `--color-bg` | `--neutral-50` `#f1f6f6` | Page canvas |
| `--color-surface` | `#ffffff` | Cards, tables, graph canvas |
| `--color-surface-raised` | `#ffffff` + `--shadow-overlay` | Menus, tooltips, drawers |
| `--color-surface-sunken` | `--neutral-100` `#e8efef` | Table header, metric strips, JSON/evidence blocks |
| `--color-surface-hover` | `#f4f8f8` | Row hover |
| `--color-border` | `--neutral-200` `#d1dbdc` | 1px card and row dividers |
| `--color-border-strong` | `--neutral-500` `#748484` | Inputs and checkboxes (3.91:1) |
| `--color-text` | `#042126` | 16.79:1 |
| `--color-text-muted` | `--neutral-700` `#495b5b` | 7.17:1 |
| `--color-text-subtle` | `--neutral-600` `#5d6e6f` | 5.35:1 (captions, placeholders) |

### 2.3 Brand vs data vs risk vs harm: the separation rule

| Channel | Tokens | Allowed for | Never for |
|---|---|---|---|
| **Brand** | `--color-brand*`, `--color-focus`, `--color-brand-bar` | Primary button, active nav underline, focus ring, selected row/card, the 3px brand bar, graph case subject | Data series by default, "OK/low/safe" states, large backgrounds |
| **Data (categorical)** | `--chart-1..8`, `--chart-focus`, `--chart-comparison` | Charts whose series are categories (detector type, specialty) | Encoding risk or harm |
| **Risk** | `--risk-{low,medium,high,critical}-{bg,fg,border,solid}` + glyph + label | Case/provider fraud-risk level (today: `case.severity` 1–4), graph node rings, risk-encoded charts | Lanes, statuses, decoration |
| **Harm** | `--harm-{bg,fg,border,solid}` + ✚ glyph | Patient-harm flag (`case.harm ≥ 3`), harm-priority lane, graph harm notch, timeline harm events | Financial risk |
| **Status** | `--color-{info,success,warning,danger}-*` | System feedback: saved, error, chain verified, form errors | Case risk |

**Why low risk is slate-blue, not green.** If low risk were green, every queue would fill with brand-coloured rows. The brand would compete with the data, and green would come to mean "safe", which is wrong for an SIU tool: a low score is not an exoneration. Slate-blue reads as "noted, cool, low urgency" and stays clear of the brand.

**Why harm is its own axis.** A $40 claim for a service after a beneficiary's death, or impossible home-health hours for a vulnerable member, can mean real harm to a patient at low dollar value. Ranking by money alone would bury it. The app already models this (`harm` 1–4 and the `harm_priority` lane that overrides capacity). Harm therefore gets:
- a distinct hue (plum `#94296f`), outside the risk ramp so it never reads as "more than critical";
- a distinct glyph, ✚ (medical cross), rather than a point on the ○◐●◆ sequence;
- a distinct placement: a flag next to the risk badge on cards and rows, and a notch on graph nodes rather than a ring.

### 2.4 Risk scale

| Level | Data (today) | Glyph | `-bg` | `-fg` | `-border` | `-solid` (rings, marks) | OKLCH L of solid |
|---|---|---|---|---|---|---|---|
| Low | severity 1 | ○ open circle | `#eef4fb` | `#2f4a67` | `#7089a4` | `#597797` | 0.56 |
| Medium | severity 2 | ◐ half circle | `#fef2d9` | `#71440c` | `#b37d24` | `#bf8105` | 0.65 |
| High | severity 3 | ● filled circle | `#ffece0` | `#883500` | `#b85207` | `#b14c03` | 0.54 |
| Critical | severity 4 | ◆ filled diamond | `#fee9e8` | `#7c1117` | `#9e2225` | `#90101a` | 0.42 |

**Colour-blind check.** I simulated the solids with Machado et al. (2009) at severity 1.0 and measured CIEDE2000 between them:

| Pair | Normal | Deuteranopia | Protanopia | Tritanopia |
|---|---:|---:|---:|---:|
| Low ↔ Medium | 42.2 | 45.9 | 42.8 | 42.8 |
| Medium ↔ High | 20.5 | 12.2 | 16.2 | 15.1 |
| High ↔ Critical | 19.8 | 14.0 | 17.0 | 11.6 |
| Critical ↔ Harm | 23.7 | 31.1 | 33.1 | 13.3 |
| Low ↔ Harm | 34.1 | 10.6 | 17.5 | 47.4 |

The first pass had High at L 0.585, which gave Medium ↔ High only **6.8** under deuteranopia. I darkened High to L 0.54 and Critical to L 0.42, so the warm steps now fall in lightness as severity rises. Glyph shape is the primary non-colour cue in every case.

### 2.5 Patient harm
`--harm-bg #fdeaf4`, `--harm-fg #752257`, `--harm-border #9b3876`, `--harm-solid #94296f`, glyph ✚. Label format: **"✚ Harm 4"**. Show the flag for harm ≥ 3. For harm 1–2, print the number as plain muted text in the table column, with no flag.

### 2.6 Chart palette

| Token | Hex | Origin | On white |
|---|---|---|---:|
| `--chart-1` | `#209b47` | Acentra dark green (starts from the brand) | 3.60 |
| `--chart-2` | `#0072b2` | Okabe-Ito blue (exact) | 5.19 |
| `--chart-3` | `#1d3b70` | Navy, the dark partner to chart-2 | 10.98 |
| `--chart-4` | `#005f68` | Acentra deep teal (h2) | 7.40 |
| `--chart-5` | `#8c5a2b` | Brown (Okabe-Ito orange family, darkened; kept away from risk amber/orange) | 5.81 |
| `--chart-6` | `#2f8fd0` | Okabe-Ito sky `#56b4e9`, darkened | 3.52 |
| `--chart-7` | `#b05a8a` | Okabe-Ito reddish purple `#cc79a7`, pushed toward rose (no violet) | 4.49 |
| `--chart-8` | `#b07a00` | Okabe-Ito orange `#e69f00`, darkened | 3.73 |
| `--chart-focus` | `#15497e` | Acentra link blue. The single highlighted series | 9.19 |
| `--chart-comparison` / `-line` | `#94a2a2` / `#748484` | Peer, baseline and "everything else" gray | 2.64 / 3.91 |
| `--chart-grid` / `--chart-axis` / `--chart-baseline` | `#dee6e7` / `#748484` / `#495b5b` | Gridlines / axis and ticks / zero line | 1.27 / 3.91 / 7.17 |

**Deuteranopia/protanopia/tritanopia check** (min CIEDE2000 across all pairs, Machado 2009):

| Set | Normal | Deutan | Protan | Tritan | Weakest pair |
|---|---:|---:|---:|---:|---|
| chart-1..5 | 19.6 | 10.2 | 15.3 | 11.2 | chart-1 vs chart-5 (deutan); every pair ≥ 10 |
| chart-1..7 | 11.0 | 10.2 | 9.0 | 9.3 | chart-2 vs chart-7 (protan) |
| chart-1..8 | 11.0 | 9.9 | **7.6** | 8.9 | chart-1 vs chart-8 (protan) |

Rules that follow from the check:
- A chart has at most **5** categorical series. With 6 or more, use small multiples.
- chart-8 is never placed next to chart-1.
- Amber, orange and red were deliberately kept **out** of the categorical palette so that a category is never mistaken for a risk level. In the first draft, Okabe-Ito amber collapsed into brand green under protanopia (ΔE **6.2**), which is why it was dropped from the early slots.
- The simulation strips are in `brand-evidence/palette.png`.

---

## 3. Contrast table (computed)

Generated by `python3 scripts/contrast_from_tokens.py`. The script parses `tokens.css`, resolves every `var()` chain for `:root` and `[data-theme="dark"]`, and computes WCAG 2.x ratios. Requirements: text ≥ 4.5:1; state-carrying UI (focus ring, input borders, selected bars, risk/harm borders and rings, chart marks) ≥ 3:1. **Result: 146 pairs, 0 failures.**

**Fixes made while building the system:**

| Problem found (computed) | Fix |
|---|---|
| `--green-700 #1c873e` as **text** on bg: 4.20:1, on sunken: 3.93:1 | Green text uses `--color-brand-text` = `--green-800 #1e672d` (6.92:1). green-700 is kept for the focus ring only (≥ 3:1 on every surface) |
| `#2bbc2b` as a state indicator (selected bar / active underline) on white: 2.52:1 | State indicators use `--color-brand-strong` = `#209b47` (3.60:1 on surface, 3.38:1 on brand-subtle). `#2bbc2b` is limited to button fills (with ink text, 6.66:1) and the decorative brand bar |
| White glyph on a `#2bbc2b` graph subject: 2.52:1 | Subject fill = `--green-700`, giving white glyph 4.58:1 |
| White text on a `#2bbc2b` button: 2.52:1 | Ink text (Acentra's own pairing): 6.66:1 |
| Risk High/Critical too close to Medium under deuteranopia (ΔE 6.8) | High solid L 0.585 → 0.54, Critical L 0.47 → 0.42 (ΔE now 12.2 / 14.0) |
| Amber in the categorical slots collided with green under protanopia (ΔE 6.2) | Removed warm hues from chart-2..7 |

**Current app (`src/index.css`) failures this system replaces:**
- White on `.badge.lane-selected` (`#1aa24c`): **3.32:1**, small text, fails.
- Focus ring `#1aa24c` on `--paper`: **2.96:1**, fails 3:1.
- `.qc-tick #7a939b` 10px labels on white: **3.24:1**, fails.
- Input border `--rule #d5e4da`: **1.32:1**, fails 3:1.
- `.factor-track i #1fbf5a` on its track: **2.05:1**.

| Theme | Group | Pair | FG | BG | Ratio | Needs | Result |
|---|---|---|---|---|---:|---:|---|
| light | Text (≥4.5) | text on bg | `#042126` | `#f1f6f6` | 15.39 | 4.5 | PASS |
| light | Text (≥4.5) | text on surface | `#042126` | `#ffffff` | 16.79 | 4.5 | PASS |
| light | Text (≥4.5) | text on surface-sunken | `#042126` | `#e8efef` | 14.41 | 4.5 | PASS |
| light | Text (≥4.5) | text on surface-hover | `#042126` | `#f4f8f8` | 15.69 | 4.5 | PASS |
| light | Text (≥4.5) | text-muted on bg | `#495b5b` | `#f1f6f6` | 6.57 | 4.5 | PASS |
| light | Text (≥4.5) | text-muted on surface | `#495b5b` | `#ffffff` | 7.17 | 4.5 | PASS |
| light | Text (≥4.5) | text-muted on surface-sunken | `#495b5b` | `#e8efef` | 6.15 | 4.5 | PASS |
| light | Text (≥4.5) | text-muted on surface-hover | `#495b5b` | `#f4f8f8` | 6.70 | 4.5 | PASS |
| light | Text (≥4.5) | text-subtle on bg | `#5d6e6f` | `#f1f6f6` | 4.90 | 4.5 | PASS |
| light | Text (≥4.5) | text-subtle on surface | `#5d6e6f` | `#ffffff` | 5.35 | 4.5 | PASS |
| light | Text (≥4.5) | text-subtle on surface-sunken | `#5d6e6f` | `#e8efef` | 4.59 | 4.5 | PASS |
| light | Text (≥4.5) | text-subtle on surface-hover | `#5d6e6f` | `#f4f8f8` | 5.00 | 4.5 | PASS |
| light | Text (≥4.5) | link on bg | `#15497e` | `#f1f6f6` | 8.42 | 4.5 | PASS |
| light | Text (≥4.5) | link on surface | `#15497e` | `#ffffff` | 9.19 | 4.5 | PASS |
| light | Text (≥4.5) | link on surface-sunken | `#15497e` | `#e8efef` | 7.88 | 4.5 | PASS |
| light | Text (≥4.5) | link on surface-hover | `#15497e` | `#f4f8f8` | 8.59 | 4.5 | PASS |
| light | Text (≥4.5) | brand-text on bg | `#1e672d` | `#f1f6f6` | 6.35 | 4.5 | PASS |
| light | Text (≥4.5) | brand-text on surface | `#1e672d` | `#ffffff` | 6.92 | 4.5 | PASS |
| light | Text (≥4.5) | brand-text on surface-sunken | `#1e672d` | `#e8efef` | 5.94 | 4.5 | PASS |
| light | Text (≥4.5) | brand-text on surface-hover | `#1e672d` | `#f4f8f8` | 6.47 | 4.5 | PASS |
| light | Text (≥4.5) | text on brand-subtle (selected row) | `#042126` | `#ecfced` | 15.76 | 4.5 | PASS |
| light | Text (≥4.5) | text-muted on brand-subtle | `#495b5b` | `#ecfced` | 6.73 | 4.5 | PASS |
| light | Brand (≥4.5) | text-on-brand on brand (primary button) | `#042126` | `#2bbc2b` | 6.66 | 4.5 | PASS |
| light | Brand (≥4.5) | text-on-brand on brand-hover | `#042126` | `#5cd370` | 8.80 | 4.5 | PASS |
| light | Brand (≥4.5) | text-on-brand on brand-active | `#042126` | `#209b47` | 4.67 | 4.5 | PASS |
| light | Brand (≥4.5) | white glyph on graph subject fill | `#ffffff` | `#1c873e` | 4.58 | 4.5 | PASS |
| light | UI state (≥3) | focus ring on bg | `#1c873e` | `#f1f6f6` | 4.20 | 3.0 | PASS |
| light | UI state (≥3) | border-strong on bg | `#748484` | `#f1f6f6` | 3.58 | 3.0 | PASS |
| light | UI state (≥3) | focus ring on surface | `#1c873e` | `#ffffff` | 4.58 | 3.0 | PASS |
| light | UI state (≥3) | border-strong on surface | `#748484` | `#ffffff` | 3.91 | 3.0 | PASS |
| light | UI state (≥3) | focus ring on surface-sunken | `#1c873e` | `#e8efef` | 3.93 | 3.0 | PASS |
| light | UI state (≥3) | border-strong on surface-sunken | `#748484` | `#e8efef` | 3.35 | 3.0 | PASS |
| light | UI state (≥3) | brand-strong (active nav underline) on surface | `#209b47` | `#ffffff` | 3.60 | 3.0 | PASS |
| light | UI state (≥3) | brand-strong (selected-row bar) on brand-subtle | `#209b47` | `#ecfced` | 3.38 | 3.0 | PASS |
| light | Risk badge | risk-low-fg on risk-low-bg (≥4.5) | `#2f4a67` | `#eef4fb` | 8.26 | 4.5 | PASS |
| light | Risk badge | risk-low-border on risk-low-bg (≥3) | `#7089a4` | `#eef4fb` | 3.27 | 3.0 | PASS |
| light | Risk badge | risk-low-border on surface (≥3) | `#7089a4` | `#ffffff` | 3.62 | 3.0 | PASS |
| light | Risk badge | risk-low-solid on surface, graph ring (≥3) | `#597797` | `#ffffff` | 4.66 | 3.0 | PASS |
| light | Risk badge | risk-medium-fg on risk-medium-bg (≥4.5) | `#71440c` | `#fef2d9` | 7.46 | 4.5 | PASS |
| light | Risk badge | risk-medium-border on risk-medium-bg (≥3) | `#b37d24` | `#fef2d9` | 3.22 | 3.0 | PASS |
| light | Risk badge | risk-medium-border on surface (≥3) | `#b37d24` | `#ffffff` | 3.57 | 3.0 | PASS |
| light | Risk badge | risk-medium-solid on surface, graph ring (≥3) | `#bf8105` | `#ffffff` | 3.30 | 3.0 | PASS |
| light | Risk badge | risk-high-fg on risk-high-bg (≥4.5) | `#883500` | `#ffece0` | 7.17 | 4.5 | PASS |
| light | Risk badge | risk-high-border on risk-high-bg (≥3) | `#b85207` | `#ffece0` | 4.31 | 3.0 | PASS |
| light | Risk badge | risk-high-border on surface (≥3) | `#b85207` | `#ffffff` | 4.94 | 3.0 | PASS |
| light | Risk badge | risk-high-solid on surface, graph ring (≥3) | `#b14c03` | `#ffffff` | 5.38 | 3.0 | PASS |
| light | Risk badge | risk-critical-fg on risk-critical-bg (≥4.5) | `#7c1117` | `#fee9e8` | 9.25 | 4.5 | PASS |
| light | Risk badge | risk-critical-border on risk-critical-bg (≥3) | `#9e2225` | `#fee9e8` | 6.66 | 3.0 | PASS |
| light | Risk badge | risk-critical-border on surface (≥3) | `#9e2225` | `#ffffff` | 7.75 | 3.0 | PASS |
| light | Risk badge | risk-critical-solid on surface, graph ring (≥3) | `#90101a` | `#ffffff` | 9.23 | 3.0 | PASS |
| light | Harm | harm-fg on harm-bg (≥4.5) | `#752257` | `#fdeaf4` | 8.60 | 4.5 | PASS |
| light | Harm | harm-border on harm-bg (≥3) | `#9b3876` | `#fdeaf4` | 5.67 | 3.0 | PASS |
| light | Harm | harm-solid on surface (≥3) | `#94296f` | `#ffffff` | 7.48 | 3.0 | PASS |
| light | Chart | chart-focus on surface (≥3) | `#15497e` | `#ffffff` | 9.19 | 3.0 | PASS |
| light | Chart | chart-axis on surface (≥3) | `#748484` | `#ffffff` | 3.91 | 3.0 | PASS |
| light | Chart | chart-baseline on surface (≥3) | `#495b5b` | `#ffffff` | 7.17 | 3.0 | PASS |
| light | Chart | chart-comparison-line on surface (≥3) | `#748484` | `#ffffff` | 3.91 | 3.0 | PASS |
| light | Chart | chart-label (tick text) on surface (≥4.5) | `#495b5b` | `#ffffff` | 7.17 | 4.5 | PASS |
| dark | Text (≥4.5) | text on bg | `#e8efef` | `#042126` | 14.41 | 4.5 | PASS |
| dark | Text (≥4.5) | text on surface | `#e8efef` | `#132b2e` | 12.76 | 4.5 | PASS |
| dark | Text (≥4.5) | text on surface-sunken | `#e8efef` | `#031a1e` | 15.40 | 4.5 | PASS |
| dark | Text (≥4.5) | text on surface-hover | `#e8efef` | `#1a3337` | 11.46 | 4.5 | PASS |
| dark | Text (≥4.5) | text-muted on bg | `#bbc7c7` | `#042126` | 9.68 | 4.5 | PASS |
| dark | Text (≥4.5) | text-muted on surface | `#bbc7c7` | `#132b2e` | 8.57 | 4.5 | PASS |
| dark | Text (≥4.5) | text-muted on surface-sunken | `#bbc7c7` | `#031a1e` | 10.34 | 4.5 | PASS |
| dark | Text (≥4.5) | text-muted on surface-hover | `#bbc7c7` | `#1a3337` | 7.70 | 4.5 | PASS |
| dark | Text (≥4.5) | text-subtle on bg | `#a0aeaf` | `#042126` | 7.33 | 4.5 | PASS |
| dark | Text (≥4.5) | text-subtle on surface | `#a0aeaf` | `#132b2e` | 6.49 | 4.5 | PASS |
| dark | Text (≥4.5) | text-subtle on surface-sunken | `#a0aeaf` | `#031a1e` | 7.83 | 4.5 | PASS |
| dark | Text (≥4.5) | text-subtle on surface-hover | `#a0aeaf` | `#1a3337` | 5.83 | 4.5 | PASS |
| dark | Text (≥4.5) | link on bg | `#97c2f0` | `#042126` | 9.03 | 4.5 | PASS |
| dark | Text (≥4.5) | link on surface | `#97c2f0` | `#132b2e` | 7.99 | 4.5 | PASS |
| dark | Text (≥4.5) | link on surface-sunken | `#97c2f0` | `#031a1e` | 9.65 | 4.5 | PASS |
| dark | Text (≥4.5) | link on surface-hover | `#97c2f0` | `#1a3337` | 7.18 | 4.5 | PASS |
| dark | Text (≥4.5) | brand-text on bg | `#90e39a` | `#042126` | 10.91 | 4.5 | PASS |
| dark | Text (≥4.5) | brand-text on surface | `#90e39a` | `#132b2e` | 9.66 | 4.5 | PASS |
| dark | Text (≥4.5) | brand-text on surface-sunken | `#90e39a` | `#031a1e` | 11.65 | 4.5 | PASS |
| dark | Text (≥4.5) | brand-text on surface-hover | `#90e39a` | `#1a3337` | 8.67 | 4.5 | PASS |
| dark | Text (≥4.5) | text on brand-subtle (selected row) | `#e8efef` | `#1f3a25` | 10.66 | 4.5 | PASS |
| dark | Text (≥4.5) | text-muted on brand-subtle | `#bbc7c7` | `#1f3a25` | 7.16 | 4.5 | PASS |
| dark | Brand (≥4.5) | text-on-brand on brand (primary button) | `#042126` | `#2bbc2b` | 6.66 | 4.5 | PASS |
| dark | UI state (≥3) | focus ring on bg | `#5cd370` | `#042126` | 8.80 | 3.0 | PASS |
| dark | UI state (≥3) | border-strong on bg | `#6d7e7f` | `#042126` | 3.95 | 3.0 | PASS |
| dark | UI state (≥3) | focus ring on surface | `#5cd370` | `#132b2e` | 7.79 | 3.0 | PASS |
| dark | UI state (≥3) | border-strong on surface | `#6d7e7f` | `#132b2e` | 3.50 | 3.0 | PASS |
| dark | UI state (≥3) | focus ring on surface-sunken | `#5cd370` | `#031a1e` | 9.40 | 3.0 | PASS |
| dark | UI state (≥3) | border-strong on surface-sunken | `#6d7e7f` | `#031a1e` | 4.22 | 3.0 | PASS |
| dark | UI state (≥3) | brand-strong (active nav underline) on surface | `#2bbc2b` | `#132b2e` | 5.90 | 3.0 | PASS |
| dark | UI state (≥3) | brand-strong (selected-row bar) on brand-subtle | `#2bbc2b` | `#1f3a25` | 4.93 | 3.0 | PASS |
| dark | Risk badge | risk-low-fg on risk-low-bg (≥4.5) | `#badbfe` | `#1e2f41` | 9.53 | 4.5 | PASS |
| dark | Risk badge | risk-low-border on risk-low-bg (≥3) | `#619dda` | `#1e2f41` | 4.77 | 3.0 | PASS |
| dark | Risk badge | risk-low-border on surface (≥3) | `#619dda` | `#132b2e` | 5.20 | 3.0 | PASS |
| dark | Risk badge | risk-low-solid on surface, graph ring (≥3) | `#619dda` | `#132b2e` | 5.20 | 3.0 | PASS |
| dark | Risk badge | risk-medium-fg on risk-medium-bg (≥4.5) | `#f3d2a4` | `#3a2b16` | 9.48 | 4.5 | PASS |
| dark | Risk badge | risk-medium-border on risk-medium-bg (≥3) | `#c08e43` | `#3a2b16` | 4.68 | 3.0 | PASS |
| dark | Risk badge | risk-medium-border on surface (≥3) | `#c08e43` | `#132b2e` | 5.09 | 3.0 | PASS |
| dark | Risk badge | risk-medium-solid on surface, graph ring (≥3) | `#c08e43` | `#132b2e` | 5.09 | 3.0 | PASS |
| dark | Risk badge | risk-high-fg on risk-high-bg (≥4.5) | `#fecbaf` | `#3e281b` | 9.43 | 4.5 | PASS |
| dark | Risk badge | risk-high-border on risk-high-bg (≥3) | `#cf8358` | `#3e281b` | 4.62 | 3.0 | PASS |
| dark | Risk badge | risk-high-border on surface (≥3) | `#cf8358` | `#132b2e` | 4.98 | 3.0 | PASS |
| dark | Risk badge | risk-high-solid on surface, graph ring (≥3) | `#cf8358` | `#132b2e` | 4.98 | 3.0 | PASS |
| dark | Risk badge | risk-critical-fg on risk-critical-bg (≥4.5) | `#fec8c3` | `#402624` | 9.38 | 4.5 | PASS |
| dark | Risk badge | risk-critical-border on risk-critical-bg (≥3) | `#d47c76` | `#402624` | 4.57 | 3.0 | PASS |
| dark | Risk badge | risk-critical-border on surface (≥3) | `#d47c76` | `#132b2e` | 4.92 | 3.0 | PASS |
| dark | Risk badge | risk-critical-solid on surface, graph ring (≥3) | `#d47c76` | `#132b2e` | 4.92 | 3.0 | PASS |
| dark | Harm | harm-fg on harm-bg (≥4.5) | `#fac6e2` | `#3c2632` | 9.40 | 4.5 | PASS |
| dark | Harm | harm-border on harm-bg (≥3) | `#c87ca8` | `#3c2632` | 4.56 | 3.0 | PASS |
| dark | Harm | harm-solid on surface (≥3) | `#c87ca8` | `#132b2e` | 4.89 | 3.0 | PASS |
| dark | Chart | chart-focus on surface (≥3) | `#97c2f0` | `#132b2e` | 7.99 | 3.0 | PASS |
| dark | Chart | chart-axis on surface (≥3) | `#6d7e7f` | `#132b2e` | 3.50 | 3.0 | PASS |
| dark | Chart | chart-baseline on surface (≥3) | `#bbc7c7` | `#132b2e` | 8.57 | 3.0 | PASS |
| dark | Chart | chart-comparison-line on surface (≥3) | `#7f8f90` | `#132b2e` | 4.41 | 3.0 | PASS |
| dark | Chart | chart-label (tick text) on surface (≥4.5) | `#bbc7c7` | `#132b2e` | 8.57 | 4.5 | PASS |
| light | Status | info-fg on info-bg (≥4.5) | `#15497e` | `#ebf5fd` | 8.32 | 4.5 | PASS |
| light | Status | info-border on info-bg (≥3) | `#557ea8` | `#ebf5fd` | 3.85 | 3.0 | PASS |
| light | Status | success-fg on success-bg (≥4.5) | `#1e672d` | `#ecfced` | 6.50 | 4.5 | PASS |
| light | Status | success-border on success-bg (≥3) | `#209b47` | `#ecfced` | 3.38 | 3.0 | PASS |
| light | Status | warning-fg on warning-bg (≥4.5) | `#71440c` | `#fef2d9` | 7.46 | 4.5 | PASS |
| light | Status | warning-border on warning-bg (≥3) | `#b37d24` | `#fef2d9` | 3.22 | 3.0 | PASS |
| light | Status | danger-fg on danger-bg (≥4.5) | `#972622` | `#feebe9` | 6.98 | 4.5 | PASS |
| light | Status | danger-border on danger-bg (≥3) | `#b33832` | `#feebe9` | 5.18 | 3.0 | PASS |
| light | Chart | chart-1 on surface (≥3) | `#209b47` | `#ffffff` | 3.60 | 3.0 | PASS |
| light | Chart | chart-2 on surface (≥3) | `#0072b2` | `#ffffff` | 5.19 | 3.0 | PASS |
| light | Chart | chart-3 on surface (≥3) | `#1d3b70` | `#ffffff` | 10.98 | 3.0 | PASS |
| light | Chart | chart-4 on surface (≥3) | `#005f68` | `#ffffff` | 7.40 | 3.0 | PASS |
| light | Chart | chart-5 on surface (≥3) | `#8c5a2b` | `#ffffff` | 5.81 | 3.0 | PASS |
| light | Chart | chart-6 on surface (≥3) | `#2f8fd0` | `#ffffff` | 3.52 | 3.0 | PASS |
| light | Chart | chart-7 on surface (≥3) | `#b05a8a` | `#ffffff` | 4.49 | 3.0 | PASS |
| light | Chart | chart-8 on surface (≥3) | `#b07a00` | `#ffffff` | 3.73 | 3.0 | PASS |
| light | Graph | provider node stroke on its fill (≥3) | `#495b5b` | `#e8efef` | 6.15 | 3.0 | PASS |
| light | Graph | provider node stroke on canvas (≥3) | `#495b5b` | `#ffffff` | 7.17 | 3.0 | PASS |
| light | Graph | owner node stroke on its fill (≥3) | `#71604a` | `#f2ece4` | 5.15 | 3.0 | PASS |
| light | Graph | owner node stroke on canvas (≥3) | `#71604a` | `#ffffff` | 6.04 | 3.0 | PASS |
| light | Graph | facility node stroke on its fill (≥3) | `#11615b` | `#e4f3f2` | 6.38 | 3.0 | PASS |
| light | Graph | facility node stroke on canvas (≥3) | `#11615b` | `#ffffff` | 7.28 | 3.0 | PASS |
| light | Graph | address node stroke on its fill (≥3) | `#5d6e6f` | `#f8fbfb` | 5.14 | 3.0 | PASS |
| light | Graph | address node stroke on canvas (≥3) | `#5d6e6f` | `#ffffff` | 5.35 | 3.0 | PASS |
| light | Graph | phone node stroke on its fill (≥3) | `#5d6e6f` | `#f8fbfb` | 5.14 | 3.0 | PASS |
| light | Graph | phone node stroke on canvas (≥3) | `#5d6e6f` | `#ffffff` | 5.35 | 3.0 | PASS |
| light | Graph | bank node stroke on its fill (≥3) | `#2f4445` | `#e8efef` | 8.86 | 3.0 | PASS |
| light | Graph | bank node stroke on canvas (≥3) | `#2f4445` | `#ffffff` | 10.33 | 3.0 | PASS |
| light | Graph | member node stroke on its fill (≥3) | `#748484` | `#ffffff` | 3.91 | 3.0 | PASS |
| light | Graph | member node stroke on canvas (≥3) | `#748484` | `#ffffff` | 3.91 | 3.0 | PASS |
| light | Graph | edge shared on canvas (≥3) | `#748484` | `#ffffff` | 3.91 | 3.0 | PASS |
| light | Graph | edge ownership on canvas (≥3) | `#2f4445` | `#ffffff` | 10.33 | 3.0 | PASS |
| light | Graph | edge referral on canvas (≥3) | `#005f68` | `#ffffff` | 7.40 | 3.0 | PASS |

**Informational (no requirement, by design):**

| Pair | FG | BG | Ratio | Why it is allowed |
|---|---|---|---:|---|
| brand (#2bbc2b) on surface | `#2bbc2b` | `#ffffff` | 2.52 | Decorative brand bar and button fill only; never text, never a state indicator |
| border on surface | `#d1dbdc` | `#ffffff` | 1.41 | Decorative 1px card/row divider |
| chart-grid on surface | `#dee6e7` | `#ffffff` | 1.27 | Gridlines are deliberately quiet |
| chart-comparison on surface | `#94a2a2` | `#ffffff` | 2.64 | Context bars; always carry a direct value label |
| graph claim edge on canvas | `#bbc7c7` | `#ffffff` | 1.73 | Most numerous edges, kept quiet; type is also in the hover label |
| dimmed node stroke (15% opacity) | `#e4e6e6` | `#ffffff` | 1.25 | Intentionally faded context outside the 2-hop focus |

---

## 4. Typography

**Font: Inter**, Acentra's own body font. It is free (SIL OFL), was designed for UI, and has real `tnum` and `cv11` features. **Mono: Roboto Mono**, which is the monospace companion to Acentra's heading family (Roboto). The repo already self-hosts it: `@fontsource/roboto-mono`, added in commit `e20263c`. Use it for case IDs, NPIs, claim and line IDs, hashes and amounts in table cells. **IBM Plex Mono**, still in the `index.html` Google link, is the fallback only. Roboto itself (Acentra's headings) is **not** used for app UI text, because one proportional family keeps a dense UI calm. Acceptable variant: Roboto 700 for the page `h1` only, to echo acentra.com, and never in tables, charts or controls. Fraunces and Outfit stay loaded **only** because the landing and login pages use them.

Loading: fonts are self-hosted through fontsource. The packages are in `package.json` as of `e20263c`; the import lines below are not committed yet.
```ts
// src/main.tsx
import "@fontsource-variable/inter";        // family "Inter Variable", wght 100–900, keeps tnum/cv11
import "@fontsource/roboto-mono/400.css";   // family "Roboto Mono"
import "@fontsource/roboto-mono/500.css";   // medium: emphasised amounts / IDs in selected rows
import "./styles/tokens.css";               // this repo's tokens.css (see §11)
```
`--font-sans` is `"Inter Variable", "Inter", system-ui, …` and `--font-mono` is `"Roboto Mono", "IBM Plex Mono", ui-monospace, …`. The Cytoscape canvas (§7) only paints fonts that are already loaded, so call `await document.fonts.load('500 11px "Inter Variable"')` before creating the graph.

**Scale** (rem at a 16px root; UI body is 14px because SIU screens are dense tables, not marketing copy):

| Role | Token | Size / line-height | Weight | Tracking | Use |
|---|---|---|---|---|---|
| display | `--type-display` | 36 / 44 | 600 | -0.011em | Rare: empty-state hero |
| h1 | `--type-h1` | 24 / 32 | 600 | -0.011em | Page title ("Today's queue") |
| h2 | `--type-h2` | 20 / 28 | 600 | -0.011em | Section title, workspace case name |
| h3 | `--type-h3` | 18 / 24 | 600 | 0 | Drawer title, panel title |
| h4 | `--type-h4` | 16 / 24 | 600 | 0 | Card title |
| body | `--type-body` | 14 / 20 | 400 | 0 | Default UI text |
| body-sm | `--type-body-sm` | 13 / 18 | 400 | 0 | Table cells, secondary copy |
| label | `--type-label` | 13 / 18 | 500 | 0 | Form labels, buttons, nav |
| caption | `--type-caption` | 12 / 16 | 400 | 0 | Chart ticks, helper text, timestamps |
| overline | `--type-overline` | 12 / 16 | 600 | 0.06em, UPPERCASE | Card kicker. It echoes Acentra's eyebrow h6 (17px, 3px tracking) at UI scale |
| numeric-lg | `--type-numeric-lg` | 30 / 36 | 600 | -0.011em + `tabular-nums` | KPI tile value |
| mono | `--type-mono` | 13 / 18 | 400 | 0 | IDs, NPIs, hashes, amounts in cells |

Why 12/13/14/16/18/20/24/30/36: 12–14 gives three dense data sizes a pixel apart, which tables, labels and body text need; 16–24 rises in roughly 1.2× steps for hierarchy; 30 and 36 are reserved for KPI and display use. That is nine sizes, and nothing else is allowed.

```css
/* data everywhere */
.app { font: var(--type-body); color: var(--color-text); background: var(--color-bg);
       font-feature-settings: "cv11" 1; /* Inter single-storey a: optional, calmer */ }
.app :is(table, .kpi, .badge, .chart, dd, .num) { font-variant-numeric: tabular-nums lining-nums; }
.overline { font: var(--type-overline); letter-spacing: var(--letter-spacing-wide); text-transform: uppercase; color: var(--color-text-muted); }
.page-head .overline { color: var(--color-brand-text); } /* the ONE place green text is allowed */
.mono { font: var(--type-mono); }
```
In SVG, `font-variant-numeric` is supported on `<text>` in Chromium and Firefox. Add `font-feature-settings: var(--font-features-data)` as a fallback.

---

## 5. Spacing, radius, elevation, motion

| Group | Tokens |
|---|---|
| Spacing (4px base) | `--space-0-5` 2 · `--space-1` 4 · `--space-1-5` 6 · `--space-2` 8 · `--space-3` 12 · `--space-4` 16 · `--space-5` 20 · `--space-6` 24 · `--space-8` 32 · `--space-10` 40 · `--space-12` 48 · `--space-16` 64 |
| Radius | `--radius-xs` 2 (bar ends) · `--radius-sm` **4** (inputs, buttons, badges; matches Acentra cards/accordions) · `--radius-md` **6** (cards, panels, popovers) · `--radius-full` (dots and avatars only) |
| Border widths | `--border-width` 1 · `--border-width-strong` 2 · `--border-width-accent` 3 (brand bar, selected-row bar, active nav underline; Acentra's tab underline is `3px solid #2bbc2b`) |
| Focus | `--focus-ring`: 2px surface gap + 2px `--color-focus` (`#1c873e`) |
| Elevation | Cards: **none** (1px border). `--shadow-overlay` for menus, tooltips and popovers. `--shadow-overlay-lg` for drawers and modals |
| Z-index | base 0 · sticky 10 · shell 20 · dropdown 30 · drawer 40 · modal 50 · popover 60 · tooltip 70 · toast 80 |
| Motion | `--duration-fast` 120ms (hover, tooltip fade, focus) · `--duration-base` 200ms (menus, tabs) · `--duration-slow` 320ms (drawer) · `--ease-standard: cubic-bezier(0.2,0,0,1)`. Under `prefers-reduced-motion` all three become 0ms. No animated chart entrances, no count-up numbers, no graph physics running on screen |
| Layout | Top bar 56px · page max 1440px · gutter 24px · table rows 40/32px · controls 36/28px · card padding 20px (16px in dense grids) |

```css
.card   { background: var(--color-surface); border: var(--border-width) solid var(--color-border); border-radius: var(--radius-md); }
.menu   { background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: var(--radius-md); box-shadow: var(--shadow-overlay); z-index: var(--z-dropdown); }
.drawer { box-shadow: var(--shadow-overlay-lg); z-index: var(--z-drawer); transition: transform var(--duration-slow) var(--ease-standard); }
:focus-visible { outline: none; box-shadow: var(--focus-ring); }
```

---

## 6. Chart style guide

### 6.0 Chart library: Recharts 3
**The chart library is Recharts.** `recharts ^3.10.1` (3.10.1 installed) was added to `frontend/package.json` in commit `e20263c` (08 Oct 2026, 19:58 IST), together with `react-is`. The committed screens still use the original hand-rolled charts:

| Chart at HEAD | File | Target |
|---|---|---|
| "Hours by queue lane" | `src/three/QueueScene.tsx` (plain SVG despite the folder name) | Recharts horizontal `BarChart` (§6.3) |
| Ranking factor bars | `src/features/queue/FactorBars.tsx` | Full view: Recharts `BarChart`. Compact strip in table rows: stays CSS (§6.9) |
| Evidence strength meter | `src/components/EvidenceBar.tsx` | Stays a CSS meter (§6.9) |
| Peer range (IQR, median, provider) | `src/features/workspace/PeerCompare.tsx` | Inline: CSS (§6.9). Detail view: Recharts (§6.6) |
| Timeline, calibration, small multiples | not built at HEAD | Recharts `LineChart`/`AreaChart`/`ComposedChart` (§6.4–6.7) |

An **uncommitted work-in-progress** from another workstream (as of 20:10 IST) already rebuilds these on Recharts in `src/components/charts/`: `ChartFrame`, `ChartTooltip`, `LaneHoursChart`, `FactorContributionChart`, `PeerComparisonChart`, `ClaimsTimelineChart` and `RiskHorizonChart`. The snippets below are written against Recharts 3 and fit straight into those components (§11.2 maps the token names). **`chartTheme.ts`, `ChartTooltip`, the lane bar chart, the line chart and `CalibrationChart` type-check (strict) against the installed `recharts` 3.10.1** (`scripts/tscheck/`).

**Colour resolution.** Recharts writes colours into SVG presentation attributes (`fill="…"`, `stroke="…"`). `var(--x)` inside an attribute renders in Chromium, but that is not portable. Resolve tokens to concrete strings at runtime (the WIP's `lib/theme.ts` `token()` does the same) and re-resolve when `data-theme` changes. Everything below goes through `useChartTheme()`.

### 6.1 Shared helper: `src/lib/chartTheme.ts`
```ts
import { useSyncExternalStore } from "react";

const read = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export function resolveChartTheme() {
  return {
    series: [1, 2, 3, 4, 5, 6, 7, 8].map(i => read(`--chart-${i}`)),
    focus: read("--chart-focus"), comparison: read("--chart-comparison"), comparisonLine: read("--chart-comparison-line"),
    grid: read("--chart-grid"), axis: read("--chart-axis"), baseline: read("--chart-baseline"), label: read("--chart-label"),
    band: read("--chart-band"), reference: read("--chart-reference"), referenceDash: read("--chart-reference-dash"), // "4 4"
    areaOpacity: Number(read("--chart-area-opacity")), bandOpacity: Number(read("--chart-band-opacity")),
    risk: { low: read("--risk-low-solid"), medium: read("--risk-medium-solid"), high: read("--risk-high-solid"), critical: read("--risk-critical-solid") },
    harm: read("--harm-solid"), surface: read("--color-surface"), hover: read("--color-surface-hover"), text: read("--color-text"),
    font: read("--font-sans"),
  };
}
export type ChartTheme = ReturnType<typeof resolveChartTheme>;

let cached: ChartTheme | null = null;
function subscribe(onChange: () => void) {
  const mo = new MutationObserver(() => { cached = null; onChange(); });
  mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme", "class"] });
  return () => mo.disconnect();
}
export const useChartTheme = () => useSyncExternalStore(subscribe, () => (cached ??= resolveChartTheme()));

// ---- shared Recharts props (spread onto the components) ----
export const CHART = { tick: 4, fontSize: 12, lineWidth: 2, barCategoryGap: "35%", maxTicks: 5 } as const; // 35% gap = 65% bar
export const axisTick = (t: ChartTheme) => ({ fontSize: CHART.fontSize, fill: t.label, fontFamily: t.font });
export const categoryAxis = (t: ChartTheme) => ({
  tick: axisTick(t), tickSize: CHART.tick, tickMargin: 4, axisLine: { stroke: t.axis }, tickLine: { stroke: t.axis },
});
export const valueAxis = (t: ChartTheme) => ({
  tick: axisTick(t), tickCount: CHART.maxTicks, axisLine: false, tickLine: false, allowDecimals: false,
});
export const grid = (t: ChartTheme, direction: "h" | "v" = "h") => ({
  stroke: t.grid, horizontal: direction === "h", vertical: direction === "v", strokeDasharray: "",
});

// ---- numbers: compact on axes, exact in tables/tooltips ----
const compactUsd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 });
const compactNum = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
export const fmtAxisUsd = (v: number) => compactUsd.format(v);        // $1.2M, $850K, $0
export const fmtAxisNum = (v: number) => compactNum.format(v);        // 12K, 1.4M
export const fmtUsd = (v: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(v); // $1,240,310
export const fmtPct = (v: number, d = 0) => `${(v * 100).toFixed(d)}%`; // 0.426 → 43%
export const fmtDate = (d: Date | string) =>                           // 08 Oct 2026
  new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(d));
export const fmtDateIso = (d: Date | string) => new Date(d).toISOString().slice(0, 10); // 2026-10-08 (tables, exports)

// "Nice" max for shared domains (small multiples): niceTicks(max).at(-1)
export function niceTicks(max: number, count = 5): number[] {
  if (max <= 0) return [0];
  const raw = max / count, mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw)!;
  return Array.from({ length: Math.ceil(max / step) + 1 }, (_, i) => i * step);
}
```
Formatting rules:
- Currency: `$1,240,310` in tables, tooltips and KPI subtext; `$1.2M` on axes and KPI values.
- Percentages: integers by default (`43%`), with one decimal only when two values differ by less than 1pt.
- Probabilities: show as % with the word ("P(confirm) 43%").
- Dates: `08 Oct 2026` in UI text and ISO `2026-10-08` in tables, audit logs and exports. Times are `14:05 IST`, always with the zone.
- Use the minus sign `−` for negatives, and never rely on colour alone for sign (pair it with ▲/▼).
- Turn off animation on every series (`isAnimationActive={false}`) and on `<Tooltip>`. No animated entrances.

### 6.2 Axes, gridlines, ticks
- **Category axis** (x for columns, y for horizontal bars): 1px `--chart-axis` line with **outside** ticks of 4px and 12px `--chart-label` labels (`categoryAxis(t)`).
- **Value axis has no axis line.** Gridlines replace it (`valueAxis(t)` + `grid(t)`). They run horizontally, or vertically only for horizontal bar charts, as 1px solid `--chart-grid`, **never dashed**.
- **Zero baseline**: `<ReferenceLine y={0} stroke={t.baseline} />`, 1px and darker than the grid.
- At most about **5 ticks** (`tickCount={5}`), with compact labels (`tickFormatter={fmtAxisUsd}`). Add an axis title only when the chart title doesn't make the unit obvious. When used it is 12px muted, top-left and horizontal. Use `<Label>` with `position="insideTopLeft"` and never `angle={-90}`.
- Charts sit on `--color-surface` with no plot background, no border inside a card, no 3D and no shadow.
- **Dashed lines are for reference lines only** (calibration y = x, capacity or target), using `t.reference` and `t.referenceDash`. Data series are never dashed.

```tsx
<CartesianGrid {...grid(t)} />
<XAxis dataKey="label" {...categoryAxis(t)} />
<YAxis {...valueAxis(t)} tickFormatter={fmtAxisUsd} width={52} />
<ReferenceLine y={0} stroke={t.baseline} />
```
```css
/* src/styles/charts.css: Recharts chrome */
.chart .recharts-wrapper { font-family: var(--font-sans); }
.chart :is(.recharts-text, .recharts-label, .recharts-label-list text) {
  font-variant-numeric: tabular-nums lining-nums; font-feature-settings: var(--font-features-data); }
.chart :is(.recharts-cartesian-grid line, .recharts-cartesian-axis-line, .recharts-cartesian-axis-tick-line, .recharts-reference-line line) {
  shape-rendering: crispEdges; }
.chart .recharts-surface:focus { outline: none; }                       /* mouse focus */
.chart .recharts-wrapper:has(.recharts-surface:focus-visible) {          /* keyboard focus (accessibilityLayer) */
  outline: var(--focus-ring-width) solid var(--color-focus); outline-offset: 2px; border-radius: var(--radius-sm); }
.chart .recharts-tooltip-wrapper { z-index: var(--z-tooltip); }
.cs-title    { font: var(--type-h4); color: var(--color-text); margin: 0; }
.cs-subtitle { font: var(--type-body-sm); color: var(--color-text-muted); margin: 2px 0 var(--space-3); }
```

### 6.3 Bars
- Square bars: radius 0, or 2px on the **value end only**. Use `radius={[2, 2, 0, 0]}` for columns and `[0, 2, 2, 0]` for horizontal bars. Bar thickness is **65%** of the band (`barCategoryGap="35%"`).
- **Sort by value** (descending) unless the categories are ordinal (lanes, months, risk levels).
- With **12 bars or fewer**, put direct value labels at the bar end (`<LabelList position="right|top">`, 12px, `t.text`) and drop the value gridlines when every bar is labelled. With more than 12 bars, use gridlines and a tooltip.
- One colour per measure. **Highlight one, gray the rest**: the focus bar uses `t.focus` and the others `t.comparison`, set per `<Cell>`. Use risk or harm colours only when the bar encodes them.
- No track or "remaining" background bars (`background` prop off), except in CSS meters (§6.9).

**Hours by queue lane** (`QueueScene.tsx` → `LaneHoursChart`). Lanes are ordinal, so they are not sorted. The harm lane uses the harm colour plus ✚ in its label, "Selected" is the focus series and the rest are gray. Capacity is a reference line.
```tsx
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { categoryAxis, grid, useChartTheme, valueAxis, type ChartTheme } from "../../lib/chartTheme";
import { ChartTooltip } from "./ChartTooltip";

const LANES = [
  { lane: "harm_priority",  label: "✚ Harm priority", color: (t: ChartTheme) => t.harm },
  { lane: "selected",       label: "Selected today",  color: (t: ChartTheme) => t.focus },
  { lane: "needs_evidence", label: "Needs evidence",  color: (t: ChartTheme) => t.comparison },
  { lane: "overflow",       label: "Tracked backlog", color: (t: ChartTheme) => t.comparison },
] as const;

const t = useChartTheme();
<ResponsiveContainer width="100%" height={LANES.length * 40 + 32}>
  <BarChart data={data} layout="vertical" barCategoryGap="35%" margin={{ top: 16, right: 56, bottom: 0, left: 0 }}>
    <CartesianGrid {...grid(t, "v")} />
    <XAxis type="number" {...valueAxis(t)} tickFormatter={hours} />
    <YAxis type="category" dataKey="label" {...categoryAxis(t)} width={132} />
    <ReferenceLine x={0} stroke={t.baseline} />
    <ReferenceLine x={capacityHours} stroke={t.reference} strokeDasharray={t.referenceDash}
      label={{ value: `Capacity ${hours(capacityHours)}`, position: "top", fill: t.label, fontSize: 12 }} />
    <Tooltip content={<ChartTooltip fmt={hours} />} cursor={{ fill: t.hover }} isAnimationActive={false} />
    <Bar dataKey="hours" radius={[0, 2, 2, 0]} isAnimationActive={false} onClick={(_, i) => onSelect(data[i].lane)}>
      {data.map((d, i) => (
        <Cell key={d.lane} cursor="pointer" fill={LANES[i].color(t)}
              fillOpacity={selected === "all" || selected === d.lane ? 1 : 0.35} />
      ))}
      <LabelList dataKey="hours" position="right" formatter={(v) => hours(Number(v))} fill={t.text} fontSize={12} fontWeight={500} />
    </Bar>
  </BarChart>
</ResponsiveContainer>
```
Factor contributions use the same pattern with `layout="vertical"`, sorted descending, and every bar in `t.comparison` except the composite or selected factor in `t.focus`. A factor that lowers the score extends left of the zero `ReferenceLine` and its label carries "−".

### 6.4 Lines
- 2px stroke with `strokeLinejoin="round"` and `type="linear"`, never `monotone`, so the chart doesn't invent smoothness. No markers, **except** a 4px dot on the last point and a 5px active dot with a 2px surface ring.
- **End labels instead of a legend**: the series name and last value sit at the right end, 12px, in the series colour, or in `t.text` when that colour is below 4.5:1. Keep labels at least 14px apart vertically.
- Peer or comparison lines use `t.comparisonLine` at 1.5px. The focus line uses `t.focus`.
```tsx
// helpers (props typed loosely; Recharts passes x/y/value/index to LabelList content and cx/cy/index to dot)
const endLabel = (n: number, name: string, fill: string) =>
  (p: { x?: number | string; y?: number | string; value?: unknown; index?: number }) =>
    p.index === n - 1
      ? <text x={Number(p.x) + 8} y={Number(p.y)} dy="0.32em" fill={fill} fontSize={12} fontWeight={500}>{name} · {fmtAxisUsd(Number(p.value))}</text>
      : null;
const lastDot = (n: number, fill: string) => (p: { cx?: number; cy?: number; index?: number }) =>
  p.index === n - 1 ? <circle key="last" cx={p.cx} cy={p.cy} r={4} fill={fill} /> : <g key={p.index} />;

<ResponsiveContainer width="100%" height={240}>
  <LineChart data={rows} margin={{ top: 8, right: 132, bottom: 0, left: 0 }}>
    <CartesianGrid {...grid(t)} />
    <XAxis dataKey="month" {...categoryAxis(t)} interval="preserveStartEnd" minTickGap={24} />
    <YAxis {...valueAxis(t)} tickFormatter={fmtAxisUsd} width={52} />
    <Tooltip content={<ChartTooltip fmt={fmtUsd} />} cursor={{ stroke: t.axis, strokeWidth: 1 }} isAnimationActive={false} />
    <Line dataKey="peerMedian" name="Peer median" type="linear" stroke={t.comparisonLine} strokeWidth={1.5}
          dot={false} activeDot={false} isAnimationActive={false}>
      <LabelList dataKey="peerMedian" content={endLabel(rows.length, "Peer median", t.label)} />
    </Line>
    <Line dataKey="billed" name="This provider" type="linear" stroke={t.focus} strokeWidth={2} strokeLinejoin="round"
          dot={lastDot(rows.length, t.focus)} activeDot={{ r: 5, fill: t.focus, stroke: t.surface, strokeWidth: 2 }}
          isAnimationActive={false}>
      <LabelList dataKey="billed" content={endLabel(rows.length, "This provider", t.text)} />
    </Line>
  </LineChart>
</ResponsiveContainer>
```

### 6.5 Areas
- Fill opacity of **12–16%** (`t.areaOpacity` = 0.14) under a 2px line in the same colour.
- **Stack only when the parts add up to a meaningful total**, for example flagged $ by detector type summing to total flagged $. Otherwise overlay lines.
- A stacked area has at most 4 layers, ordered by size with the largest first (Recharts draws the first `<Area>` at the bottom), and uses end labels.
```tsx
<AreaChart data={rows} margin={{ top: 8, right: 132, bottom: 0, left: 0 }}>
  <CartesianGrid {...grid(t)} />
  <XAxis dataKey="month" {...categoryAxis(t)} />
  <YAxis {...valueAxis(t)} tickFormatter={fmtAxisUsd} width={52} />
  {DETECTORS.map((d, i) => (
    <Area key={d.key} dataKey={d.key} name={d.label} stackId="flagged" type="linear"
          stroke={t.series[i]} strokeWidth={2} fill={t.series[i]} fillOpacity={t.areaOpacity}
          dot={false} activeDot={{ r: 5, stroke: t.surface, strokeWidth: 2 }} isAnimationActive={false} />
  ))}
  <Tooltip content={<ChartTooltip fmt={fmtUsd} />} isAnimationActive={false} />
</AreaChart>
```

### 6.6 Small multiples
- Panels share **one y-scale by default** (`domain={[0, yMax]}` on every `YAxis`). If panels use independent scales, say so in the caption: "Each panel has its own scale."
- Lay them out on a CSS grid of 2–4 columns with a 13px `--type-label` title per panel. Keep axes minimal: y ticks on the first column only and x ticks on the bottom row only, with gridlines kept. `syncId` keeps the tooltips in step.
- Switch to small multiples whenever there would otherwise be more than 5 series.
```tsx
const yMax = niceTicks(Math.max(...panels.flatMap(p => p.rows.map(r => r.v)))).at(-1)!;
<div className="cs-multiples">
  {panels.map((p, i) => (
    <figure key={p.id} className="cs-panel">
      <h4>{p.title}</h4>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={p.rows} syncId="peer-multiples" margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid {...grid(t)} />
          <XAxis dataKey="month" {...categoryAxis(t)} hide={!isBottomRow(i)} />
          <YAxis {...valueAxis(t)} domain={[0, yMax]} tickFormatter={fmtAxisNum}
                 width={isFirstCol(i) ? 40 : 4} tick={isFirstCol(i) ? axisTick(t) : false} />
          <Line dataKey="v" type="linear" stroke={p.isSubject ? t.focus : t.comparisonLine}
                strokeWidth={p.isSubject ? 2 : 1.5} dot={false} isAnimationActive={false} />
          <Tooltip content={<ChartTooltip fmt={fmtAxisNum} />} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </figure>
  ))}
</div>
```
```css
.cs-multiples { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-4) var(--space-5); }
@media (min-width: 1200px) { .cs-multiples { grid-template-columns: repeat(4, 1fr); } }
.cs-panel { margin: 0; }
.cs-panel h4 { font: var(--type-label); color: var(--color-text); margin: 0 0 var(--space-1); }
.cs-multiples-caption { font: var(--type-caption); color: var(--color-text-subtle); margin-top: var(--space-2); }
```

### 6.7 Calibration chart (new, for P(confirm))
This chart shows whether "43% likely to confirm" really confirms about 43% of the time, so investigators can trust the ranking.
- **Square** (`aspect={1}`), with both axes running 0–1 as **percentages** (0%, 25%, 50%, 75%, 100%). This is the one chart that gets gridlines in both directions, because the eye reads distance from the diagonal.
- **y = x reference**: a dashed neutral `ReferenceLine` segment (`t.reference`, dash `4 4`).
- **Model curve**: `t.series[0]` (`--chart-1`, brand-derived green, which is fine for a single series), 2px, with **points sized by bin count** (`<ZAxis range>` maps n to area).
- **Confidence band** (Wilson 95% per bin): a ranged `<Area>` (`dataKey` → `[lo, hi]`) in `--chart-1` at **15%** opacity with no outline.
- Underneath, a 48px **histogram strip** of predicted probabilities in `t.comparison`, with no y-axis and synced through `syncId`.
- Footer caption: "Brier 0.142 · ECE 3.1% · n = 4,812 closed cases · 10 equal-width bins".
```tsx
// src/components/charts/CalibrationChart.tsx
import { Area, Bar, BarChart, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { axisTick, categoryAxis, fmtPct, useChartTheme, valueAxis } from "../../lib/chartTheme";

type Bin = { p: number; observed: number; lo: number; hi: number; n: number };
const PCT = [0, 0.25, 0.5, 0.75, 1];

export function CalibrationChart({ bins, caption }: { bins: Bin[]; caption: string }) {
  const t = useChartTheme();
  const data = bins.map(b => ({ ...b, band: [b.lo, b.hi] as [number, number] }));
  return (
    <figure className="chart cs-calibration">
      <ResponsiveContainer width="100%" aspect={1} maxHeight={320}>
        <ComposedChart data={data} syncId="calibration" margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
                       accessibilityLayer title="Calibration: predicted vs observed confirmation rate">
          <CartesianGrid stroke={t.grid} strokeDasharray="" />
          <XAxis type="number" dataKey="p" domain={[0, 1]} ticks={PCT} tickFormatter={v => fmtPct(v)} {...categoryAxis(t)} />
          <YAxis type="number" domain={[0, 1]} ticks={PCT} tickFormatter={v => fmtPct(v)} {...valueAxis(t)} width={40} />
          <ZAxis dataKey="n" range={[28, 200]} />
          <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke={t.reference} strokeDasharray={t.referenceDash} ifOverflow="hidden" />
          <Area dataKey="band" type="linear" stroke="none" fill={t.series[0]} fillOpacity={t.bandOpacity} activeDot={false} isAnimationActive={false} />
          <Line dataKey="observed" type="linear" stroke={t.series[0]} strokeWidth={2} dot={false} activeDot={false} isAnimationActive={false} />
          <Scatter dataKey="observed" fill={t.series[0]} stroke={t.surface} strokeWidth={1.5} isAnimationActive={false} />
          <Tooltip content={<CalibrationTooltip />} cursor={{ stroke: t.axis }} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
      <ResponsiveContainer width="100%" height={48}>
        <BarChart data={data} syncId="calibration" barCategoryGap="35%" margin={{ top: 4, right: 8, bottom: 0, left: 40 }}>
          <XAxis dataKey="p" hide /><YAxis hide />
          <Bar dataKey="n" name="Cases" fill={t.comparison} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
      <figcaption className="cs-multiples-caption">Predicted P(confirm) → · ↑ Observed confirmed · {caption}</figcaption>
    </figure>
  );
}
// CalibrationTooltip: "Bin 40–50% · predicted 45% · observed 43% (95% CI 38–48%) · n = 512"
```

### 6.8 Legends and tooltips
- **Legend**: render it as HTML above the plot (`.cs-legend`), top-left, inline, 12px. Bars and areas get 8×8px **square** swatches, lines get 12×2px **line segments**, and risk uses the ring glyph. **No legend for a single series.** Prefer end labels or direct labels. If Recharts' `<Legend>` is used, give it `content={<ChartLegend />}`, `verticalAlign="top"` and `align="left"` so it renders the same markup.
- **Tooltip**: `<Tooltip content={<ChartTooltip fmt={…} />} isAnimationActive={false} />`, which disables Recharts' sliding animation. The card uses `--color-surface-raised`, a 1px `--color-border`, `--shadow-overlay`, radius 6 and 12–13px text. It has a title row (category or date) and then aligned rows of swatch · name · **right-aligned tabular value**. The only motion is a **120ms opacity fade-in**.
```tsx
// src/components/charts/ChartTooltip.tsx
import { Fragment } from "react";
import type { TooltipContentProps } from "recharts";

type Props = Partial<TooltipContentProps<number, string>> & { fmt?: (v: number) => string; title?: (label: unknown) => string };
export function ChartTooltip({ active, payload, label, fmt = String, title = String }: Props) {
  if (!active || !payload?.length) return null;
  return (
    <div className="cs-tooltip">
      <h5>{title(label)}</h5>
      <dl>
        {payload.map(p => (
          <Fragment key={String(p.dataKey)}>
            <i style={{ background: p.color }} aria-hidden="true" /><dt>{p.name}</dt><dd>{fmt(Number(p.value))}</dd>
          </Fragment>
        ))}
      </dl>
    </div>
  );
}
```
```css
.cs-legend { display: flex; flex-wrap: wrap; gap: var(--space-1) var(--space-4); font: var(--type-caption); color: var(--color-text-muted); margin: 0 0 var(--space-2); padding: 0; list-style: none; }
.cs-legend i { display: inline-block; width: 8px; height: 8px; margin-right: 6px; vertical-align: 0; }
.cs-legend i.line { width: 12px; height: 2px; vertical-align: 3px; }
.cs-tooltip { min-width: 160px; pointer-events: none;
  background: var(--color-surface-raised); border: 1px solid var(--color-border); border-radius: var(--radius-md);
  box-shadow: var(--shadow-overlay); padding: var(--space-2) var(--space-3); font: var(--type-caption); color: var(--color-text);
  animation: cs-fade var(--duration-fast) var(--ease-standard); }
@keyframes cs-fade { from { opacity: 0 } to { opacity: 1 } }
.cs-tooltip h5 { font: var(--type-label); margin: 0 0 var(--space-1); }
.cs-tooltip dl { display: grid; grid-template-columns: 8px 1fr auto; gap: 2px var(--space-2); margin: 0; align-items: center; }
.cs-tooltip i { width: 8px; height: 8px; }
.cs-tooltip dt { color: var(--color-text-muted); }
.cs-tooltip dd { margin: 0; text-align: right; font-variant-numeric: tabular-nums; font-weight: var(--font-weight-medium); }
@media (prefers-reduced-motion: reduce) { .cs-tooltip { animation: none; } }
```

### 6.9 Meters and micro-charts already in the app
```css
/* EvidenceBar + FactorBars: one neutral measure, not brand green */
.evidence-track, .factor-track { height: 6px; background: var(--color-surface-sunken); border-radius: var(--radius-xs); }
.evidence-fill, .factor-track i { background: var(--neutral-700); border-radius: var(--radius-xs); }
.factor-composite .factor-track i { background: var(--chart-focus); }      /* the combined score is the focus */
.factor-bars li { font: var(--type-caption); color: var(--color-text-muted); }
.factor-bars .mono, .evidence .mono { font-variant-numeric: tabular-nums; color: var(--color-text); }
/* PeerRange: IQR band, median tick, provider dot (focus) */
.peer-range  { position: relative; height: 20px; border-bottom: 1px solid var(--chart-axis); }
.peer-iqr    { position: absolute; top: 6px; height: 8px; background: var(--chart-band); }
.peer-median { position: absolute; top: 3px; width: 2px; height: 14px; background: var(--chart-baseline); }
.peer-dot    { position: absolute; top: 5px; width: 10px; height: 10px; margin-left: -5px; border-radius: 50%;
               background: var(--chart-focus); box-shadow: 0 0 0 2px var(--color-surface); }
.peer-compare.is-limited .peer-iqr { background: transparent; box-shadow: inset 0 0 0 1px var(--chart-axis); } /* hollow band = limited peers */
```
`is-limited` changes the **shape** (a hollow band), not the colour, and it always comes with the text "Limited peer group (n = 7)".

### 6.10 Chart states
- **Loading**: a skeleton with the chart's real footprint. Three or four gray bars or a flat line in `--color-surface-sunken`, plus a 1.2s opacity pulse (0.6↔1) that is disabled under reduced motion. Never use a spinner inside a chart.
- **Empty**: keep the axes frame and centre a 13px muted message saying why and what to do: "No closed cases in this run yet. Calibration appears after 30 decisions."
- **Error**: an inline `--color-danger-fg` message with ⚠, the error id in mono, and a ghost "Retry" button. The card chrome stays.
- **Limited data**: show the data with a caption ("n = 7, wide intervals").
```css
.cs-skeleton { fill: var(--color-surface-sunken); background: var(--color-surface-sunken); animation: cs-pulse 1.2s var(--ease-standard) infinite alternate; }
@keyframes cs-pulse { from { opacity: .6 } to { opacity: 1 } }
@media (prefers-reduced-motion: reduce) { .cs-skeleton { animation: none; } }
.cs-empty, .cs-error { display: grid; place-items: center; min-height: 160px; font: var(--type-body-sm); color: var(--color-text-muted); text-align: center; }
.cs-error { color: var(--color-danger-fg); }
```


---

## 7. Provider network graph

### 7.0 Graph library: Cytoscape.js + fcose
**The graph library is Cytoscape.js.** `cytoscape ^3.34.3` and `cytoscape-fcose ^2.2.0` (3.34.3 and 2.2.0 installed) were added in commit `e20263c` (08 Oct 2026, 19:58 IST). 3.34 supports every style property used below, including `outline-*`, `background-image-containment` and `bounds-expansion`. I checked these against `node_modules/cytoscape/dist`. **The §7.7 stylesheet was also type-checked against `cytoscape` 3.34.3 typings and rendered in headless Chrome with zero console warnings** (`brand-evidence/graph_preview_*.png`, harness in `scripts/tscheck/`).
- **At HEAD** the graph is still the old **custom React SVG** (`src/three/NetworkGraph.tsx`, which doesn't use three.js), hosted by `features/workspace/NetworkPanel.tsx`. It has a hand-rolled radial layout and loud `TYPE_COLOR` hues: provider `#1aa24c`, member `#c49a3c`, facility `#3d7ea6`, owner `#b94832`.
- **Uncommitted WIP** from another workstream (as of 20:10 IST) replaces it with `src/components/network/{CaseNetworkGraph.tsx, graphStyles.ts, networkModel.ts, LinkTypeLegend.tsx, LinkedEntityList.tsx}`, using Cytoscape plus fcose with "force" and "rings" layouts. §7.7 is written to drop into `graphStyles.ts`. §11.2 lists where the WIP's current colours and dashes diverge from this spec.
- The SVG-renderer stylesheet is kept as appendix §7.9, for use only if the Cytoscape swap is abandoned.

Data from `backend/.../cases/workspace.py::network_pack` (2 hops):
- **Node types today:** `provider` (with `primary` for the case subject, and `risk` = case p_confirm on the subject only), `member` (masked), `facility` and `owner`.
- **Edge kinds today:** `rendered`, `billed`, `at_facility`, `owns`, `referral`, `shared_location`, `shared_tin`, `shared_owner` and `shared_contact`.
- Address, phone and bank/TIN are **edges** today (`shared_location`, `shared_contact`, `shared_tin`), not nodes. The spec also styles them as nodes, ready for when the API promotes them. An identity-ring view reads better when the shared address is a visible hub.

### 7.1 Node types: shape + glyph + quiet tint, never six loud hues

| Type | In data today | Shape | Size (px) | Fill | 1.5px stroke | Glyph (12px, lucide name; optional, see below) |
|---|---|---|---|---|---|---|
| **Case subject** | `provider` with `primary: true` | Circle | **44** ⌀ | `--graph-subject-fill` `#1c873e` | none | `stethoscope`, **white** (4.58:1) at 16px |
| Provider | yes | Circle | 28 ⌀ | `--graph-node-provider-fill` `#e8efef` | `#495b5b` | `stethoscope` |
| Owner | yes | Rounded square (r 4) | 24 | `--graph-node-owner-fill` `#f2ece4` (Acentra sand) | `#71604a` | `user-round` |
| Facility | yes | Rounded rect 30×22 (r 2) | 30×22 | `--graph-node-facility-fill` `#e4f3f2` (Acentra pale teal) | `#11615b` (Acentra teal) | `building-2` |
| Address | future (`shared_location`) | Diamond | 24 | `#f8fbfb` | `#5d6e6f` | `map-pin` |
| Phone / contact | future (`shared_contact`) | Small circle | 14 ⌀ | `#f8fbfb` | `#5d6e6f` | none (too small); `phone` in panel |
| Bank / TIN | future (`shared_tin`) | Hexagon | 24 | `#e8efef` | `#2f4445` | `landmark` |
| Member | yes (masked) | Small triangle | 16 | `#ffffff` | `#748484` | none; aggregate "N members" node = 28px triangle with the count |

Every stroke is ≥ 3:1 against both its own fill and the canvas (computed in §3).

Cytoscape `shape` per type: subject, provider and phone use `ellipse`; owner uses `round-rectangle` (24×24); facility uses `round-rectangle` (30×22); address uses `diamond`; bank uses `hexagon`; member uses `triangle`.

**Glyphs are optional.** Shape alone separates the types. The repo has no icon package; `lucide-react` is not in `package.json`. To show glyphs, add `lucide-static` (ISC licence) and pass each icon's SVG string, with `currentColor` replaced by `--graph-node-glyph` (or `--graph-subject-glyph` on the subject), as a data-URI `background-image` (§7.7). Without it, `icon` falls back to a transparent placeholder.

### 7.2 Edge types

| Kind | Meaning | Stroke | Arrow | Width |
|---|---|---|---|---|
| `billed`, `rendered`, `at_facility` | Claim relationships | `--graph-edge-claim` `#bbc7c7`, solid | no | 1px + count |
| `shared_location` | Shared address | `--graph-edge-shared` `#748484`, solid | no | 1.5px |
| `shared_tin` | Shared tax ID / bank | `--graph-edge-shared`, solid | no | 1.5px |
| `shared_contact` | Shared phone/email | `--graph-edge-shared`, solid | no | 1.5px |
| `owns` | Ownership | `--graph-edge-ownership` `#2f4445`, solid | **yes** (owner → provider) | 2px |
| `shared_owner` | Same owner | `--graph-edge-ownership`, solid | no | 2px |
| `referral` | Referral | `--graph-edge-referral` `#005f68` (Acentra deep teal), solid | **yes** (referrer → receiver) | 1.5px + count |
| inferred / weak | Not in data today | Same colour as its kind, **dashed `4 3`** (the only graph dash) | per kind | 1px |

- **Width encodes count** after aggregation: `w = 1 + 2 * min(1, (count - 1) / 4)`, clamped to 1–3px.
- Edge labels appear **on hover only**: "Referral · 14 claims", 12px, on a surface halo.

### 7.3 Risk ring, harm notch, subject, selection
- **Risk ring** = Cytoscape `outline`: 2.5px wide, offset 2px outside the border, in `--risk-{level}-solid`. Low is slate, medium amber, high orange, critical red. Nodes without a risk value get no ring. The level glyph and label (`● High risk`) appear in the side panel and the hover label, so the ring is never the only cue.
- **Patient harm**: a 9px plum dot (`--harm-solid`) with a 1.5px canvas-coloured outline at the node's top-right (1–2 o'clock), drawn as a second `background-image` layer with `background-image-containment: over`, `background-clip: none` and `bounds-expansion` so it isn't clipped. The side panel shows "✚ Harm 4". The API needs a per-node `harm` field; until then, apply it to the subject when `case.harm ≥ 3`.
- **Case subject**: the largest node (44px), with a green-700 fill, white glyph, a **3px** outline in its risk colour (or `--graph-subject-ring-fallback` `#2bbc2b` when it has no risk), and a **label that is always visible** at 12px semibold.
- **Selected**: Cytoscape gives each node one outline, so on selection the outline becomes the **2px focus ring** (`--color-focus`, offset 2px, which leaves a canvas gap) and the risk colour **moves into the 2.5px border** for as long as the node is selected. Risk stays visible and focus stays unambiguous. The details open in the side panel. The canvas is not keyboard-reachable, so **`LinkedEntityList` is the keyboard path**: Tab or arrow keys move through the list, Enter selects (synced to `cy.$id(id).select()`), and Esc clears.

### 7.4 2-hop highlight
On hover or selection, take the active node's 2-hop neighbourhood over **enabled** edges:
- depth 0–2 nodes and the edges between them stay at full opacity;
- **1-hop edges get +0.75px** of width (`.hop1`);
- 1-hop nodes get their labels (`.labelled`);
- everything else dims to **15%** opacity (`--graph-dim-opacity`, `.dimmed`). Nothing is hidden;
- opacity transitions at `--duration-fast`, which becomes 0 under reduced motion. Positions never animate.

Edge-kind filters should `remove()` and `restore()` the filtered edges, not just hide them, so the neighbourhood maths sees enabled edges only.
```ts
export function focusHood(cy: cytoscape.Core, id: string | null) {
  cy.batch(() => {
    cy.elements().removeClass("dimmed hop1 labelled");
    if (!id) return;
    const node = cy.$id(id);
    const hop1 = node.closedNeighborhood();            // node + 1-hop nodes + connecting edges
    const hop2 = hop1.closedNeighborhood();            // within 2 hops
    cy.elements().not(hop2).addClass("dimmed");
    node.connectedEdges().addClass("hop1");
    hop1.nodes().addClass("labelled");
  });
}
cy.on("mouseover", "node", e => focusHood(cy, e.target.id()));
cy.on("mouseout",  "node", () => focusHood(cy, cy.$("node:selected").first().id() || null));
cy.on("select",    "node", e => focusHood(cy, e.target.id()));
cy.on("unselect",  "node", () => focusHood(cy, null));
cy.on("mouseover", "edge", e => e.target.addClass("hovered"));
cy.on("mouseout",  "edge", e => e.target.removeClass("hovered"));
```

### 7.5 Labels
- 11px Inter 500 in `--color-text`, with a 3px `--graph-label-halo` text outline so labels stay readable over edges. Labels sit below the node; the subject's label is 12px semibold.
- Show labels for **the subject (always), hovered and selected nodes, and 1-hop neighbours of the active node** (`.labelled`). Every other label is hidden. If the graph has 12 nodes or fewer, add `.labelled` to all nodes. `min-zoomed-font-size: 8` drops labels automatically when zoomed out.
- Truncate the label to 22 characters with "…" in the element data (`short`). The full text goes in the side panel and hover tooltip. Masked members show only their masked display.

### 7.6 Layout and canvas
- Canvas: the container background is `--graph-bg` (surface white), with **no grid, no dot pattern and no inner rounded rect**. The card provides the 1px border. Height is `min(560px, 70vh)`.
- **Default layout "Organic"**: first a deterministic `concentric` seed by hop from the subject (subject centred, hop 1 inside, hop 2 outside, sorted by type within each ring: owner, facility, providers, contact hubs, members). Then **fcose** refines it with `randomize: false` and `animate: false`, so there are **no live physics on screen** and no random first frame. I rendered the same input twice in headless Chrome and got byte-identical output; see `brand-evidence/graph_preview_organic.png`.
- **Alternative "Rings"**: the concentric seed on its own. It shows hop distance literally, but edges cross more (`graph_preview_rings.png`), so offer it as a toggle, not the default.
- Members collapse to one "N members" node when there are more than 8 (existing behaviour, kept).
- Zoom and pan are allowed (`minZoom 0.4`, `maxZoom 2.5`). Add zoom buttons and "Fit" as ghost icon buttons top-right. Box selection is off.
```ts
import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";
cytoscape.use(fcose);

await document.fonts.load('500 11px "Inter Variable"');          // canvas text needs the font loaded first
const cy = cytoscape({
  container, elements, style: cyStyle(),
  layout: { name: "preset" }, minZoom: 0.4, maxZoom: 2.5,
  boxSelectionEnabled: false, selectionType: "single", autoungrabify: false,
});
const hop = hopDistances(subjectId);                               // BFS depth from the subject (WIP: networkModel.hopDistances)
const TYPE_ORDER = ["owner", "facility", "provider", "address", "phone", "bank", "member"];
cy.layout({
  name: "concentric", animate: false, avoidOverlap: true, minNodeSpacing: 40, startAngle: (3 / 2) * Math.PI,
  concentric: n => 3 - Math.min(hop.get(n.id()) ?? 2, 2),          // subject 3, hop-1 2, hop-2 1
  levelWidth: () => 1,
  sort: (a, b) => TYPE_ORDER.indexOf(a.data("type")) - TYPE_ORDER.indexOf(b.data("type")),
}).run();
if (mode === "organic") cy.layout({
  name: "fcose", quality: "proof", randomize: false, animate: false, nodeDimensionsIncludeLabels: true,
  nodeRepulsion: 20000, nodeSeparation: 60, numIter: 2500,
  idealEdgeLength: (e: cytoscape.EdgeSingular) => (String(e.data("kind")).startsWith("shared") ? 90 : 120),
  fixedNodeConstraint: [{ nodeId: subjectId, position: { x: 0, y: 0 } }],
} as cytoscape.LayoutOptions).run();
cy.fit(undefined, 32);
cy.$id(subjectId).addClass("subject");
```

### 7.7 Full Cytoscape stylesheet (`src/components/network/graphStyles.ts`)
Element data contract:
- **nodes:** `{ id, type, short, label, primary?, risk?: "low"|"medium"|"high"|"critical", harm?: boolean, icon?: dataUri, count? }`
- **edges:** `{ id, source, target, kind, count = 1, inferred?, hoverLabel }`, for example "Referral · 14 claims".
```ts
import type cytoscape from "cytoscape";

const v = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim(); // canvas needs concrete colours
const uri = (svg: string) => `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
const EMPTY = uri('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>');
const RISK = ["low", "medium", "high", "critical"] as const;
// claim + referral edges scale with count (1–3px); shared 1.5px; ownership 2px; inferred 1px
const edgeWidth = (e: cytoscape.EdgeSingular) => {
  const kind = String(e.data("kind"));
  if (e.data("inferred")) return 1;
  if (kind === "owns" || kind === "shared_owner") return 2;
  if (kind.startsWith("shared_")) return 1.5;
  return 1 + 2 * Math.min(1, Math.max(0, (Number(e.data("count") ?? 1) - 1) / 4));
};

export function cyStyle(): cytoscape.StylesheetJson {
  const harmDot = uri(`<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12"><circle cx="6" cy="6" r="4.5" fill="${v("--harm-solid")}" stroke="${v("--graph-bg")}" stroke-width="1.5"/></svg>`);
  const fade = v("--duration-fast");                                   // "120ms", or "0ms" under prefers-reduced-motion
  const node = (type: string, shape: string, w: number, h = w) => ({
    selector: `node[type = "${type}"]`,
    style: { shape, width: w, height: h, "background-color": v(`--graph-node-${type}-fill`), "border-color": v(`--graph-node-${type}-stroke`) },
  });
  return [
    { selector: "core", style: { "active-bg-opacity": 0, "selection-box-opacity": 0 } },

    /* ---- nodes: base ---- */
    { selector: "node", style: {
        shape: "ellipse", width: 28, height: 28,
        "background-color": v("--graph-node-provider-fill"), "border-color": v("--graph-node-provider-stroke"),
        "border-width": Number.parseFloat(v("--graph-node-stroke-width")) || 1.5,
        // layer 0 = type glyph, layer 1 = harm notch (always two layers so the array props line up)
        "background-image": (n: cytoscape.NodeSingular) => [n.data("icon") ?? EMPTY, n.data("harm") ? harmDot : EMPTY],
        "background-width": ["50%", "12px"], "background-height": ["50%", "12px"],
        "background-position-x": ["50%", "100%"], "background-position-y": ["50%", "0%"],
        "background-clip": ["node", "none"], "background-image-containment": ["inside", "over"],
        "bounds-expansion": 8,
        label: "", color: v("--color-text"), "font-family": v("--font-sans"), "font-size": 11, "font-weight": 500,
        "text-valign": "bottom", "text-margin-y": 6, "text-outline-color": v("--graph-label-halo"), "text-outline-width": 3,
        "min-zoomed-font-size": 8, "overlay-opacity": 0,
        "transition-property": "opacity", "transition-duration": fade,
    } },
    node("provider", "ellipse", 28),
    node("owner", "round-rectangle", 24),
    node("facility", "round-rectangle", 30, 22),
    node("address", "diamond", 24),
    node("phone", "ellipse", 14),
    node("bank", "hexagon", 24),
    node("member", "triangle", 16),
    { selector: "node:active, node.hovered", style: { "border-width": 2 } },

    /* ---- risk ring = outline (2px gap, 2.5px ring) ---- */
    ...RISK.map(level => ({ selector: `node[risk = "${level}"]`,
        style: { "outline-width": 2.5, "outline-offset": 2, "outline-color": v(`--risk-${level}-solid`) } })),

    /* ---- case subject ---- */
    { selector: "node.subject, node[?primary]", style: {
        width: 44, height: 44, "background-color": v("--graph-subject-fill"), "border-width": 0,
        "outline-width": 3, "outline-offset": 2, "outline-color": v("--graph-subject-ring-fallback"),
        label: "data(short)", "font-size": 12, "font-weight": 600,
    } },
    ...RISK.map(level => ({ selector: `node.subject[risk = "${level}"], node[?primary][risk = "${level}"]`,
        style: { "outline-color": v(`--risk-${level}-solid`) } })),

    /* ---- labels ---- */
    { selector: "node.labelled, node.hovered, node:selected", style: { label: "data(short)" } },

    /* ---- selection: outline becomes the focus ring; risk moves into the border ---- */
    { selector: "node:selected", style: { "outline-width": 2, "outline-offset": 2, "outline-color": v("--color-focus") } },
    ...RISK.map(level => ({ selector: `node[risk = "${level}"]:selected`,
        style: { "border-width": 2.5, "border-color": v(`--risk-${level}-solid`) } })),

    /* ---- edges ---- */
    { selector: "edge", style: {
        width: edgeWidth, "line-color": v("--graph-edge-claim"), "curve-style": "bezier", "line-cap": "round",
        "target-arrow-shape": "none", "arrow-scale": 0.8, "overlay-opacity": 0,
        label: "", "font-family": v("--font-sans"), "font-size": 11, color: v("--color-text-muted"),
        "text-background-color": v("--graph-label-halo"), "text-background-opacity": 1, "text-background-padding": "2px",
        "text-rotation": "autorotate", "min-zoomed-font-size": 8,
        "transition-property": "opacity", "transition-duration": fade,
    } },
    { selector: 'edge[kind = "shared_location"], edge[kind = "shared_tin"], edge[kind = "shared_contact"]',
      style: { "line-color": v("--graph-edge-shared") } },
    { selector: 'edge[kind = "owns"]',
      style: { "line-color": v("--graph-edge-ownership"), "target-arrow-shape": "triangle", "target-arrow-color": v("--graph-edge-ownership") } },
    { selector: 'edge[kind = "shared_owner"]', style: { "line-color": v("--graph-edge-ownership") } },
    { selector: 'edge[kind = "referral"]',
      style: { "line-color": v("--graph-edge-referral"), "target-arrow-shape": "triangle", "target-arrow-color": v("--graph-edge-referral") } },
    { selector: "edge[?inferred]", style: { "line-style": "dashed", "line-dash-pattern": [4, 3] } },  // the ONLY graph dash
    { selector: "edge.hop1", style: { width: (e: cytoscape.EdgeSingular) => edgeWidth(e) + 0.75 } },
    { selector: "edge.hovered", style: { label: "data(hoverLabel)" } },

    /* ---- 2-hop focus ---- */
    { selector: ".dimmed", style: { opacity: Number(v("--graph-dim-opacity")) || 0.15 } },
  ] as cytoscape.StylesheetJson;
}
```
Notes:
- Edge width comes from one function (`edgeWidth`), so the `.hop1` boost (+0.75px) is correct for every kind.
- On theme switch, call `cy.style(cyStyle())`, because colours are resolved at build time.
- Risk bucketing for node rings: use the backend's case **severity** 1–4 when available. If only a probability is present (`node.risk` = p_confirm), use < 0.25 low, < 0.50 medium, < 0.75 high and otherwise critical. These are **placeholder thresholds** to agree with the model owner, and the same mapping must drive the badges.

### 7.8 Legend and side panel
**`<GraphLegend>`** sits below the canvas, left-aligned, as a 12px caption in `--color-text-muted`, and lists only the types and kinds present:
- **Row 1, nodes:** a 14px mini-shape for each type (same fill and stroke as the graph) plus its name: "◯ Provider ▢ Owner ▭ Facility ◇ Address ⬡ Bank/TIN ○ Phone △ Member".
- **Row 2, edges:** 24px line samples: thin light "Billed/rendered", mid-gray "Shared address/TIN/phone", dark with arrowhead "Owns", teal with arrowhead "Referral", and a dashed sample "Inferred" only if present.
- **Row 3, encodings:** "Ring = risk level", followed by four ring swatches with glyph labels (○ Low ◐ Medium ● High ◆ Critical), then a "✚ dot = patient harm" swatch.
- The legend replaces HEAD's `.net-legend` coloured dots (WIP: `LinkTypeLegend.tsx`). The edge-kind checkboxes stay as a filter `fieldset` above the graph, styled as chips (§10).

**Side panel** (selection): a 320px column to the right of the canvas (stacked below it under 1100px). It shows:
- an overline with the type name;
- the node label as h3;
- the ID in mono;
- the risk badge and harm flag;
- "Connections": counts by edge kind, each row clickable to highlight;
- "Open evidence" (secondary) and "Center graph here" (ghost) buttons.

The panel replaces HEAD's `.net-pick` paragraph (WIP: `LinkedEntityList.tsx` + panel).

### 7.9 Appendix: stylesheet for the legacy SVG renderer (only if the Cytoscape swap is abandoned)
This applies to HEAD's `src/three/NetworkGraph.tsx` + `features/workspace/network.css` (the WIP deletes the latter). The encodings are identical to §7.7. Hop depth comes from a BFS over enabled edges, the same as `networkModel.hopDistances`, with layout as in §7.6, computed in JS.
Markup contract: `<g class="net-node" data-type="provider|owner|facility|address|phone|bank|member" data-risk="low|medium|high|critical" data-harm data-subject data-selected data-hop="0|1|2" data-label="on">` containing `.net-ring`, `.net-gap`, `.net-shape`, `.net-glyph`, `.net-harm`, `.net-focus`, `.net-label`. Edges: `<line|path class="net-edge" data-kind=… data-hop=… data-inferred style="--w:1.5px">`.
```css
.n3-host { border: 0; border-radius: 0; background: var(--graph-bg); }
.net-map { display: block; width: 100%; height: auto; max-height: 70vh; background: var(--graph-bg); }

/* ---- edges ---- */
.net-edge { fill: none; stroke: var(--graph-edge-claim); stroke-width: var(--w, 1px); stroke-linecap: round;
            transition: opacity var(--duration-fast) var(--ease-standard); }
.net-edge:is([data-kind="shared_location"], [data-kind="shared_tin"], [data-kind="shared_contact"]) { stroke: var(--graph-edge-shared); --w: 1.5px; }
.net-edge:is([data-kind="owns"], [data-kind="shared_owner"]) { stroke: var(--graph-edge-ownership); --w: 2px; }
.net-edge[data-kind="owns"]     { marker-end: url(#net-arrow-ownership); }
.net-edge[data-kind="referral"] { stroke: var(--graph-edge-referral); --w: 1.5px; marker-end: url(#net-arrow-referral); }
.net-edge[data-inferred]        { stroke-dasharray: var(--graph-edge-inferred-dash); }
.net-edge[data-hop="1"]         { stroke-width: calc(var(--w, 1px) + 0.75px); }
.net-arrow-ownership { fill: var(--graph-edge-ownership); }
.net-arrow-referral  { fill: var(--graph-edge-referral); }
.net-edge-label { font: 500 var(--font-size-12)/1 var(--font-sans); fill: var(--color-text-muted); paint-order: stroke;
                  stroke: var(--graph-label-halo); stroke-width: 3px; stroke-linejoin: round; pointer-events: none; display: none; }
.net-edge:hover + .net-edge-label, .net-edge-label[data-on] { display: block; }

/* ---- nodes ---- */
.net-node { cursor: pointer; outline: none; transition: opacity var(--duration-fast) var(--ease-standard); }
.net-shape { stroke-width: var(--graph-node-stroke-width); }
.net-node[data-type="provider"] .net-shape { fill: var(--graph-node-provider-fill); stroke: var(--graph-node-provider-stroke); }
.net-node[data-type="owner"]    .net-shape { fill: var(--graph-node-owner-fill);    stroke: var(--graph-node-owner-stroke); }
.net-node[data-type="facility"] .net-shape { fill: var(--graph-node-facility-fill); stroke: var(--graph-node-facility-stroke); }
.net-node[data-type="address"]  .net-shape { fill: var(--graph-node-address-fill);  stroke: var(--graph-node-address-stroke); }
.net-node[data-type="phone"]    .net-shape { fill: var(--graph-node-phone-fill);    stroke: var(--graph-node-phone-stroke); }
.net-node[data-type="bank"]     .net-shape { fill: var(--graph-node-bank-fill);     stroke: var(--graph-node-bank-stroke); }
.net-node[data-type="member"]   .net-shape { fill: var(--graph-node-member-fill);   stroke: var(--graph-node-member-stroke); }
.net-glyph { color: var(--graph-node-glyph); pointer-events: none; }            /* lucide icons use currentColor */
.net-node:hover .net-shape { stroke-width: 2px; }

/* subject */
.net-node[data-subject] .net-shape { fill: var(--graph-subject-fill); stroke: none; }
.net-node[data-subject] .net-glyph { color: var(--graph-subject-glyph); }
.net-node[data-subject] .net-ring  { stroke: var(--graph-subject-ring-fallback); stroke-width: var(--graph-subject-ring-width); }

/* risk ring (outer, after a 2px gap) */
.net-ring { fill: none; stroke: none; stroke-width: var(--graph-ring-width); }
.net-node[data-risk="low"]      .net-ring { stroke: var(--risk-low-solid); }
.net-node[data-risk="medium"]   .net-ring { stroke: var(--risk-medium-solid); }
.net-node[data-risk="high"]     .net-ring { stroke: var(--risk-high-solid); }
.net-node[data-risk="critical"] .net-ring { stroke: var(--risk-critical-solid); }

/* harm notch */
.net-harm { display: none; fill: var(--harm-solid); stroke: var(--graph-bg); stroke-width: 1.5px; }
.net-node[data-harm] .net-harm { display: block; }

/* selection: 2px canvas gap + 2px focus ring */
.net-gap, .net-focus { fill: none; display: none; }
.net-gap   { stroke: var(--graph-bg); stroke-width: var(--graph-ring-gap); }
.net-focus { stroke: var(--color-focus); stroke-width: var(--focus-ring-width); }
.net-node:is([data-selected], :focus-visible) :is(.net-gap, .net-focus) { display: block; }

/* labels */
.net-label { display: none; font: var(--font-weight-medium) var(--graph-label-size)/1 var(--font-sans); fill: var(--color-text);
             paint-order: stroke; stroke: var(--graph-label-halo); stroke-width: 3px; stroke-linejoin: round; pointer-events: none; }
.net-node:is([data-subject], [data-selected], :hover, [data-label="on"]) .net-label { display: block; }
.net-node[data-subject] .net-label { font-size: var(--font-size-12); font-weight: var(--font-weight-semibold); }

/* 2-hop focus: dim everything not within 2 hops */
.net-map[data-focus] :is(.net-node, .net-edge):not([data-hop]) { opacity: var(--graph-dim-opacity); }

@media (prefers-reduced-motion: reduce) { .net-node, .net-edge { transition: none; } }
```
Shape and ring geometry (TSX):
```tsx
const SIZE = { subject: 22, provider: 14, owner: 12, facility: [15, 11], address: 12, phone: 7, bank: 12, member: 8 } as const;
function shapePath(type: string, r: number): string {
  switch (type) {
    case "owner":   return roundedRect(-r, -r, 2 * r, 2 * r, 4);
    case "facility":return roundedRect(-15, -11, 30, 22, 2);
    case "address": return `M0 ${-r}L${r} 0 0 ${r} ${-r} 0Z`;                       // diamond
    case "bank":    return hex(r);                                                  // pointy-side hexagon
    case "member":  return `M0 ${-r}L${r * 0.95} ${r * 0.7} ${-r * 0.95} ${r * 0.7}Z`; // triangle
    default:        return circle(r);                                               // provider, phone, subject
  }
}
// per node, inside <g className="net-node" data-type=… transform=…>:
<circle className="net-ring"  r={outer + 2 + 1.25} />           {/* 2px gap, 2.5px ring */}
<path   className="net-shape" d={shapePath(type, r)} />
<Stethoscope className="net-glyph" x={-6} y={-6} width={12} height={12} strokeWidth={1.75} /> {/* lucide-react */}
<circle className="net-harm"  cx={outer * 0.7} cy={-outer * 0.7} r={4.5} />
<circle className="net-gap"   r={ringOuter + 1} />  <circle className="net-focus" r={ringOuter + 3} />
<text   className="net-label" y={ringOuter + 14} textAnchor="middle">{clip(label, 22)}<title>{label}</title></text>
// <defs>: <marker id="net-arrow-ownership" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path className="net-arrow-ownership" d="M0 0L8 4 0 8Z"/></marker>
// shorten each edge by the target's outer radius + 3px so the arrow tip meets the border.
```


---

## 8. Tables

Applies to `.grid` / `.queue-grid` (manager queue), `ClaimsTable.tsx` (workspace claims), `.audit-grid` (audit).

| Rule | Spec |
|---|---|
| Row height | **40px** default, **32px** compact (`.grid.is-compact`, user toggle in the toolbar). Cells padded 0 12px, vertically centred |
| Text | 13px (`--type-body-sm`) cells; 14px for the primary cell (case/provider name, 500 weight) |
| Numbers | Right-aligned, `tabular-nums`, the header right-aligned too. Amounts are exact (`$48,210`) |
| IDs / NPIs / claim / hash | `--font-mono` 13px, `--color-text-muted`, never wrapped |
| Header | 12px, **500 weight, sentence case** (no uppercase shouting), `--color-text-muted` on `--color-surface-sunken`, **sticky** (`top: 0; z-index: var(--z-sticky)`), with a 1px bottom border in `--color-border` |
| Dividers | 1px `--color-border-subtle` between rows. **No zebra**: zebra competes with the hover, selected and risk-badge signals, and 40px rows with dividers scan cleanly |
| Hover | `--color-surface-hover` (`#f4f8f8`) |
| Selected / open row | `--color-brand-subtle` bg + **3px left bar** in `--color-brand-strong` (`box-shadow: inset 3px 0 0 …`). The bar is 3.38:1 against the row bg |
| Risk | A **badge** (glyph + label) in a Risk column. **Never colour a whole row.** The current lane-coloured inset bars (`.grid tr.lane-*`) are removed, and lane becomes a chip |
| Harm | ✚ flag in the Harm column for harm ≥ 3; muted number for 1–2 |
| Sort | Sortable headers are buttons: label + 12px chevron. Unsorted shows a faint ↕ (`--color-text-subtle`) on hover only; sorted shows ▲/▼ in `--color-text` with `aria-sort`. One sort at a time; numbers default to descending |
| Truncation | `max-width` + `text-overflow: ellipsis`; the full value goes in a tooltip (`title` minimum, `.cs-tooltip` preferred) after a 400ms hover delay and on keyboard focus |
| Empty | One row spanning all columns, 48px tall: a muted message plus a next action ("No cases match 'Harm ≥ 3'. **Clear filters**") |
| Loading | 6 skeleton rows of the real height (sunken bars at 40/60/30% widths) |
| Pagination | Bottom bar inside the table card: "1–50 of 312" (tabular) at left; page-size select (25/50/100) and prev/next ghost buttons at right. Use virtual scrolling instead when > 500 rows |
| Bulk actions | When ≥1 row is checked, a bar replaces the toolbar: `--color-brand-subtle` bg, 1px `--color-brand-strong` top border, "3 selected" (label) · actions (secondary buttons, a primary for the main one) · "Clear" ghost. Checkbox column 40px wide, `accent-color: var(--color-focus)` |

```css
.table-wrap { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); overflow: auto; }
.grid { width: 100%; border-collapse: separate; border-spacing: 0; font: var(--type-body-sm); color: var(--color-text); }
.grid th { position: sticky; top: 0; z-index: var(--z-sticky); height: var(--row-height-compact); padding: 0 var(--space-3);
  background: var(--color-surface-sunken); color: var(--color-text-muted); font: var(--type-caption); font-weight: var(--font-weight-medium);
  text-transform: none; letter-spacing: 0; text-align: left; white-space: nowrap; border-bottom: 1px solid var(--color-border); }
.grid td { height: var(--row-height); padding: 0 var(--space-3); vertical-align: middle; border-bottom: 1px solid var(--color-border-subtle); }
.grid.is-compact td { height: var(--row-height-compact); }
.grid :is(th, td).num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.grid td.mono { font: var(--type-mono); color: var(--color-text-muted); white-space: nowrap; }
.grid tbody tr { cursor: pointer; transition: background-color var(--duration-fast) var(--ease-standard); }
.grid tbody tr:hover { background: var(--color-surface-hover); }
.grid tbody tr:is(.is-open, [aria-selected="true"]) { background: var(--color-brand-subtle); }
.grid tbody tr:is(.is-open, [aria-selected="true"]) td:first-child { box-shadow: inset var(--border-width-accent) 0 0 var(--color-brand-strong); }
.grid tbody tr:focus-visible { outline: none; box-shadow: inset 0 0 0 2px var(--color-focus); }
.grid tr[class*="lane-"] td:first-child { box-shadow: none; }   /* retire lane-coloured row bars */
.grid .truncate { display: block; max-width: 16rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.th-sort { all: unset; cursor: pointer; display: inline-flex; gap: 4px; align-items: center; }
.th-sort[aria-sort="none"] .chev { opacity: 0; } .th-sort:hover .chev { opacity: 1; color: var(--color-text-subtle); }
.bulk-bar { display: flex; gap: var(--space-3); align-items: center; padding: var(--space-2) var(--space-3);
  background: var(--color-brand-subtle); border-top: 1px solid var(--color-brand-strong); font: var(--type-label); }
.table-foot { display: flex; justify-content: space-between; align-items: center; padding: var(--space-2) var(--space-3);
  border-top: 1px solid var(--color-border); font: var(--type-caption); color: var(--color-text-muted); font-variant-numeric: tabular-nums; }
```

---

## 9. Cards and KPI tiles

**Card**: `--color-surface`, 1px `--color-border`, `--radius-md` (6px), padding 20px (16px in dense grids), **no shadow at rest**. Header row layout:
- left: an optional overline (12px caps, muted) above the title (16px semibold, `--type-h4`; 14px semibold in dense grids);
- right: actions (ghost icon buttons and a "⋯" menu);
- below: an optional 13px muted subtitle.

Hover lifts nothing. Clickable cards get `border-color: var(--color-border-strong)` on hover, plus the focus ring.

Retire the coloured left borders on `.ws-panel`, `.lane-stat`, `.case-card` and `.proposal-card`. Today they encode the panel type, which is decoration that adds noise.

```css
.card, .ws-panel, .queue-chart, .control-board, .waterfall, .compare-strip, .override-form, .proposal-card {
  background: var(--color-surface); border: 1px solid var(--color-border); border-left-width: 1px;
  border-radius: var(--radius-md); padding: var(--card-padding); box-shadow: none; }
.card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-3); margin-bottom: var(--space-3); }
.card-head h2, .card-head h3 { font: var(--type-h4); margin: 0; }
.card-head .actions { display: flex; gap: var(--space-1); }
```

**KPI tile** (manager queue funnel `.stat-chip`, lane tiles `.lane-stat`, workspace `.ws-metrics`):
- **Label** first, 13px muted, e.g. "Flagged dollars".
- **Value** as `--type-numeric-lg` (30px, 600, tabular), e.g. "$1.24M", with the exact value in `title`.
- **Delta**: an arrow plus text, never colour alone. "▲ 8.2% vs prior run" / "▼ 3 cases". Muted colour by default; status colours are allowed only when direction has a clear good or bad meaning, and the arrow and words still carry it.
- Optional **sparkline**: 80×24, 1.5px `--chart-focus` line, last-point dot, no axes, on the right.
- Lane tiles act as filters: the selected tile uses `--color-brand-subtle` bg + 3px `--color-brand-strong` **top** bar, with `aria-pressed`. The harm-priority tile prefixes its label with ✚ in `--harm-fg` and keeps a neutral background.

```css
.kpi { display: grid; gap: var(--space-1); padding: var(--space-4); }
.kpi .kpi-label { font: var(--type-label); color: var(--color-text-muted); }
.kpi .kpi-value { font: var(--type-numeric-lg); font-variant-numeric: tabular-nums; letter-spacing: var(--letter-spacing-tight); color: var(--color-text); }
.kpi .kpi-delta { font: var(--type-body-sm); color: var(--color-text-muted); font-variant-numeric: tabular-nums; }
.lane-stat[aria-pressed="true"], .lane-stat.on { background: var(--color-brand-subtle); box-shadow: inset 0 var(--border-width-accent) 0 var(--color-brand-strong); }
```

**Queue / alert card pattern.** The investigator desk uses `.case-card` in `InvestigatorCasesPage`. The manager queue uses the same anatomy for the compare strip and any card view.
```
┌───────────────────────────────────────────────────────────────┐
│ ● High   ✚ Harm 4   Selected today            CASE-0192  ⋯   │  row 1: risk badge · harm flag · lane chip … ID (mono) · menu
│ Sunrise Home Health LLC                                        │  row 2: entity name (16px semibold)
│ Home health · NPI 1234567890 · 3 linked providers              │  row 3: meta (13px muted, NPI in mono)
│ ──────────────────────────────────────────────────────────── │
│ Flagged        P(confirm)   Evidence      Age / screen         │  dl: 12px muted labels
│ $48,210        43%          ▮▮▮▯▯ 62%     12d · 33d left       │  values 14px 600 tabular; age chip turns warning ≤15d, danger ≤7d (+ text)
│                                              [ Take case ]     │  primary only for the single main action
└───────────────────────────────────────────────────────────────┘
```
- **Age indicator**: "12d" since the alert, plus the screening clock from `screeningShort()`. Tone from `screeningTone()`: ok → muted text; warn → `--color-warning-*` chip "15d left"; hot → `--color-danger-*` chip "3d past". The words always say "left" or "past".
- Manager queue: the same row-1 badges in the table's Risk/Harm/Lane columns, and the waterfall/ranking policy as a plain card list with 1px dividers (no dotted borders).
- Cards are **never** tinted by risk. Only the badge carries risk.

---

## 10. Components

### 10.1 Buttons
| Variant | Bg | Text | Border | Hover | Active | Use |
|---|---|---|---|---|---|---|
| **Primary** | `--color-brand` `#2bbc2b` | `--color-text-on-brand` (ink, 6.66:1) | none | `--color-brand-hover` | `--color-brand-active` | **One per view**: "Take case", "Record decision", "Load run" |
| Secondary | `--color-surface` | `--color-text` | 1px `--color-border-strong` | `--color-surface-hover` | `--color-surface-sunken` | Everything else |
| Ghost | transparent | `--color-text-muted` → `--color-text` | none | `--color-surface-hover` | sunken | Toolbar, card actions, "Cancel", "Sign out" |
| Danger | `--color-surface` | `--color-danger-fg` | 1px `--color-danger-border` | `--color-danger-bg` | | "Close as unfounded", "Release" |
| Danger (confirm) | `--color-danger` `#b02b27` | white (6.52:1) | none | `--color-danger-fg` bg | | Only inside a confirm dialog |

Sizes: 36px (default) and 28px (`.btn-sm`), radius 4px, label 13px/500, padding 0 16px (0 10px sm), 16px icons with a 6px gap. Disabled: 50% opacity with `cursor: not-allowed`, and the label still explains why via `title`. Loading: an inline 12px spinner replaces the icon and the width stays fixed.
```css
.btn { display: inline-flex; align-items: center; gap: var(--space-1-5); height: var(--control-height); padding: 0 var(--space-4);
  border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); background: var(--color-surface); color: var(--color-text);
  font: var(--type-label); cursor: pointer; transition: background-color var(--duration-fast) var(--ease-standard); }
.btn:hover { background: var(--color-surface-hover); }
.btn.solid, .btn.primary { background: var(--color-brand); border-color: var(--color-brand); color: var(--color-text-on-brand); }
.btn.solid:hover, .btn.primary:hover { background: var(--color-brand-hover); border-color: var(--color-brand-hover); filter: none; }
.btn.solid:active, .btn.primary:active { background: var(--color-brand-active); border-color: var(--color-brand-active); }
.btn.ghost { background: transparent; border-color: transparent; color: var(--color-text-muted); }
.btn.ghost:hover { background: var(--color-surface-hover); color: var(--color-text); }
.btn.danger { color: var(--color-danger-fg); border-color: var(--color-danger-border); }
.btn.danger:hover { background: var(--color-danger-bg); }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn-sm { height: var(--control-height-sm); padding: 0 10px; font-size: var(--font-size-12); }
:where(.btn, a, button, input, select, textarea, [tabindex]):focus-visible { outline: none; box-shadow: var(--focus-ring); }
```

### 10.2 Badges and chips
- **Risk badge** `<RiskBadge level>`: 22px tall, radius 4, 1px `-border`, `-bg`, `-fg`, 12px/500, sentence case. Glyph then label, e.g. "◐ Medium". Never icon-only. In tables the label may shorten to "Med", but the glyph stays.
- **Harm flag** `<HarmFlag harm>`: the same metrics in harm tokens, "✚ Harm 4". Rendered only for harm ≥ 3.
- **Lane chip** (workflow state, not risk): neutral, i.e. `--color-surface-sunken` bg, `--color-text` text, no border. Harm-priority adds the ✚ glyph in `--harm-fg`, and "Selected today" adds a 6px `--color-brand-strong` dot. The current solid green and red lane pills are removed.
- **Status chip** (proposal/decision/audit status): status tokens, with a text label always present.
- **Filter chip** (edge kinds, toolbar filters): 28px, 1px `--color-border`, radius 4. When on, it gets `--color-brand-subtle` bg, a `--color-brand-strong` border and a ✓ glyph.
- **Count pill** (menu counters): sunken bg, 12px tabular.
```tsx
// src/components/Badge.tsx (replacing HarmBadge's 3 colour buckets)
const RISK = { 1: "low", 2: "medium", 3: "high", 4: "critical" } as const;
const GLYPH = { low: "○", medium: "◐", high: "●", critical: "◆" } as const;
const LABEL = { low: "Low", medium: "Medium", high: "High", critical: "Critical" } as const;
export function RiskBadge({ severity }: { severity: 1 | 2 | 3 | 4 }) {
  const lv = RISK[severity];
  return <span className={`badge risk risk-${lv}`}><span aria-hidden="true">{GLYPH[lv]}</span>{LABEL[lv]}<span className="sr"> risk</span></span>;
}
export function HarmFlag({ harm }: { harm: number }) {
  if (harm < 3) return <span className="muted cs-num" title="Patient harm">{harm}</span>;
  return <span className="badge harm" title="Patient-harm level (separate from financial risk)"><span aria-hidden="true">✚</span>Harm {harm}</span>;
}
```
```css
.badge { display: inline-flex; align-items: center; gap: 6px; height: 22px; padding: 0 var(--space-2); border: 1px solid transparent;
  border-radius: var(--radius-sm); font: var(--type-caption); font-weight: var(--font-weight-medium); letter-spacing: 0; text-transform: none;
  white-space: nowrap; background: var(--color-surface-sunken); color: var(--color-text); }
.badge.risk-low      { background: var(--risk-low-bg);      color: var(--risk-low-fg);      border-color: var(--risk-low-border); }
.badge.risk-medium   { background: var(--risk-medium-bg);   color: var(--risk-medium-fg);   border-color: var(--risk-medium-border); }
.badge.risk-high     { background: var(--risk-high-bg);     color: var(--risk-high-fg);     border-color: var(--risk-high-border); }
.badge.risk-critical { background: var(--risk-critical-bg); color: var(--risk-critical-fg); border-color: var(--risk-critical-border); }
.badge.harm          { background: var(--harm-bg);          color: var(--harm-fg);          border-color: var(--harm-border); }
.badge[class*="lane-"] { background: var(--color-surface-sunken); color: var(--color-text); border-color: transparent; }
.badge.lane-harm_priority::before { content: var(--harm-glyph); color: var(--harm-fg); }
.badge.lane-selected::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: var(--color-brand-strong); }
.badge.status-ok { background: var(--color-success-bg); color: var(--color-success-fg); border-color: var(--color-success-border); }
.badge.status-warn { background: var(--color-warning-bg); color: var(--color-warning-fg); border-color: var(--color-warning-border); }
.sla-chip.sla-ok   { background: transparent; color: var(--color-text-muted); }
.sla-chip.sla-warn { background: var(--color-warning-bg); color: var(--color-warning-fg); }
.sla-chip.sla-hot  { background: var(--color-danger-bg);  color: var(--color-danger-fg); }
/* detector approach badges: neutral, the text says which detector */
.badge:is(.approach-hard_rule, .approach-rules, .approach-behavioral_anomaly, .approach-anomaly, .approach-network_graph, .approach-graph) {
  background: var(--color-surface-sunken); color: var(--color-text-muted); border-color: transparent; }
```

### 10.3 Inputs
- Height 36px (28px small), radius 4, 1px `--color-border-strong` (3.91:1), surface background, 14px text, placeholder in `--color-text-subtle`.
- Hover: border `--neutral-600`. Focus: `--focus-ring`. Invalid: border `--color-danger-border` plus a 12px `--color-danger-fg` message with ⚠ below. Disabled: sunken background.
- Labels are 13px/500 above the field; helper text is 12px muted.
- Checkbox, radio and range use `accent-color: var(--color-focus)`.
- The decision radio cards (`.decide-actions label`) use a 1px border; selected gets `--color-brand-subtle` and a `--color-brand-strong` border.
- Textareas (decision reason ≥ 20 chars) show a live tabular counter, "18 / 20 minimum".
```css
:where(.app) :is(input:not([type="checkbox"], [type="radio"], [type="range"]), select, textarea) {
  height: var(--control-height); padding: 0 var(--space-3); border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm);
  background: var(--color-surface); color: var(--color-text); font: var(--type-body); }
:where(.app) textarea { height: auto; padding: var(--space-2) var(--space-3); line-height: var(--line-height-normal); }
:where(.app) :is(input, select, textarea)::placeholder { color: var(--color-text-subtle); }
:where(.app) :is(input, select, textarea):hover { border-color: var(--neutral-600); }
:where(.app) :is(input, select, textarea)[aria-invalid="true"] { border-color: var(--color-danger-border); }
:where(.app) input:is([type="checkbox"], [type="radio"], [type="range"]) { accent-color: var(--color-focus); }
.decide-actions label { border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: var(--color-surface); }
.decide-actions label.on { border-color: var(--color-brand-strong); background: var(--color-brand-subtle); }
```

### 10.4 App shell and navigation
**Decision: white top bar with a 3px Acentra-green brand bar.** Acentra's inner pages (`/about-us` and the solutions pages) use a **white header** (`.header .primary-section{background-color:#fff}`) with the colour logo. The dark ink only appears behind the marketing hero. A light shell matches that, keeps the canvas calm, and leaves green as the one accent. The 3px strip borrows Acentra's own 3px active-tab underline.
- **Brand bar**: 3px `--color-brand-bar` across the very top (decorative).
- **Top bar**: 56px, `--color-surface`, 1px bottom `--color-border`, sticky, `z-index: var(--z-shell)`.
- **Left side:** the brand mark and "ClaimShield Nexus" (15px/600) with a muted 12px "SIU · Acentra Health" beneath.
  - Replace the current conic-gradient `.brand-mark` with a flat mark: a 24px `--color-brand` shape, or the Acentra "A" symbol if licensed for the demo.
- **Nav** (Queue · Cases · Precedents · Audit) uses 14px/500 links in `--color-text-muted`:
  - hover: `--color-text`;
  - **active**: `--color-text` plus a 3px `--color-brand-strong` underline flush with the bar bottom, and `aria-current="page"`;
  - no pill backgrounds.
- **Right side:** user name (13px) with the role as muted 12px text, a "Sign out" ghost button, and an optional density toggle.
- **Page header** (`.page-head`): overline (`--color-brand-text`, the only green text) → h1 24px → 13px muted lede. Actions sit right-aligned and bottom-aligned (one primary at most). Spacing: 24px top, 16px bottom, then content. Breadcrumbs (workspace only): 12px muted "Cases / CASE-0192".
- **Workspace header** (`.ws-head`): case name as h2, chips row (risk, harm, lane, SLA), and the metrics strip (`.ws-metrics`) on `--color-surface-sunken` with radius 6 and tabular values.
- **Section menu** (`.ws-menu`): tabs with 13px/500 labels, active tab gets the 3px `--color-brand-strong` underline, counters as sunken count pills.
```css
.app { background: var(--color-bg); color: var(--color-text); font: var(--type-body); }
.mast { position: sticky; top: 0; z-index: var(--z-shell); height: var(--shell-topbar-height); padding: 0 var(--page-gutter);
  background: var(--color-surface); color: var(--color-text); border-top: var(--border-width-accent) solid var(--color-brand-bar);
  border-bottom: 1px solid var(--color-border); gap: var(--space-8); }
.mast-brand p, .mast-user em { color: var(--color-text-muted); font: var(--type-caption); }
.brand-mark { background: var(--color-brand); clip-path: polygon(50% 0%, 100% 78%, 78% 100%, 50% 72%, 22% 100%, 0 78%); width: 24px; height: 24px; } /* flat, no gradient */
.mast-nav { align-self: stretch; gap: var(--space-6); }
.mast-nav a { display: flex; align-items: center; padding: 0; border-radius: 0; font: var(--type-label); font-size: var(--font-size-14);
  color: var(--color-text-muted); border-bottom: var(--border-width-accent) solid transparent; margin-bottom: -1px; }
.mast-nav a:hover { color: var(--color-text); background: none; }
.mast-nav a.active { color: var(--color-text); background: none; border-bottom-color: var(--color-brand-strong); }
.mast-user .btn.ghost { color: var(--color-text-muted); border-color: transparent; }
.ws-menu button.on { color: var(--color-text); border-bottom: var(--border-width-accent) solid var(--color-brand-strong); font-weight: var(--font-weight-semibold); }
.ws-metrics, .facts.dense { background: var(--color-surface-sunken); border: 0; border-radius: var(--radius-md); }
.boot { background: var(--color-bg); color: var(--color-text); }
```

### 10.5 Drawers, banners, empty states
- **Drawer** (`CaseDrawer`, `EvidenceDrawer`): `--color-surface-raised`, 1px left border, `--shadow-overlay-lg`, `--z-drawer`, a 320ms slide that becomes instant under reduced motion. Use a scrim only if the drawer is modal.
- **Banner** (`.banner`): radius 6 with status tokens and a leading glyph (ⓘ ✓ ⚠ ✕). The text states the outcome, e.g. "Audit chain verified · 1,204 entries · 08 Oct 2026 14:05 IST".
- **Empty** (`.empty`): a **solid** 1px border (no dashed), surface background, a 13px muted explanation and one action.
- **Evidence JSON** (`.evidence-json`): sunken background, mono 12px, radius 4.

---

## 11. Implementation map (`/workspace/claimshield-ui/frontend`)

### 11.0 Stack facts (read-only inspection, 08 Oct 2026 ~20:10 IST)
- **Committed HEAD `e20263c`** ("Add Recharts, Cytoscape (fcose) and self-hosted brand fonts", 19:58 IST). It only touches `package.json` and the lockfile. Dependencies: React 19, Vite 8, TanStack Router/Query, three.js (`@react-three/fiber`/`drei`, landing and login only), plus **`recharts ^3.10.1`**, **`cytoscape ^3.34.3`**, **`cytoscape-fcose ^2.2.0`**, `react-is`, **`@fontsource-variable/inter`**, `@fontsource/roboto` and **`@fontsource/roboto-mono`**.
- **CSS approach at HEAD:** plain global CSS. `src/index.css` holds a handful of `:root` vars (`--ink`, `--paper`, `--rule`, `--mast`, `--harm`, `--selected`, `--sans` …), with per-feature files `queue.css`, `workspace-siu.css` and `workspace/network.css`. There is no Tailwind, CSS modules or MUI. Hex values are hard-coded in TSX: `QueueScene.tsx` (6), `NetworkGraph.tsx` (8) and `three/palette.ts`, which serves the landing only.
- **Charts and graph at HEAD** are still hand-rolled SVG/CSS (§6.0, §7.0). The libraries are installed but not imported yet.
- **Uncommitted WIP in the working tree** (another workstream, in flux; not authored by this review). It:
  - deletes `src/index.css` (staged) and `features/workspace/network.css`;
  - adds `src/styles/{tokens,base,components,public,shell}.css`, `src/lib/theme.ts` (`token()`), `src/components/charts/*` (Recharts), `src/components/network/*` (Cytoscape + fcose) and `src/components/ui/*`;
  - imports the fontsource packages in `main.tsx`;
  - modifies `Shell.tsx`, `router.tsx`, `FactorBars.tsx`, `EvidenceBar.tsx`, `NetworkPanel.tsx`, `ClaimsTable.tsx`, `PeerCompare.tsx`, `TimelinePanel.tsx` and others.
  
  Treat the paths below as **targets**: use the HEAD path if the WIP is dropped, or the WIP path if it lands.
- Landing and login (`landing.css`, `login.css`, `StoryScene`) sit **outside** `<Shell>`. Scope app styles under `.app` and **do not redefine `--sans`**, because `landing.css` uses it.

### 11.1 Legacy (HEAD `index.css`) → token mapping

| Legacy (`index.css`) | Replace with |
|---|---|
| `--ink #12262c` | `--color-text` (`#042126`, Acentra ink) |
| `--ink-2 #4a6670` | `--color-text-muted` |
| `--paper #eef3ef` / `--paper-2 #fff` | `--color-bg` / `--color-surface` |
| `--rule #d5e4da` | `--color-border` (dividers) or `--color-border-strong` (inputs) |
| `--mast #06141b`, `--mast-ink` | Top bar becomes `--color-surface` / `--color-text` (§10.4) |
| `--harm #b94832`, `--harm-bg` | `--harm-solid` / `--harm-fg` / `--harm-bg` (plum, ✚) |
| `--selected #1aa24c`, `--selected-bg` | Lane "selected" becomes a neutral chip with a brand dot. Selected **rows** use `--color-brand-subtle` + `--color-brand-strong` |
| `--monitor`, `--monitor-bg`, `--need`, `--need-bg` | Neutral lane chips. Warnings use `--color-warning-*` |
| `--ok`, `--err` | `--color-success-fg`, `--color-danger-fg` |
| `--focus #1aa24c` | `--color-focus` (`#1c873e`) via `--focus-ring` |
| `--green #1fbf5a` | `--color-brand` (`#2bbc2b`) |
| `--radius 12px` (and 10/14px literals) | `--radius-sm` 4 (controls) / `--radius-md` 6 (cards) |
| `--shadow` | Remove from cards. `--shadow-overlay(-lg)` on drawers and menus only |
| `--sans "Outfit"…` | Leave it for the landing page. The app uses `--font-sans` (Inter Variable) on `.app` |

### 11.2 Reconciling with the WIP `src/styles/tokens.css`
The WIP ships its own token file with different names. **Pick one source of truth.** The lowest-churn path is to replace the WIP `styles/tokens.css` with this `tokens.css` and append the bridge below, so the WIP components keep compiling while they migrate:
```css
/* bridge: WIP token names → this design system (delete once components use the canonical names) */
:root {
  --surface-page: var(--color-bg);        --surface-card: var(--color-surface);   --surface-sunken: var(--color-surface-sunken);
  --text-strong: var(--color-text);       --text-body: var(--color-text);         --text-muted: var(--color-text-muted);
  --text-accent: var(--color-brand-text); --text-link: var(--color-link);
  --border-subtle: var(--color-border);   --border-default: var(--color-border);  /* --border-strong: same name, same role */
  --action-primary-bg: var(--color-brand);       --action-primary-bg-hover: var(--color-brand-hover);
  --action-primary-fg: var(--color-text-on-brand); --focus-ring-color: var(--color-focus);
  --success-fg: var(--color-success-fg);  --success-bg: var(--color-success-bg);
  --warning-fg: var(--color-warning-fg);  --warning-bg: var(--color-warning-bg);
  --danger-fg: var(--color-danger-fg);    --danger-bg: var(--color-danger-bg);
  --info-fg: var(--color-info-fg);        --info-bg: var(--color-info-bg);
  --lane-harm: var(--harm-solid);         --lane-selected: var(--chart-focus);
  --lane-evidence: var(--chart-comparison); --lane-backlog: var(--chart-comparison);
  --node-provider: var(--graph-node-provider-fill); --node-facility: var(--graph-node-facility-fill);
  --node-owner: var(--graph-node-owner-fill);       --node-member: var(--graph-node-member-fill);
  --node-subject-ring: var(--graph-subject-ring-fallback);
  --edge-rendered: var(--graph-edge-claim); --edge-billed: var(--graph-edge-claim); --edge-at-facility: var(--graph-edge-claim);
  --edge-owns: var(--graph-edge-ownership); --edge-referral: var(--graph-edge-referral);
  --edge-shared-location: var(--graph-edge-shared); --edge-shared-tin: var(--graph-edge-shared); --edge-other: var(--graph-edge-claim);
  --font-display: var(--font-sans);
  --text-xs: var(--font-size-12); --text-sm: var(--font-size-13); --text-md: var(--font-size-14);
  --text-base: var(--font-size-14); --text-lg: var(--font-size-18); --text-xl: var(--font-size-20); --text-2xl: var(--font-size-24);
  --radius-lg: var(--radius-md); --radius-pill: var(--radius-full);
  --shadow-sm: none; --shadow-md: none; --shadow-lg: var(--shadow-overlay-lg);
  --motion-fast: var(--duration-fast); --motion-base: var(--duration-base); --ease-out: var(--ease-standard);
  --shell-header-height: var(--shell-topbar-height);
}
```
(`--space-*`, `--chart-1..8`, `--chart-grid`, `--chart-axis`, `--chart-band`, `--font-sans`, `--font-mono`, `--radius-sm`, `--radius-md` and `--content-max` already share names. The values follow this system. Note that the WIP's `--radius-md` is 10px and ours is 6px, and the WIP's `--focus-ring` is a colour while ours is a box-shadow; the WIP's `--focus-ring` call sites should move to `--focus-ring-color`.)

**Where the WIP currently diverges from this spec.** These are observations only; nothing was changed:

| WIP value | Issue | Spec |
|---|---|---|
| `--node-owner`, `--edge-owns`, `--chart-5` = `#7a4e9c` | Purple. Breaks the "no purple" rule, and it is **not an acentra.com colour** | Owner = sand tint, rounded square (§7.1). Chart-5 `#8c5a2b` |
| `--edge-shared-location`, `--chart-6` = `#b42318` | Red on a non-risk meaning collides with the risk ramp. Not an acentra.com colour | Shared edges are neutral `--graph-edge-shared`. Red is reserved for critical/danger |
| Saturated node fills (`#1c873e` provider, `#005f68` facility, …) | Green used as a data colour; four loud hues | Quiet tints + shape + glyph; green only on the subject |
| Edge `lineStyle` dotted/dashed per kind (shared_tin dotted 3.5px, shared_location dashed) | Dashes used as a type code | All solid; dash only for inferred (§7.2) |
| `--lane-selected: brand-green-700` | Brand green used as a data series | `--chart-focus` (`#15497e`) |
| `--action-primary-bg-hover: #b4ea54` (Acentra lime) | A verified Acentra colour (footer/timeline backgrounds, symbol gradient end) but very bright for an enterprise hover | `--color-brand-hover` (green-400). Lime is acceptable only if the team wants the marketing feel |
| `--radius-md 10px`, `--radius-lg 14px`, `--shadow-md` | Rounder and softer than the brief (4–6px, shadows on overlays only) | 4 / 6px; cards get borders, not shadows |
| `--focus-ring: #005f68` | Teal focus; fine for contrast but differs | `--color-focus` `#1c873e` |
| `--font-display: Roboto` on chart titles | A second family in data UI | Inter everywhere except the optional page `h1` |
| `.chart-plot .recharts-surface:focus { outline: none }` | Removes keyboard focus entirely | Keep the `:focus-visible` ring (§6.2) |

### 11.3 Order of work (highest visual impact first)

| # | Step | Files (HEAD → WIP target) | Tokens consumed |
|---|---|---|---|
| 1 | Install tokens: this `tokens.css` becomes `src/styles/tokens.css` (+ §11.2 bridge while migrating), imported first in `main.tsx` after the fontsource imports (§4) | `main.tsx`, `styles/tokens.css` (HEAD: import before `index.css`) | all |
| 2 | App base: `.app` font, colour and background; `body` stays for the landing page | `styles/base.css` (HEAD: `index.css` `.app`, `.page`, `.boot`) | `--type-body`, `--color-bg`, `--color-text`, `--font-sans` |
| 3 | **Shell / top bar**: white bar, 3px brand bar, flat mark, nav underline, `aria-current` | `components/Shell.tsx`, `styles/shell.css` (HEAD: `index.css` `.mast*`) | `--color-surface`, `--color-brand-bar`, `--color-brand-strong`, `--shell-topbar-height` |
| 4 | **Tables**: sticky sunken header, 40px rows, no lane row bars, selected row, tabular numbers, mono IDs | `styles/components.css` (HEAD `index.css` `.grid*`), `queue.css`, `ClaimsTable.tsx`, `AuditPage.tsx` | `--row-height`, `--color-surface-sunken`, `--color-brand-subtle`, `--font-mono` |
| 5 | **Badges**: `RiskBadge` (severity), `HarmFlag` (harm ≥ 3), neutral lane chips, SLA and status chips | `components/Badge.tsx` / `components/ui/*`, `queue.css` `.sla-chip`, `workspace-siu.css` | `--risk-*`, `--harm-*`, `--color-*-bg/fg` |
| 6 | **Cards and KPI tiles**: 1px border, radius 6, no shadow, no coloured left borders, numeric-lg values | `styles/components.css` (`.case-card`, `.lane-stat`, `.ws-panel*`, …), `queue.css` `.stat-chip` | `--card-padding`, `--radius-md`, `--type-numeric-lg` |
| 7 | **Charts (Recharts)**: add `lib/chartTheme.ts` (§6.1); `LaneHoursChart`, `FactorContributionChart`, `PeerComparisonChart`, `ClaimsTimelineChart`, `RiskHorizonChart` adopt §6.2–6.8; meters stay CSS (§6.9) | `components/charts/*`, `charts.css` (HEAD: `three/QueueScene.tsx`, `FactorBars.tsx`, `EvidenceBar.tsx`, `PeerCompare.tsx`) | `--chart-*`, `--harm-solid` |
| 8 | **Network graph (Cytoscape)**: `graphStyles.ts` becomes §7.7; `NODE_TYPES` shapes/fills per §7.1; `EDGE_TYPES` solid per §7.2; rings layout default, fcose refine; `focusHood`; legend + `LinkedEntityList` as the keyboard path | `components/network/{graphStyles.ts, networkModel.ts, CaseNetworkGraph.tsx, LinkTypeLegend.tsx, LinkedEntityList.tsx}`, `features/workspace/NetworkPanel.tsx` (HEAD: `three/NetworkGraph.tsx`) | `--graph-*`, `--risk-*-solid`, `--harm-solid`, `--color-focus` |
| 9 | Workspace chrome: header, metrics strip, section menu, findings cards, provenance | `features/workspace/CaseHeader.tsx` (WIP), `workspace-siu.css` | `--color-surface-sunken`, `--color-brand-strong` |
| 10 | Buttons, inputs, decision cards, drawers, banners, empty states | `styles/components.css` / `components/ui/*`, `DecisionBar.tsx`, `CaseDrawer.tsx`, `EvidenceDrawer.tsx` | `--color-brand*`, `--color-border-strong`, `--focus-ring`, `--shadow-overlay-lg` |
| 11 | New charts only if the brief needs them: `CalibrationChart` (§6.7), small multiples (§6.6) | `components/charts/CalibrationChart.tsx` | `--chart-1`, `--chart-reference*` |
| 12 | Clean-up: remove the §11.2 bridge once nothing references it, and the legacy vars (`rg "var\(--(ink|paper|rule|mast|selected|monitor|need|surface-card|text-strong|node-|edge-)"`). Leave `three/palette.ts`, `landing.css` and `login.css` alone | `styles/*` | n/a |

Quick check after each step: `rg -n "#[0-9a-fA-F]{3,6}\b" src --glob '!features/landing/*' --glob '!features/auth/*' --glob '!three/StoryScene.tsx' --glob '!three/palette.ts' --glob '!styles/tokens.css'`. The count should trend towards zero, because colours belong only in `tokens.css`.

---

## 12. Do / Don't

| Do | Don't |
|---|---|
| Use `#2bbc2b` for the primary button (ink text), the brand bar, and nothing else large | Use green to mean "low risk", "safe", "OK" or "approved" in case data |
| Use `#209b47` (`--color-brand-strong`) for selected and active indicators (≥ 3:1) | Use `#2bbc2b` for thin indicators or text (2.52:1) |
| Show risk as glyph + label + colour (○ Low · ◐ Medium · ● High · ◆ Critical) | Tint whole rows or cards by risk, or show colour-only dots |
| Keep patient harm a separate plum ✚ flag | Fold harm into the risk ramp or make it "extra red" |
| Highlight one series, gray the rest; direct-label bars (≤ 12) and line ends | Use a rainbow, more than 5 categorical series, or legends for single series |
| Use horizontal 1px solid gridlines, a darker zero line, ≤ 5 ticks, $1.2M abbreviations | Dash gridlines, draw value-axis lines, rotate tick labels, or use 3D |
| Use dashes only for reference lines (calibration y = x, capacity) and inferred graph edges | Dash data series, gridlines or edge types |
| Use 1px borders on cards and shadows only on overlays | Add drop shadows on cards, glassmorphism, gradients or glows |
| Use 4px radius on controls and 6px on cards | Use pill buttons, 12–14px radii or mixed radii |
| Use tabular numerals everywhere, right-aligned numbers, IDs in mono | Mix proportional digits in columns or centre-align numbers |
| Distinguish graph node types by shape + glyph with quiet tints | Give six node types six saturated hues |
| Dim to 15% outside the 2-hop neighbourhood | Hide nodes, animate physics on screen, or bounce on hover |
| Use 120/200/320ms motion with one easing curve, and honour reduced motion | Animate chart entrances, count numbers up, or move things continuously |
| Read every colour from `tokens.css` | Hard-code hex in TSX/CSS (`#1aa24c`, `#b94832` …) |
| Re-run `scripts/contrast_from_tokens.py` after any token edit | Eyeball contrast |
| Use purple/violet nowhere; plum is reserved for harm | Use purple or neon accents, or decorative particles |
