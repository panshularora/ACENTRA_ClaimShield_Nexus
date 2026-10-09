const pptxgen = require("pptxgenjs");
const sharp = require("sharp");

async function pngFromSvg(svg) {
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

async function buildDeck() {
  const pres = new pptxgen();
  pres.defineLayout({ name: "CS_WIDE", width: 13.333, height: 7.5 });
  pres.layout = "CS_WIDE";
  pres.author = "Team SE7EN";
  pres.title = "ClaimShield Nexus";
  pres.subject = "BUILD TO CARE 2026 · Acentra Health · Problem Statement 3";
  pres.company = "Team SE7EN";

  const C = {
    ink: "0B161C",
    ink2: "12242C",
    navy: "16313C",
    teal: "2A9A8F",
    tealLite: "7ED9CE",
    gold: "C6A15B",
    cream: "F6F1E8",
    cream2: "EDE6D8",
    paper: "FFFbf5",
    body: "2C3A40",
    mute: "7A8A90",
    muteDark: "8AA0A6",
    white: "FFFFFF",
    rule: "D8D0C2",
    ruleDark: "2A414A",
    rose: "C45C4A",
  };
  const FH = "Georgia";
  const FB = "Arial";
  const FM = "Consolas";
  const TOTAL = 16;
  const SW = 13.333;
  const SH = 7.5;
  const M = 0.62;

  const coverBg = await pngFromSvg(`
    <svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900">
      <defs>
        <radialGradient id="g" cx="78%" cy="28%" r="78%">
          <stop offset="0%" stop-color="#1C4A52"/>
          <stop offset="42%" stop-color="#123038"/>
          <stop offset="100%" stop-color="#0B161C"/>
        </radialGradient>
      </defs>
      <rect width="1600" height="900" fill="url(#g)"/>
      <g stroke="#2A9A8F" stroke-width="1.2" fill="none" opacity="0.28">
        <circle cx="1180" cy="250" r="70"/>
        <circle cx="1320" cy="340" r="46"/>
        <circle cx="1080" cy="420" r="34"/>
        <circle cx="1400" cy="180" r="22"/>
        <circle cx="1240" cy="520" r="58"/>
        <line x1="1180" y1="250" x2="1320" y2="340"/>
        <line x1="1180" y1="250" x2="1080" y2="420"/>
        <line x1="1320" y1="340" x2="1400" y2="180"/>
        <line x1="1080" y1="420" x2="1240" y2="520"/>
        <line x1="1320" y1="340" x2="1240" y2="520"/>
      </g>
      <g fill="#7ED9CE" opacity="0.85">
        <circle cx="1180" cy="250" r="5"/>
        <circle cx="1320" cy="340" r="5"/>
        <circle cx="1080" cy="420" r="5"/>
        <circle cx="1400" cy="180" r="4"/>
        <circle cx="1240" cy="520" r="5"/>
      </g>
    </svg>`);

  const creamTex = await pngFromSvg(`
    <svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900">
      <rect width="1600" height="900" fill="#F6F1E8"/>
      <rect x="0" y="0" width="18" height="900" fill="#16313C"/>
    </svg>`);

  function notes(slide, text) {
    slide.addNotes(text);
  }

  function brackets(slide, x, y, w, h, color, size = 0.18, stroke = 1.25) {
    const s = size;
    const ln = () => ({ color, width: stroke });
    slide.addShape(pres.shapes.LINE, { x, y, w: s, h: 0, line: ln() });
    slide.addShape(pres.shapes.LINE, { x, y, w: 0, h: s, line: ln() });
    slide.addShape(pres.shapes.LINE, { x: x + w - s, y, w: s, h: 0, line: ln() });
    slide.addShape(pres.shapes.LINE, { x: x + w, y, w: 0, h: s, line: ln() });
    slide.addShape(pres.shapes.LINE, { x, y: y + h - s, w: 0, h: s, line: ln() });
    slide.addShape(pres.shapes.LINE, { x, y: y + h, w: s, h: 0, line: ln() });
    slide.addShape(pres.shapes.LINE, { x: x + w, y: y + h - s, w: 0, h: s, line: ln() });
    slide.addShape(pres.shapes.LINE, { x: x + w - s, y: y + h, w: s, h: 0, line: ln() });
  }

  function footerDark(slide, n, section) {
    slide.addText("TEAM SE7EN  ·  CLAIMSHIELD NEXUS", {
      x: M, y: 7.08, w: 5.6, h: 0.24, margin: 0,
      fontFace: FM, fontSize: 10, color: C.muteDark, charSpacing: 1.4,
    });
    slide.addText(section, {
      x: 5.6, y: 7.08, w: 4.4, h: 0.24, margin: 0, align: "center",
      fontFace: FM, fontSize: 10, color: C.gold, charSpacing: 1.6,
    });
    slide.addText(String(n).padStart(2, "0") + "  /  " + String(TOTAL).padStart(2, "0"), {
      x: 10.4, y: 7.08, w: 2.3, h: 0.24, margin: 0, align: "right",
      fontFace: FM, fontSize: 10, color: C.muteDark, charSpacing: 1.4,
    });
  }

  function footerLight(slide, n, section) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 7.12, w: SW, h: 0.38, fill: { color: C.ink },
    });
    slide.addText("TEAM SE7EN  ·  CLAIMSHIELD NEXUS", {
      x: M, y: 7.12, w: 5.6, h: 0.38, margin: 0, valign: "middle",
      fontFace: FM, fontSize: 10, color: C.tealLite, charSpacing: 1.2,
    });
    slide.addText(section, {
      x: 5.6, y: 7.12, w: 4.4, h: 0.38, margin: 0, align: "center", valign: "middle",
      fontFace: FM, fontSize: 10, color: C.gold, charSpacing: 1.4,
    });
    slide.addText(String(n).padStart(2, "0") + "  /  " + String(TOTAL).padStart(2, "0"), {
      x: 10.4, y: 7.12, w: 2.3, h: 0.38, margin: 0, align: "right", valign: "middle",
      fontFace: FM, fontSize: 10, color: C.cream, charSpacing: 1.2,
    });
  }

  function eyebrow(slide, num, label, onDark) {
    slide.addText([
      { text: String(num).padStart(2, "0") + "   ", options: { color: onDark ? C.muteDark : C.mute, fontFace: FM, fontSize: 11, charSpacing: 2 } },
      { text: label, options: { color: onDark ? C.gold : C.teal, fontFace: FM, fontSize: 11, charSpacing: 2.4, bold: true } },
    ], { x: M, y: 0.32, w: 12, h: 0.28, margin: 0 });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: M, y: 0.64, w: 1.35, h: 0.035, fill: { color: onDark ? C.gold : C.teal },
    });
  }

  // ─────────────────────────────────────────────
  // 01 COVER
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.ink };
    s.addImage({ data: coverBg, x: 0, y: 0, w: SW, h: SH });
    s.addText("BUILD TO CARE  2026   ·   ACENTRA HEALTH   ·   PROBLEM STATEMENT 3", {
      x: M, y: 0.42, w: 12, h: 0.28, margin: 0,
      fontFace: FM, fontSize: 11, color: C.gold, charSpacing: 2.2,
    });
    s.addText("ClaimShield", {
      x: M, y: 1.85, w: 9.2, h: 0.95, margin: 0,
      fontFace: FH, fontSize: 54, color: C.cream, bold: true,
    });
    s.addText("Nexus", {
      x: M, y: 2.72, w: 9.2, h: 0.85, margin: 0,
      fontFace: FH, fontSize: 54, color: C.tealLite, italic: true,
    });
    s.addText("The SIU desk that turns unexplained claim alerts into ranked,\nevidence-backed cases a human can actually work today.", {
      x: M, y: 3.8, w: 8.4, h: 0.85, margin: 0,
      fontFace: FB, fontSize: 16, color: C.cream, italic: true,
    });
    s.addShape(pres.shapes.RECTANGLE, { x: M, y: 4.85, w: 2.1, h: 0.04, fill: { color: C.gold } });
    s.addText("TEAM SE7EN     ·     RECOMMEND ONLY     ·     SUSPICION, NEVER A FRAUD STAMP", {
      x: M, y: 5.15, w: 10, h: 0.32, margin: 0,
      fontFace: FM, fontSize: 12, color: C.muteDark, charSpacing: 1.2,
    });
    s.addText("01  /  16", {
      x: 10.6, y: 7.05, w: 2.1, h: 0.24, margin: 0, align: "right",
      fontFace: FM, fontSize: 11, color: C.muteDark,
    });
    notes(s, "Open on the title. Pause. Then: we do not find fraud. We build the desk an SIU can trust.");
  }

  // ─────────────────────────────────────────────
  // 02 ONE LINE
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.ink };
    eyebrow(s, 2, "THE SENTENCE", true);
    s.addText("Alerts become cases.\nCases fit today’s hours.\nA human still decides.", {
      x: M, y: 1.4, w: 12, h: 3.6, margin: 0,
      fontFace: FH, fontSize: 36, color: C.cream, italic: true,
    });
    s.addText("That is the whole product. Everything else is how we keep it explainable.", {
      x: M, y: 5.4, w: 11.5, h: 0.45, margin: 0,
      fontFace: FB, fontSize: 16, color: C.tealLite,
    });
    footerDark(s, 2, "THESIS");
    notes(s, "This is the spine. Repeat it at the close. Improper payment is not fraud; an alert is a suspicion to verify.");
  }

  // ─────────────────────────────────────────────
  // 03 PROBLEM
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.cream };
    s.addImage({ data: creamTex, x: 0, y: 0, w: SW, h: SH });
    eyebrow(s, 3, "THE PROBLEM", false);
    s.addText("An SIU cannot open a thousand unconnected hits.", {
      x: M, y: 0.85, w: 12, h: 0.7, margin: 0,
      fontFace: FH, fontSize: 26, color: C.ink,
    });
    const beats = [
      { n: "01", t: "The firehose", d: "Detectors shout on every line. Investigators get noise, not a pattern they can work." },
      { n: "02", t: "The clock", d: "CMS-style screening is 45 days. Ranking by dollars buries after-death billing and excluded parties." },
      { n: "03", t: "The miss", d: "Rings, shared owners, and referral monopolies live across claims. One claim is never the story." },
    ];
    beats.forEach((b, i) => {
      const x = M + i * 4.05;
      s.addShape(pres.shapes.RECTANGLE, { x, y: 1.85, w: 3.85, h: 4.55, fill: { color: C.paper } });
      s.addShape(pres.shapes.RECTANGLE, { x, y: 1.85, w: 3.85, h: 0.08, fill: { color: i === 1 ? C.gold : C.teal } });
      s.addText(b.n, {
        x: x + 0.28, y: 2.15, w: 3.3, h: 0.4, margin: 0,
        fontFace: FM, fontSize: 14, color: C.teal, charSpacing: 2,
      });
      s.addText(b.t, {
        x: x + 0.28, y: 2.6, w: 3.3, h: 0.55, margin: 0,
        fontFace: FH, fontSize: 22, color: C.ink,
      });
      s.addText(b.d, {
        x: x + 0.28, y: 3.3, w: 3.3, h: 1.55, margin: 0,
        fontFace: FB, fontSize: 15, color: C.body,
      });
    });
    footerLight(s, 3, "PROBLEM");
    notes(s, "Users: SIU investigators, managers, honest providers, members. Scarce resource is investigator time, not compute.");
  }

  // ─────────────────────────────────────────────
  // 04 STAKE
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.ink };
    eyebrow(s, 4, "THE STAKE", true);
    s.addText("6.12%", {
      x: M, y: 1.15, w: 7.2, h: 1.7, margin: 0,
      fontFace: FH, fontSize: 92, color: C.cream, bold: true,
    });
    s.addText("Medicaid improper payments, FY2025  ·  $37.39 billion", {
      x: M, y: 2.9, w: 12, h: 0.4, margin: 0,
      fontFace: FM, fontSize: 14, color: C.gold, charSpacing: 1,
    });
    s.addText("Most of that is documentation. CMS is explicit: it is generally not fraud.\nIf we call it fraud on this stage, we have already lost.", {
      x: M, y: 3.55, w: 12, h: 1.1, margin: 0,
      fontFace: FH, fontSize: 20, color: C.tealLite, italic: true,
    });
    const chips = ["Fraud is knowing", "Abuse is inflated practice", "Waste is inefficiency", "We recommend. We never convict."];
    chips.forEach((t, i) => {
      const x = M + (i % 2) * 6.2;
      const y = 5.0 + Math.floor(i / 2) * 0.7;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x, y, w: 5.9, h: 0.58, fill: { color: C.ink2 }, rectRadius: 0.04,
      });
      s.addText(t, {
        x: x + 0.25, y, w: 5.4, h: 0.58, margin: 0, valign: "middle",
        fontFace: FB, fontSize: 15, color: C.cream,
      });
    });
    footerDark(s, 4, "INTEGRITY");
    notes(s, "Cite CMS FY2025 fact sheet. 42 CFR 455.13–16 due process. 455.23 payment suspension is the state’s call.");
  }

  // ─────────────────────────────────────────────
  // 05 PRODUCT
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.cream };
    s.addImage({ data: creamTex, x: 0, y: 0, w: SW, h: SH });
    eyebrow(s, 5, "WHAT WE BUILT", false);
    s.addText("A live SIU application, not a slide about one.", {
      x: M, y: 0.85, w: 12, h: 0.55, margin: 0,
      fontFace: FH, fontSize: 26, color: C.ink,
    });
    const items = [
      { k: "Queue", v: "Manager loads an extract, sets hours and member weight, sees today’s recommended desk." },
      { k: "Worklist", v: "Investigators take ownership of harm-priority and selected cases." },
      { k: "Workspace", v: "Overview, findings, brief, claims, timeline, network, decide — one section at a time." },
      { k: "Evidence", v: "Every result names its tables, detector path, and supporting claim lines." },
      { k: "Wiki", v: "A closed decision can become a human-approved precedent page." },
      { k: "Audit", v: "Hash-chained log. Unmask, promote, and decide are append-only." },
    ];
    items.forEach((it, i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = M + col * 6.2;
      const y = 1.6 + row * 1.7;
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 5.95, h: 1.52, fill: { color: C.paper } });
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.09, h: 1.52, fill: { color: C.teal } });
      s.addText(it.k, {
        x: x + 0.35, y: y + 0.18, w: 5.35, h: 0.38, margin: 0,
        fontFace: FH, fontSize: 20, color: C.ink,
      });
      s.addText(it.v, {
        x: x + 0.35, y: y + 0.62, w: 5.35, h: 0.7, margin: 0,
        fontFace: FB, fontSize: 14, color: C.body,
      });
    });
    footerLight(s, 5, "PRODUCT");
    notes(s, "Demo logins: manager@demo.claimshield / demo-manager. Investigator counterpart exists. Landing is 3D; the SIU is a paper workstation.");
  }

  // ─────────────────────────────────────────────
  // 06 PIPELINE
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.ink };
    eyebrow(s, 6, "PIPELINE", true);
    s.addText("One path. Lambda never scores. FastAPI does.", {
      x: M, y: 0.85, w: 12, h: 0.5, margin: 0,
      fontFace: FH, fontSize: 24, color: C.cream,
    });
    const steps = [
      { n: "01", t: "Extract", d: "Tiny seed 7 or S3 CSVs. Member, provider, claim, line." },
      { n: "02", t: "Rules", d: "After death, excluded party, duplicates, caps, overlap." },
      { n: "03", t: "Peers", d: "Like-with-like specialty. A baseline only." },
      { n: "04", t: "Graph", d: "Owner, TIN, contact, referral. Rings live here." },
      { n: "05", t: "Cases", d: "Same NPI shares a case. Extra NPIs need a visible link." },
      { n: "06", t: "Desk", d: "Harm first. Knapsack the rest. Backlog stays named." },
    ];
    s.addShape(pres.shapes.RECTANGLE, {
      x: M + 0.55, y: 2.18, w: 11.1, h: 0.025, fill: { color: C.ruleDark },
    });
    steps.forEach((st, i) => {
      const x = M + i * 2.05;
      s.addShape(pres.shapes.OVAL, {
        x: x + 0.62, y: 2.0, w: 0.4, h: 0.4, fill: { color: C.teal },
      });
      s.addText(String(i + 1), {
        x: x + 0.62, y: 2.0, w: 0.4, h: 0.4, margin: 0, align: "center", valign: "middle",
        fontFace: FM, fontSize: 12, color: C.ink, bold: true,
      });
      s.addText(st.n + "  " + st.t, {
        x, y: 2.65, w: 1.95, h: 0.7, margin: 0, align: "center",
        fontFace: FH, fontSize: 16, color: C.cream,
      });
      s.addText(st.d, {
        x: x + 0.05, y: 3.4, w: 1.9, h: 1.7, margin: 0, align: "center",
        fontFace: FB, fontSize: 13, color: C.muteDark,
      });
    });
    s.addText("Ground-truth labels are never features. No AMA CPT. Synthetic NPIs pass Luhn.", {
      x: M, y: 5.45, w: 12, h: 0.4, margin: 0,
      fontFace: FM, fontSize: 13, color: C.gold,
    });
    footerDark(s, 6, "PIPELINE");
    notes(s, "Walk left to right. Emphasize 03 vs 05: peers score, they do not join. 06 is the desk, not a live ticker.");
  }

  // ─────────────────────────────────────────────
  // 07 ARCHITECTURE
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.cream };
    s.addImage({ data: creamTex, x: 0, y: 0, w: SW, h: SH });
    eyebrow(s, 7, "ARCHITECTURE", false);
    s.addText("Thin cloud trigger. One API. One workstation.", {
      x: M, y: 0.85, w: 12, h: 0.5, margin: 0,
      fontFace: FH, fontSize: 26, color: C.ink,
    });
    const layers = [
      { t: "Ingest", d: "S3 incoming/*.csv → existing Lambda claimshield-s3-processor\nor manager Load batch on the laptop." },
      { t: "API", d: "FastAPI, SQLAlchemy, cookie JWT, RBAC, CSRF.\nSQLite locally. Postgres in Docker." },
      { t: "Engines", d: "Rules catalog, peer stats, NetworkX graph,\ncase builder, five-factor knapsack." },
      { t: "SIU UI", d: "React queue, workspace, wiki, audit.\nThree.js only on the landing story." },
    ];
    layers.forEach((L, i) => {
      const y = 1.5 + i * 1.28;
      s.addShape(pres.shapes.RECTANGLE, { x: M, y, w: 12.05, h: 1.16, fill: { color: i % 2 === 0 ? C.ink : C.navy } });
      s.addText(String(i + 1).padStart(2, "0"), {
        x: M + 0.3, y, w: 0.7, h: 1.16, margin: 0, valign: "middle",
        fontFace: FM, fontSize: 16, color: C.gold,
      });
      s.addText(L.t, {
        x: M + 1.15, y, w: 2.3, h: 1.16, margin: 0, valign: "middle",
        fontFace: FH, fontSize: 20, color: C.cream,
      });
      s.addText(L.d, {
        x: M + 3.6, y, w: 8.2, h: 1.16, margin: 0, valign: "middle",
        fontFace: FB, fontSize: 15, color: C.tealLite,
      });
    });
    footerLight(s, 7, "ARCHITECTURE");
    notes(s, "We did not rebuild the bucket or Lambda. Live S3 needs public HTTPS. localhost cannot be Lambda’s URL. No Kafka, Neo4j, GNN, K8s.");
  }

  // ─────────────────────────────────────────────
  // 08 GROUPING
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.cream };
    s.addImage({ data: creamTex, x: 0, y: 0, w: SW, h: SH });
    eyebrow(s, 8, "DIFFERENTIATOR  ·  GROUPING", false);
    s.addText("The portal is the queue. Related alerts share a case.", {
      x: M, y: 0.85, w: 12, h: 0.55, margin: 0,
      fontFace: FH, fontSize: 24, color: C.ink,
    });
    const rules = [
      { t: "Same billing NPI", d: "Every hit on one provider is one investigation. Mentors agreed: no pager per alert." },
      { t: "A second NPI joins only on a visible link", d: "Identity ring (owner, TIN, contact), excluded owner, or concentrated referral." },
      { t: "Urgent stays visible", d: "After-death and excluded-party signals keep a harm-4 chip inside the group." },
    ];
    rules.forEach((r, i) => {
      const y = 1.6 + i * 1.65;
      s.addShape(pres.shapes.RECTANGLE, { x: M, y, w: 12.05, h: 1.5, fill: { color: C.paper } });
      s.addText(String(i + 1).padStart(2, "0"), {
        x: M + 0.3, y, w: 1.1, h: 1.5, margin: 0, valign: "middle",
        fontFace: FH, fontSize: 28, color: C.teal,
      });
      s.addText(r.t, {
        x: M + 1.6, y: y + 0.22, w: 10, h: 0.45, margin: 0,
        fontFace: FH, fontSize: 20, color: C.ink,
      });
      s.addText(r.d, {
        x: M + 1.6, y: y + 0.72, w: 10, h: 0.55, margin: 0,
        fontFace: FB, fontSize: 15, color: C.body,
      });
    });
    footerLight(s, 8, "GROUPING");
    notes(s, "Hero demo: after-death + concentrated referral, two NPIs, harm 4. Queue copy: grouped alerts · linked NPIs · urgent still visible.");
  }

  // ─────────────────────────────────────────────
  // 09 PEERS
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.ink };
    eyebrow(s, 9, "DIFFERENTIATOR  ·  PEERS", true);
    s.addText("Similar is not the same case.", {
      x: M, y: 1.35, w: 12, h: 1.1, margin: 0,
      fontFace: FH, fontSize: 36, color: C.cream, italic: true,
    });
    s.addText("Anomaly scoring needs clinics like this one as a baseline.\nThose NPIs are listed as comparison peers held out.\nThey never auto-join the investigation.", {
      x: M, y: 2.7, w: 12, h: 1.6, margin: 0,
      fontFace: FB, fontSize: 20, color: C.tealLite,
    });
    brackets(s, M, 4.6, 12.05, 1.85, C.gold, 0.22, 1.35);
    s.addText("Mentor line we kept: group a provider’s pattern. Do not smear honest neighbors.", {
      x: M + 0.4, y: 4.85, w: 11.25, h: 1.35, margin: 0, valign: "middle",
      fontFace: FH, fontSize: 18, color: C.gold, italic: true,
    });
    footerDark(s, 9, "PEERS");
    notes(s, "If asked why not cluster by specialty: that would pull honest DME suppliers into a fraud case. Visible graph links only.");
  }

  // ─────────────────────────────────────────────
  // 10 RANK
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.cream };
    s.addImage({ data: creamTex, x: 0, y: 0, w: SW, h: SH });
    eyebrow(s, 10, "RANKING", false);
    s.addText("Not 1,000 cases sorted by money.", {
      x: M, y: 0.82, w: 12, h: 0.5, margin: 0,
      fontFace: FH, fontSize: 26, color: C.ink,
    });
    const fac = [
      { w: "22", n: "Severity", d: "Scheme and harm level" },
      { w: "22", n: "Exposure", d: "Flagged dollars, scaled" },
      { w: "22", n: "Members", d: "Harm × people. Slider." },
      { w: "18", n: "Evidence", d: "How well it is backed" },
      { w: "16", n: "Urgency", d: "Horizon + 45-day clock" },
    ];
    fac.forEach((f, i) => {
      const x = M + i * 2.45;
      s.addShape(pres.shapes.RECTANGLE, { x, y: 1.55, w: 2.32, h: 3.15, fill: { color: C.ink } });
      s.addText(f.w + "%", {
        x, y: 1.85, w: 2.32, h: 0.85, margin: 0, align: "center",
        fontFace: FH, fontSize: 34, color: C.gold,
      });
      s.addText(f.n, {
        x: x + 0.1, y: 2.8, w: 2.12, h: 0.45, margin: 0, align: "center",
        fontFace: FH, fontSize: 16, color: C.cream,
      });
      s.addText(f.d, {
        x: x + 0.12, y: 3.35, w: 2.08, h: 0.9, margin: 0, align: "center",
        fontFace: FB, fontSize: 13, color: C.tealLite,
      });
    });
    s.addText("Then a knapsack fills investigator hours. Harm ≥ 4 takes a reserved slice first so member safety is not crowded out.", {
      x: M, y: 4.95, w: 12.05, h: 0.85, margin: 0,
      fontFace: FB, fontSize: 16, color: C.body,
    });
    footerLight(s, 10, "RANKING");
    notes(s, "Recompute with member-weight slider to show the desk change. Overflow is tracked backlog, not dismissal.");
  }

  // ─────────────────────────────────────────────
  // 11 LANES
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.ink };
    eyebrow(s, 11, "TODAY’S DESK", true);
    s.addText("Four lanes. One human loop.", {
      x: M, y: 0.85, w: 12, h: 0.5, margin: 0,
      fontFace: FH, fontSize: 26, color: C.cream,
    });
    const lanes = [
      { c: C.rose, t: "Harm priority", d: "After death, excluded party, excluded owner. Reserved hours." },
      { c: C.teal, t: "Selected", d: "Composite knapsack inside remaining hours and a slot cap." },
      { c: C.gold, t: "Gather evidence", d: "Strength below 0.40. Request records. Do not dismiss." },
      { c: C.muteDark, t: "Tracked backlog", d: "Still open. Promote by hand. A surge stays named." },
    ];
    lanes.forEach((L, i) => {
      const x = M + i * 3.05;
      s.addShape(pres.shapes.RECTANGLE, { x, y: 1.6, w: 2.92, h: 4.7, fill: { color: C.ink2 } });
      s.addShape(pres.shapes.RECTANGLE, { x, y: 1.6, w: 2.92, h: 0.1, fill: { color: L.c } });
      s.addText(String(i + 1).padStart(2, "0"), {
        x: x + 0.22, y: 1.95, w: 2.48, h: 0.4, margin: 0,
        fontFace: FM, fontSize: 13, color: L.c, charSpacing: 2,
      });
      s.addText(L.t, {
        x: x + 0.22, y: 2.5, w: 2.48, h: 0.95, margin: 0,
        fontFace: FH, fontSize: 22, color: C.cream,
      });
      s.addText(L.d, {
        x: x + 0.22, y: 3.55, w: 2.48, h: 1.7, margin: 0,
        fontFace: FB, fontSize: 15, color: C.muteDark,
      });
    });
    footerDark(s, 11, "QUEUE");
    notes(s, "Queue is ranked inside a run. New claims enter on load, ingest, or recompute. We do not reshuffle mid-brief.");
  }

  // ─────────────────────────────────────────────
  // 12 EVIDENCE
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.cream };
    s.addImage({ data: creamTex, x: 0, y: 0, w: SW, h: SH });
    eyebrow(s, 12, "DIFFERENTIATOR  ·  EVIDENCE", false);
    s.addText("Walk backward from the badge to the table.", {
      x: M, y: 0.85, w: 12, h: 0.5, margin: 0,
      fontFace: FH, fontSize: 24, color: C.ink,
    });
    const path = ["Extract", "Rules", "Peer anomaly", "Network", "Case builder", "Rank"];
    path.forEach((p, i) => {
      const x = M + i * 2.05;
      s.addShape(pres.shapes.OVAL, { x: x + 0.72, y: 1.55, w: 0.42, h: 0.42, fill: { color: C.ink } });
      s.addText(String(i + 1), {
        x: x + 0.72, y: 1.55, w: 0.42, h: 0.42, margin: 0, align: "center", valign: "middle",
        fontFace: FM, fontSize: 12, color: C.cream,
      });
      if (i < 5) {
        s.addShape(pres.shapes.RECTANGLE, {
          x: x + 1.2, y: 1.73, w: 1.5, h: 0.04, fill: { color: C.teal },
        });
      }
      s.addText(p, {
        x, y: 2.1, w: 1.95, h: 0.55, margin: 0, align: "center",
        fontFace: FB, fontSize: 13, color: C.body,
      });
    });
    const where = [
      { t: "Overview", d: "Which alerts sit together, case NPIs, source tables, urgent chip." },
      { t: "Findings", d: "Method, table roles, fields used, supporting lines, held-out peers." },
      { t: "Claims", d: "Source system and received date on every line from the extract." },
      { t: "Decide", d: "Attach the alerts you inspected. Reason of 20+ characters. Human only." },
    ];
    where.forEach((w, i) => {
      const x = M + i * 3.05;
      s.addShape(pres.shapes.RECTANGLE, { x, y: 2.85, w: 2.92, h: 2.55, fill: { color: C.paper } });
      s.addText(w.t, {
        x: x + 0.2, y: 3.08, w: 2.52, h: 0.42, margin: 0, valign: "top",
        fontFace: FH, fontSize: 18, color: C.teal,
      });
      s.addText(w.d, {
        x: x + 0.2, y: 3.52, w: 2.52, h: 1.4, margin: 0, valign: "top",
        fontFace: FB, fontSize: 14, color: C.body,
      });
    });
    footerLight(s, 12, "EVIDENCE");
    notes(s, "Judges will ask where a number came from. Click a finding, open the drawer, show the claim line.");
  }

  // ─────────────────────────────────────────────
  // 13 WORKSPACE
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.ink };
    eyebrow(s, 13, "THE WORKSPACE", true);
    s.addText("One case. Seven rooms. Inspect, then decide.", {
      x: M, y: 0.85, w: 12, h: 0.5, margin: 0,
      fontFace: FH, fontSize: 24, color: C.cream,
    });
    const tabs = [
      ["Overview", "Rank, grouping, trail"],
      ["Findings", "Each detector, lineage"],
      ["Brief", "Cited sentences only"],
      ["Claims", "Lines and source"],
      ["Timeline", "What happened when"],
      ["Network", "Two-hop neighbourhood"],
      ["Decide", "Human next step"],
    ];
    tabs.forEach((t, i) => {
      const y = 1.55 + i * 0.7;
      s.addText(String(i + 1).padStart(2, "0"), {
        x: M, y, w: 0.7, h: 0.62, margin: 0, valign: "middle",
        fontFace: FM, fontSize: 14, color: C.gold,
      });
      s.addText(t[0], {
        x: M + 0.85, y, w: 2.6, h: 0.62, margin: 0, valign: "middle",
        fontFace: FH, fontSize: 20, color: C.cream,
      });
      s.addText(t[1], {
        x: M + 3.6, y, w: 3.6, h: 0.62, margin: 0, valign: "middle",
        fontFace: FB, fontSize: 15, color: C.muteDark,
      });
    });
    brackets(s, 8.35, 1.55, 4.35, 4.9, C.gold, 0.2, 1.25);
    s.addText("Also true", {
      x: 8.65, y: 1.8, w: 3.8, h: 0.4, margin: 0,
      fontFace: FM, fontSize: 12, color: C.gold, charSpacing: 2,
    });
    const extra = [
      "Members stay masked",
      "Unmask is audited",
      "Promote / defer with a reason",
      "Ladder up to recommend 455.23",
      "Wiki from a closed decision",
      "Queue follows the latest run",
    ];
    extra.forEach((line, i) => {
      s.addText(line, {
        x: 8.65, y: 2.35 + i * 0.58, w: 3.8, h: 0.5, margin: 0, valign: "middle",
        fontFace: FB, fontSize: 14, color: C.cream,
      });
    });
    footerDark(s, 13, "WORKSPACE");
    notes(s, "Do not tour all seven tabs. Overview, findings, decide. Optionally claims Source column.");
  }

  // ─────────────────────────────────────────────
  // 14 SAFE
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.cream };
    s.addImage({ data: creamTex, x: 0, y: 0, w: SW, h: SH });
    eyebrow(s, 14, "SAFE BY DESIGN", false);
    s.addText("Dynamic when the world changes.\nStable while a person is writing.", {
      x: M, y: 0.85, w: 12, h: 1.35, margin: 0,
      fontFace: FH, fontSize: 26, color: C.ink, italic: true,
    });
    const cols = [
      { t: "Human in the loop", d: "Take ownership. Inspect each alert. Write a reason. A manager can promote or defer. Analysts cannot read cases." },
      { t: "Due process", d: "45-day clock on the row. Masked PHI. Hash-chained audit. Payment suspension is recommended, never executed." },
      { t: "Honest surge", d: "New claims enter on the next run. Harm still goes first. Overflow stays on a named backlog." },
    ];
    cols.forEach((c, i) => {
      const x = M + i * 4.05;
      s.addShape(pres.shapes.RECTANGLE, { x, y: 2.45, w: 3.9, h: 3.9, fill: { color: C.ink } });
      s.addText(String(i + 1).padStart(2, "0"), {
        x: x + 0.28, y: 2.7, w: 3.3, h: 0.35, margin: 0,
        fontFace: FM, fontSize: 12, color: C.gold, charSpacing: 2,
      });
      s.addText(c.t, {
        x: x + 0.28, y: 3.15, w: 3.3, h: 0.7, margin: 0,
        fontFace: FH, fontSize: 20, color: C.cream,
      });
      s.addText(c.d, {
        x: x + 0.28, y: 3.95, w: 3.3, h: 1.7, margin: 0,
        fontFace: FB, fontSize: 14, color: C.tealLite,
      });
    });
    footerLight(s, 14, "SAFETY");
    notes(s, "If asked about a live queue: ranking is live inside a run; membership refreshes on ingest/recompute. That is the adult SIU answer.");
  }

  // ─────────────────────────────────────────────
  // 15 WHY WE WIN
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.ink };
    eyebrow(s, 15, "THE EDGE", true);
    s.addText("Other teams will say they found fraud.\nWe show an SIU how to work.", {
      x: M, y: 0.85, w: 12, h: 1.2, margin: 0,
      fontFace: FH, fontSize: 26, color: C.cream, italic: true,
    });
    const rows = [
      ["Cases, not a firehose", "N alerts collapse to M investigations on the portal."],
      ["Peers held out", "Similar clinics score the outlier. They are not co-suspects."],
      ["Provenance everywhere", "Tables, fields, detector path — walk backward from the badge."],
      ["Harm-reserved knapsack", "Member safety gets hours before a billing mill fills the bag."],
      ["Named backlog", "What we cannot work today stays open. That is the surge story."],
      ["Recommend only", "No fraud stamp. No auto-suspension. A person records the next step."],
    ];
    rows.forEach((r, i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = M + col * 6.2;
      const y = 2.25 + row * 1.45;
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 5.95, h: 1.3, fill: { color: C.ink2 } });
      s.addText(r[0], {
        x: x + 0.28, y: y + 0.16, w: 5.4, h: 0.4, margin: 0,
        fontFace: FH, fontSize: 16, color: C.gold,
      });
      s.addText(r[1], {
        x: x + 0.28, y: y + 0.6, w: 5.4, h: 0.5, margin: 0,
        fontFace: FB, fontSize: 14, color: C.cream,
      });
    });
    footerDark(s, 15, "EDGE");
    notes(s, "This is the close of the argument. Then go to the 90-second path or live demo.");
  }

  // ─────────────────────────────────────────────
  // 16 CLOSE / DEMO
  // ─────────────────────────────────────────────
  {
    const s = pres.addSlide();
    s.background = { color: C.ink };
    s.addImage({ data: coverBg, x: 0, y: 0, w: SW, h: SH });
    s.addText("90 SECONDS ON THE MACHINE", {
      x: M, y: 0.4, w: 12, h: 0.28, margin: 0,
      fontFace: FM, fontSize: 12, color: C.gold, charSpacing: 2.2,
    });
    s.addText("Show the desk. Open the grouped harm case.\nWalk the evidence. Let a human decide.", {
      x: M, y: 0.85, w: 12, h: 1.25, margin: 0,
      fontFace: FH, fontSize: 26, color: C.cream,
    });
    const demo = [
      "Landing — improper payment is not fraud",
      "Load tiny seed 7 as manager",
      "Queue — grouped alerts, linked NPIs, urgent",
      "Overview + findings lineage",
      "Decide — 20+ character reason",
    ];
    demo.forEach((line, i) => {
      s.addText([
        { text: String(i + 1).padStart(2, "0") + "   ", options: { fontFace: FM, color: C.gold, fontSize: 14 } },
        { text: line, options: { fontFace: FB, color: C.cream, fontSize: 16 } },
      ], { x: M, y: 2.3 + i * 0.48, w: 12, h: 0.44, margin: 0, valign: "middle" });
    });
    s.addText("manager@demo.claimshield   ·   demo-manager", {
      x: M, y: 4.85, w: 12, h: 0.32, margin: 0,
      fontFace: FM, fontSize: 13, color: C.tealLite,
    });
    s.addShape(pres.shapes.RECTANGLE, { x: M, y: 5.4, w: 2.1, h: 0.035, fill: { color: C.gold } });
    s.addText("Recommend only. Improper payment is not fraud.\nTeam SE7EN  ·  BUILD TO CARE 2026", {
      x: M, y: 5.6, w: 12, h: 0.75, margin: 0,
      fontFace: FH, fontSize: 16, color: C.cream, italic: true,
    });
    notes(s, "Login already filled. Hero case: harm-4 grouped row with linked NPIs. End on decide. Do not say AI found fraud.");
  }

  const out = "/Users/namanrai/Downloads/ACENTRA_ClaimShield_Nexus-main/ClaimShield_Nexus_Judging.pptx";
  await pres.writeFile({ fileName: out });
  console.log("Wrote", out);
}

buildDeck().catch((e) => {
  console.error(e);
  process.exit(1);
});
