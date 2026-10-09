const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");

function renderIconSvg(IC, color, size = 256) {
  return ReactDOMServer.renderToStaticMarkup(React.createElement(IC, { color, size: String(size) }));
}
async function iconPng(IC, color, sz = 256) {
  return "image/png;base64," + (await sharp(Buffer.from(renderIconSvg(IC, color, sz))).png().toBuffer()).toString("base64");
}

async function buildDeck() {
  const {
    FaShieldAlt, FaExclamationTriangle, FaProjectDiagram, FaUsers, FaClipboardCheck,
    FaBalanceScale, FaDatabase, FaCogs, FaSearch, FaLink, FaCheckCircle,
    FaUserCheck, FaClock, FaLayerGroup, FaEye, FaServer, FaCloud,
  } = require("react-icons/fa");
  const { MdOutlinePolicy, MdOutlineHub } = require("react-icons/md");
  const { HiOutlineDocumentSearch } = require("react-icons/hi");

  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = "Team SE7EN";
  pres.title = "ClaimShield Nexus — BUILD TO CARE 2026";
  pres.subject = "Acentra Health PS3 SIU platform";

  const C = {
    navy: "0F2B3C", teal: "0D7377", tealLight: "14A3A8", mint: "A7E8D0",
    white: "FFFFFF", offWhite: "F4F7F6", lightGray: "E8EDED",
    gray: "6B7F82", dkGray: "4A5C60", darkText: "1A2E35",
    red: "D94452", amber: "E8A838", green: "2D9B6E", coral: "E07A5F",
  };
  const F = "Arial";
  const shadow = () => ({ type: "outer", blur: 4, offset: 2, angle: 135, color: "000000", opacity: 0.08 });

  const W = 13.3;
  const H = 7.5;
  const LBL_Y = 0.28;
  const TY = 0.48;
  const BODY_Y = 1.15;
  const FTR_Y = 7.05;
  const FTR_H = 0.45;
  const TOTAL = 14;

  function addFooter(sl, n, src) {
    sl.addShape(pres.shapes.RECTANGLE, { x: 0, y: FTR_Y, w: W, h: FTR_H, fill: { color: C.navy } });
    sl.addText("CLAIMSHIELD NEXUS  ·  TEAM SE7EN", {
      x: 0.4, y: FTR_Y, w: 5.2, h: FTR_H, fontSize: 10, fontFace: F, color: C.mint,
      valign: "middle", margin: 0, charSpacing: 1.2,
    });
    sl.addText(src || "Recommend only  ·  suspicion, not a fraud label", {
      x: 5.4, y: FTR_Y, w: 6.2, h: FTR_H, fontSize: 10, fontFace: F, color: C.white,
      valign: "middle", align: "center", margin: 0,
    });
    sl.addText(`${n}  /  ${TOTAL}`, {
      x: 11.7, y: FTR_Y, w: 1.2, h: FTR_H, fontSize: 10, fontFace: F, color: C.white,
      align: "right", valign: "middle", margin: 0,
    });
  }
  function addLabel(sl, t) {
    sl.addText(t, {
      x: 0.5, y: LBL_Y, w: 12.3, h: 0.22, fontSize: 11, fontFace: F, color: C.teal,
      charSpacing: 2.4, bold: true, margin: 0,
    });
  }
  function addTitle(sl, t) {
    sl.addText(t, {
      x: 0.5, y: TY, w: 12.3, h: 0.55, fontSize: 22, fontFace: F, color: C.darkText,
      bold: true, margin: 0, valign: "middle",
    });
  }

  const icoShield = await iconPng(FaShieldAlt, "#14A3A8", 256);
  const icoWarn = await iconPng(FaExclamationTriangle, "#D94452", 256);
  const icoGraph = await iconPng(FaProjectDiagram, "#0D7377", 256);
  const icoUsers = await iconPng(FaUsers, "#0D7377", 256);
  const icoClip = await iconPng(FaClipboardCheck, "#2D9B6E", 256);
  const icoScale = await iconPng(FaBalanceScale, "#0D7377", 256);
  const icoDb = await iconPng(FaDatabase, "#14A3A8", 256);
  const icoCogs = await iconPng(FaCogs, "#0D7377", 256);
  const icoSearch = await iconPng(FaSearch, "#0D7377", 256);
  const icoLink = await iconPng(FaLink, "#0D7377", 256);
  const icoCheck = await iconPng(FaCheckCircle, "#2D9B6E", 256);
  const icoHuman = await iconPng(FaUserCheck, "#2D9B6E", 256);
  const icoClock = await iconPng(FaClock, "#E8A838", 256);
  const icoLayer = await iconPng(FaLayerGroup, "#0D7377", 256);
  const icoEye = await iconPng(FaEye, "#0D7377", 256);
  const icoServer = await iconPng(FaServer, "#14A3A8", 256);
  const icoCloud = await iconPng(FaCloud, "#14A3A8", 256);
  const icoPolicy = await iconPng(MdOutlinePolicy, "#0D7377", 256);
  const icoHub = await iconPng(MdOutlineHub, "#0D7377", 256);
  const icoDoc = await iconPng(HiOutlineDocumentSearch, "#0D7377", 256);

  // ══════════════════════════════════════════════
  // 1 TITLE
  // ══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.navy };
    s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.16, h: H, fill: { color: C.teal } });
    s.addShape(pres.shapes.RECTANGLE, { x: 9.6, y: 0, w: 3.7, h: H, fill: { color: "0B2433" } });
    s.addImage({ data: icoShield, x: 10.55, y: 2.55, w: 1.6, h: 1.6 });
    s.addText("TEAM SE7EN", {
      x: 0.7, y: 1.35, w: 8.4, h: 0.32, fontSize: 13, fontFace: F, color: C.tealLight,
      charSpacing: 3, bold: true, margin: 0,
    });
    s.addText("ClaimShield Nexus", {
      x: 0.7, y: 1.75, w: 8.5, h: 0.85, fontSize: 40, fontFace: F, color: C.white, bold: true, margin: 0,
    });
    s.addText("A post-adjudication SIU desk for Medicaid-like fraud, waste, and abuse.", {
      x: 0.7, y: 2.7, w: 8.4, h: 0.45, fontSize: 16, fontFace: F, color: C.mint, margin: 0,
    });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 3.35, w: 2.4, h: 0.05, fill: { color: C.teal } });
    s.addText("BUILD TO CARE 2026  ·  Acentra Health  ·  Problem Statement 3", {
      x: 0.7, y: 3.55, w: 8.4, h: 0.32, fontSize: 14, fontFace: F, color: C.gray, margin: 0,
    });
    const pills = [
      { t: "Alerts → cases", y: 4.25 },
      { t: "Harm first, then capacity", y: 4.85 },
      { t: "Recommend only · humans decide", y: 5.45 },
    ];
    pills.forEach((p) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: 0.7, y: p.y, w: 5.6, h: 0.48, fill: { color: "163A4C" }, rectRadius: 0.08,
      });
      s.addText(p.t, {
        x: 0.9, y: p.y, w: 5.2, h: 0.48, fontSize: 14, fontFace: F, color: C.white,
        valign: "middle", margin: 0,
      });
    });
    s.addText("An alert is a suspicion to verify.\nImproper payment is not fraud.", {
      x: 9.85, y: 4.5, w: 3.15, h: 1.4, fontSize: 13, fontFace: F, color: C.mint, align: "center", margin: 0,
    });
  }

  // ══════════════════════════════════════════════
  // 2 PROBLEM
  // ══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.offWhite };
    addFooter(s, 2, "CMS FY2025 improper-payment fact sheet  ·  42 CFR 455.13–16  ·  PIM screening clock");
    addLabel(s, "THE PROBLEM");
    addTitle(s, "Thousands of unexplained alerts. A few dozen hours. Member harm still buried.");

    const cards = [
      { ico: icoWarn, h: "Alert firehose", b: "SIU inboxes fill with unconnected claim hits. Investigators cannot open a pattern. Honest providers get noise." },
      { ico: icoClock, h: "Time is the scarce resource", b: "Federal screening is 45 days. Ranking by dollars alone misses after-death billing and excluded parties." },
      { ico: icoScale, h: "Improper payment ≠ fraud", b: "Medicaid improper payments: 6.12% / $37.39B FY2025. Most is documentation. We never stamp a provider guilty." },
      { ico: icoUsers, h: "Who pays for a miss", b: "Members, honest clinics, and the program. Rings and shared owners never appear if you score one claim at a time." },
    ];
    cards.forEach((c, i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = 0.5 + col * 6.4;
      const y = BODY_Y + row * 2.55;
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 6.15, h: 2.35, fill: { color: C.white }, shadow: shadow() });
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.1, h: 2.35, fill: { color: C.teal } });
      s.addImage({ data: c.ico, x: x + 0.35, y: y + 0.28, w: 0.42, h: 0.42 });
      s.addText(c.h, {
        x: x + 0.9, y: y + 0.3, w: 4.9, h: 0.4, fontSize: 18, fontFace: F, color: C.darkText, bold: true, margin: 0, valign: "middle",
      });
      s.addText(c.b, {
        x: x + 0.35, y: y + 0.9, w: 5.5, h: 1.2, fontSize: 14, fontFace: F, color: C.dkGray, margin: 0,
      });
    });
  }

  // ══════════════════════════════════════════════
  // 3 WHAT WE BUILT
  // ══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.offWhite };
    addFooter(s, 3);
    addLabel(s, "THE PRODUCT");
    addTitle(s, "A working SIU application: extract in, ranked cases out, a human on the last click.");

    const items = [
      { ico: icoDb, t: "Landing + login", d: "3D story, then live cookie JWT and RBAC." },
      { ico: icoLayer, t: "Manager queue", d: "Load extract. Hours, member weight, slots. Promote / defer." },
      { ico: icoUsers, t: "Investigator desk", d: "Take ownership of today’s recommended cases." },
      { ico: icoDoc, t: "Workspace", d: "Overview, findings, brief, claims, timeline, network, decide." },
      { ico: icoClip, t: "Precedent wiki", d: "Closed work can become an approved page." },
      { ico: icoEye, t: "Hash-chained audit", d: "Unmask, decide, and override are append-only." },
    ];
    items.forEach((it, i) => {
      const col = i % 3;
      const row = Math.floor(i / 3);
      const x = 0.5 + col * 4.2;
      const y = BODY_Y + row * 2.65;
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 4.0, h: 2.45, fill: { color: C.white }, shadow: shadow() });
      s.addShape(pres.shapes.OVAL, { x: x + 0.28, y: y + 0.28, w: 0.55, h: 0.55, fill: { color: "E6F4F4" } });
      s.addImage({ data: it.ico, x: x + 0.38, y: y + 0.38, w: 0.35, h: 0.35 });
      s.addText(it.t, {
        x: x + 0.28, y: y + 1.0, w: 3.45, h: 0.4, fontSize: 16, fontFace: F, color: C.darkText, bold: true, margin: 0,
      });
      s.addText(it.d, {
        x: x + 0.28, y: y + 1.42, w: 3.45, h: 0.75, fontSize: 13, fontFace: F, color: C.dkGray, margin: 0,
      });
    });
  }

  // ══════════════════════════════════════════════
  // 4 PIPELINE
  // ══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.offWhite };
    addFooter(s, 4, "Ground-truth labels are never features  ·  no AMA CPT");
    addLabel(s, "DETECTION PIPELINE");
    addTitle(s, "One path from extract to desk. Lambda never scores. FastAPI does.");

    const steps = [
      { n: "01", t: "Extract", d: "Synthetic tiny seed 7 or S3 CSVs. Member, provider, claim, claim line." },
      { n: "02", t: "Rules", d: "Catalog hits: after death, excluded party, duplicates, unit caps, overlap." },
      { n: "03", t: "Peer anomaly", d: "Like-with-like specialty / type / rural. Peers are a baseline." },
      { n: "04", t: "Network", d: "Owner, TIN, contact, referral. Rings and monopolies live here." },
      { n: "05", t: "Case builder", d: "Same NPI shares a case. Extra NPIs join only on a visible link." },
      { n: "06", t: "Rank + pack", d: "Harm 4 first. Composite knapsack. Overflow stays tracked." },
    ];
    steps.forEach((st, i) => {
      const x = 0.45 + i * 2.12;
      s.addShape(pres.shapes.RECTANGLE, { x, y: BODY_Y, w: 2.02, h: 4.55, fill: { color: C.white }, shadow: shadow() });
      s.addShape(pres.shapes.RECTANGLE, { x, y: BODY_Y, w: 2.02, h: 0.08, fill: { color: i < 4 ? C.teal : C.green } });
      s.addText(st.n, {
        x, y: BODY_Y + 0.3, w: 2.02, h: 0.4, fontSize: 18, fontFace: F, color: C.teal, bold: true, align: "center", margin: 0,
      });
      s.addText(st.t, {
        x: x + 0.1, y: BODY_Y + 0.8, w: 1.82, h: 0.7, fontSize: 16, fontFace: F, color: C.darkText, bold: true, align: "center", margin: 0,
      });
      s.addText(st.d, {
        x: x + 0.12, y: BODY_Y + 1.65, w: 1.78, h: 2.5, fontSize: 13, fontFace: F, color: C.dkGray, align: "center", margin: 0,
      });
    });
  }

  // ══════════════════════════════════════════════
  // 5 ARCHITECTURE
  // ══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.offWhite };
    addFooter(s, 5, "No Kafka, Neo4j, GNN, or K8s  ·  one pipeline on a laptop");
    addLabel(s, "ARCHITECTURE");
    addTitle(s, "Thin cloud trigger. Detection, ranking, and evidence stay in one API.");

    const layers = [
      { ico: icoCloud, t: "Ingest", d: "S3 incoming/*.csv\nLambda claimshield-s3-processor\nor manager Load batch" },
      { ico: icoServer, t: "ClaimShield API", d: "FastAPI + SQLAlchemy\nJWT RBAC · CSRF\nSQLite local / Postgres" },
      { ico: icoCogs, t: "Engines", d: "Rules YAML catalog\nPeer stats\nNetworkX graph\nCase builder + knapsack" },
      { ico: icoUsers, t: "SIU UI", d: "React workstation\nQueue · workspace · wiki · audit\nThree.js on landing only" },
    ];
    layers.forEach((L, i) => {
      const x = 0.5 + i * 3.2;
      s.addShape(pres.shapes.RECTANGLE, { x, y: BODY_Y, w: 3.0, h: 3.55, fill: { color: C.white }, shadow: shadow() });
      s.addShape(pres.shapes.RECTANGLE, { x, y: BODY_Y, w: 3.0, h: 0.9, fill: { color: C.navy } });
      s.addImage({ data: L.ico, x: x + 0.22, y: BODY_Y + 0.25, w: 0.4, h: 0.4 });
      s.addText(L.t, {
        x: x + 0.7, y: BODY_Y, w: 2.15, h: 0.9, fontSize: 16, fontFace: F, color: C.white, bold: true, valign: "middle", margin: 0,
      });
      s.addText(L.d, {
        x: x + 0.2, y: BODY_Y + 1.15, w: 2.6, h: 2.15, fontSize: 14, fontFace: F, color: C.darkText, margin: 0,
      });
    });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 5.0, w: 12.3, h: 1.75, fill: { color: C.white }, shadow: shadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 5.0, w: 0.1, h: 1.75, fill: { color: C.amber } });
    s.addText("Contract we kept", {
      x: 0.85, y: 5.12, w: 11.7, h: 0.32, fontSize: 14, fontFace: F, color: C.darkText, bold: true, margin: 0,
    });
    s.addText("Lambda posts object keys with X-ClaimShield-Internal-Token. The API waits until member, provider, claim, and claim_line exist, then persist_dataset + execute_run. Outputs never write back to incoming/. Live S3 needs a public HTTPS host — localhost cannot be Lambda’s URL.", {
      x: 0.85, y: 5.48, w: 11.7, h: 1.1, fontSize: 14, fontFace: F, color: C.dkGray, margin: 0,
    });
  }

  // ══════════════════════════════════════════════
  // 6 GROUPING — differentiator
  // ══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.offWhite };
    addFooter(s, 6, "Mentor-aligned  ·  comparison peers are not co-subjects");
    addLabel(s, "DIFFERENTIATOR  ·  CASE GROUPING");
    addTitle(s, "The portal is the queue. Related alerts share a case. Similar clinics do not.");

    const left = [
      { t: "Same billing NPI", d: "Every detector hit on one provider is one investigation — not a pager per alert." },
      { t: "Join a second NPI only on a visible link", d: "Identity ring (owner / TIN / contact), excluded owner, or concentrated referral." },
      { t: "Urgent stays visible", d: "After-death and excluded-party hits keep a harm-4 chip even inside a larger group." },
    ];
    left.forEach((row, i) => {
      const y = BODY_Y + i * 1.7;
      s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y, w: 7.4, h: 1.55, fill: { color: C.white }, shadow: shadow() });
      s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y, w: 0.1, h: 1.55, fill: { color: C.teal } });
      s.addText(row.t, {
        x: 0.85, y: y + 0.18, w: 6.8, h: 0.4, fontSize: 16, fontFace: F, color: C.darkText, bold: true, margin: 0,
      });
      s.addText(row.d, {
        x: 0.85, y: y + 0.62, w: 6.8, h: 0.7, fontSize: 14, fontFace: F, color: C.dkGray, margin: 0,
      });
    });
    s.addShape(pres.shapes.RECTANGLE, { x: 8.15, y: BODY_Y, w: 4.65, h: 5.1, fill: { color: C.navy } });
    s.addText("HELD OUT", {
      x: 8.4, y: BODY_Y + 0.3, w: 4.15, h: 0.3, fontSize: 12, fontFace: F, color: C.tealLight, charSpacing: 2, bold: true, margin: 0,
    });
    s.addText("Comparison peers", {
      x: 8.4, y: BODY_Y + 0.7, w: 4.15, h: 0.45, fontSize: 20, fontFace: F, color: C.white, bold: true, margin: 0,
    });
    s.addText("Anomaly scoring needs similar providers as a baseline. Those NPIs never auto-join the case. The workspace lists them as comparison_peers_held_out.", {
      x: 8.4, y: BODY_Y + 1.35, w: 4.15, h: 1.8, fontSize: 14, fontFace: F, color: C.mint, margin: 0,
    });
    s.addText("Mentors: group the pattern. Do not smear honest neighbors.", {
      x: 8.4, y: BODY_Y + 3.4, w: 4.15, h: 1.2, fontSize: 14, fontFace: F, color: C.white, italic: true, margin: 0,
    });
  }

  // ══════════════════════════════════════════════
  // 7 RANKING
  // ══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.offWhite };
    addFooter(s, 7, "Default weights  ·  manager can raise member impact and recompute");
    addLabel(s, "CAPACITY-AWARE DESK");
    addTitle(s, "Not 1,000 cases sorted by dollars. Harm first, then a five-factor pack.");

    const factors = [
      { k: "22%", n: "Severity", d: "Scheme / harm level" },
      { k: "22%", n: "Exposure", d: "Flagged dollars, scaled" },
      { k: "22%", n: "Members", d: "Harm × people affected" },
      { k: "18%", n: "Evidence", d: "How well the hit is backed" },
      { k: "16%", n: "Urgency", d: "F30/60/90 + 45-day clock" },
    ];
    factors.forEach((f, i) => {
      const x = 0.5 + i * 2.52;
      s.addShape(pres.shapes.RECTANGLE, { x, y: BODY_Y, w: 2.4, h: 2.15, fill: { color: C.white }, shadow: shadow() });
      s.addText(f.k, {
        x, y: BODY_Y + 0.15, w: 2.4, h: 0.7, fontSize: 28, fontFace: F, color: C.teal, bold: true, align: "center", margin: 0,
      });
      s.addText(f.n, {
        x: x + 0.1, y: BODY_Y + 0.9, w: 2.2, h: 0.4, fontSize: 16, fontFace: F, color: C.darkText, bold: true, align: "center", margin: 0,
      });
      s.addText(f.d, {
        x: x + 0.1, y: BODY_Y + 1.35, w: 2.2, h: 0.55, fontSize: 12, fontFace: F, color: C.dkGray, align: "center", margin: 0,
      });
    });

    const lanes = [
      { c: C.red, t: "Harm priority", d: "Harm ≥ 4 takes a reserved slice of hours. Member safety is not crowded out." },
      { c: C.green, t: "Selected today", d: "Knapsack on composite inside remaining hours and a slot cap (default 20)." },
      { c: C.amber, t: "Gather evidence", d: "Strength below 0.40. Request records. Do not dismiss and do not call it fraud." },
      { c: C.navy, t: "Tracked backlog", d: "Still open. A manager can promote. Overflow is not a closed case." },
    ];
    lanes.forEach((L, i) => {
      const x = 0.5 + i * 3.2;
      const y = 3.55;
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 3.05, h: 3.2, fill: { color: C.white }, shadow: shadow() });
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 3.05, h: 0.1, fill: { color: L.c } });
      s.addText(L.t, {
        x: x + 0.18, y: y + 0.3, w: 2.7, h: 0.7, fontSize: 16, fontFace: F, color: C.darkText, bold: true, margin: 0,
      });
      s.addText(L.d, {
        x: x + 0.18, y: y + 1.1, w: 2.7, h: 1.8, fontSize: 13, fontFace: F, color: C.dkGray, margin: 0,
      });
    });
  }

  // ══════════════════════════════════════════════
  // 8 EVIDENCE TRAIL
  // ══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.offWhite };
    addFooter(s, 8);
    addLabel(s, "DIFFERENTIATOR  ·  EVIDENCE TRAIL");
    addTitle(s, "Every result names the table, the detector, and the path that produced it.");

    const path = [
      { n: "1", t: "Extract", d: "Batch / generator / S3 prefix" },
      { n: "2", t: "Rules", d: "Catalog hits on lines" },
      { n: "3", t: "Peer anomaly", d: "Baseline, not co-subjects" },
      { n: "4", t: "Network", d: "Owner, TIN, referral" },
      { n: "5", t: "Case builder", d: "Why these alerts sit together" },
      { n: "6", t: "Rank", d: "Why this case is here" },
    ];
    path.forEach((p, i) => {
      const x = 0.5 + i * 2.12;
      s.addShape(pres.shapes.OVAL, { x: x + 0.7, y: BODY_Y, w: 0.55, h: 0.55, fill: { color: C.navy } });
      s.addText(p.n, {
        x: x + 0.7, y: BODY_Y, w: 0.55, h: 0.55, fontSize: 14, fontFace: F, color: C.white, bold: true, align: "center", valign: "middle", margin: 0,
      });
      if (i < 5) {
        s.addShape(pres.shapes.RECTANGLE, { x: x + 1.3, y: BODY_Y + 0.24, w: 1.45, h: 0.06, fill: { color: C.tealLight } });
      }
      s.addText(p.t, {
        x, y: BODY_Y + 0.7, w: 2.02, h: 0.4, fontSize: 13, fontFace: F, color: C.darkText, bold: true, align: "center", margin: 0,
      });
      s.addText(p.d, {
        x, y: BODY_Y + 1.1, w: 2.02, h: 0.55, fontSize: 11, fontFace: F, color: C.dkGray, align: "center", margin: 0,
      });
    });

    const where = [
      { t: "Overview", d: "Grouped alerts, case NPIs, six-step trail, source tables, urgent chip." },
      { t: "Findings + drawer", d: "Method, table roles, fields used, supporting lines, held-out peers." },
      { t: "Claims", d: "Source column: extract system and received date on every line." },
      { t: "Decide", d: "Attach the alerts you inspected. Reason ≥ 20 characters. Human only." },
    ];
    where.forEach((w, i) => {
      const x = 0.5 + (i % 4) * 3.2;
      const y = 3.55;
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 3.05, h: 3.2, fill: { color: C.white }, shadow: shadow() });
      s.addText(w.t, {
        x: x + 0.18, y: y + 0.25, w: 2.7, h: 0.7, fontSize: 16, fontFace: F, color: C.teal, bold: true, margin: 0,
      });
      s.addText(w.d, {
        x: x + 0.18, y: y + 1.05, w: 2.7, h: 1.85, fontSize: 14, fontFace: F, color: C.dkGray, margin: 0,
      });
    });
  }

  // ══════════════════════════════════════════════
  // 9 WORKSPACE FEATURES
  // ══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.offWhite };
    addFooter(s, 9);
    addLabel(s, "MAJOR FEATURES");
    addTitle(s, "One case, seven sections. Inspect the hit, then record a next step.");

    const tabs = [
      { n: "Overview", d: "Rank factors, grouping, evidence trail" },
      { n: "Findings", d: "Each detector with lineage" },
      { n: "Brief", d: "Cited sentences; uncited text dropped" },
      { n: "Claims", d: "Lines, codes, paid, source" },
      { n: "Timeline", d: "Events on member and provider" },
      { n: "Network", d: "Two-hop billed / owns / referral" },
      { n: "Decide", d: "HITL ladder, audit, precedent" },
    ];
    tabs.forEach((t, i) => {
      const y = BODY_Y + i * 0.72;
      s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y, w: 7.5, h: 0.64, fill: { color: C.white }, shadow: shadow() });
      s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y, w: 0.1, h: 0.64, fill: { color: C.teal } });
      s.addText(`${String(i + 1).padStart(2, "0")}`, {
        x: 0.8, y, w: 0.7, h: 0.64, fontSize: 14, fontFace: F, color: C.teal, bold: true, valign: "middle", margin: 0,
      });
      s.addText(t.n, {
        x: 1.55, y, w: 2.2, h: 0.64, fontSize: 16, fontFace: F, color: C.darkText, bold: true, valign: "middle", margin: 0,
      });
      s.addText(t.d, {
        x: 3.85, y, w: 3.95, h: 0.64, fontSize: 14, fontFace: F, color: C.dkGray, valign: "middle", margin: 0,
      });
    });
    s.addShape(pres.shapes.RECTANGLE, { x: 8.25, y: BODY_Y, w: 4.55, h: 5.1, fill: { color: C.white }, shadow: shadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 8.25, y: BODY_Y, w: 4.55, h: 0.7, fill: { color: C.navy } });
    s.addText("Also on the desk", {
      x: 8.45, y: BODY_Y, w: 4.15, h: 0.7, fontSize: 16, fontFace: F, color: C.white, bold: true, valign: "middle", margin: 0,
    });
    const extra = [
      "Masked members; unmask is audited",
      "Peer compare on anomaly hits",
      "Promote / defer with a written reason",
      "Action ladder up to recommend 455.23",
      "Wiki proposal from a closed decision",
      "Queue follows the latest run",
    ];
    extra.forEach((line, i) => {
      s.addImage({ data: icoCheck, x: 8.5, y: BODY_Y + 0.95 + i * 0.65, w: 0.28, h: 0.28 });
      s.addText(line, {
        x: 8.95, y: BODY_Y + 0.88 + i * 0.65, w: 3.55, h: 0.42, fontSize: 13, fontFace: F, color: C.darkText, valign: "middle", margin: 0,
      });
    });
  }

  // ══════════════════════════════════════════════
  // 10 DUE PROCESS
  // ══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.offWhite };
    addFooter(s, 10, "42 CFR 455.13–16 due process  ·  455.23 is a state decision");
    addLabel(s, "SAFE BY DESIGN");
    addTitle(s, "Recommend only. Stable while a human is in the case. Refresh on the next run.");

    const cols = [
      { ico: icoHuman, t: "Human in the loop", d: "Take ownership. Inspect each alert. Write a reason. Manager promote/defer. Analyst cannot read cases." },
      { ico: icoPolicy, t: "Due process", d: "45-day clock on the row. Masked PHI. Hash-chained audit. Payment suspension is recommended, never executed." },
      { ico: icoHub, t: "Honest queue", d: "New claims enter on load, ingest, or recompute. We do not reshuffle the table mid-brief. Backlog stays named." },
    ];
    cols.forEach((c, i) => {
      const x = 0.5 + i * 4.2;
      s.addShape(pres.shapes.RECTANGLE, { x, y: BODY_Y, w: 4.0, h: 5.1, fill: { color: C.white }, shadow: shadow() });
      s.addShape(pres.shapes.OVAL, { x: x + 1.55, y: BODY_Y + 0.4, w: 0.9, h: 0.9, fill: { color: "E6F4F4" } });
      s.addImage({ data: c.ico, x: x + 1.72, y: BODY_Y + 0.57, w: 0.56, h: 0.56 });
      s.addText(c.t, {
        x: x + 0.25, y: BODY_Y + 1.55, w: 3.5, h: 0.7, fontSize: 18, fontFace: F, color: C.darkText, bold: true, align: "center", margin: 0,
      });
      s.addText(c.d, {
        x: x + 0.3, y: BODY_Y + 2.4, w: 3.4, h: 2.3, fontSize: 15, fontFace: F, color: C.dkGray, align: "center", margin: 0,
      });
    });
  }

  // ══════════════════════════════════════════════
  // 11 DIFFERENTIATORS
  // ══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.offWhite };
    addFooter(s, 11);
    addLabel(s, "WHY THIS BEATS AN ALERT DUMP");
    addTitle(s, "Other teams will say they found fraud. We show an SIU how to work.");

    const rows = [
      { t: "Cases, not a firehose", d: "N alerts collapse to M investigations on the portal." },
      { t: "Peers held out", d: "Similar providers score the outlier. They do not become co-suspects." },
      { t: "Provenance on every surface", d: "Tables, fields, detector path, extract source — walk backward from the badge." },
      { t: "Harm-reserved knapsack", d: "Member safety gets hours before a billing mill fills the backpack." },
      { t: "Named backlog", d: "What we cannot work today stays open. That is the honest surge story." },
      { t: "Recommend only", d: "No fraud stamp. No auto-suspension. A person records the next step." },
    ];
    rows.forEach((r, i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = 0.5 + col * 6.4;
      const y = BODY_Y + row * 1.7;
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 6.15, h: 1.55, fill: { color: C.white }, shadow: shadow() });
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.1, h: 1.55, fill: { color: C.green } });
      s.addText(r.t, {
        x: x + 0.4, y: y + 0.18, w: 5.5, h: 0.4, fontSize: 16, fontFace: F, color: C.darkText, bold: true, margin: 0,
      });
      s.addText(r.d, {
        x: x + 0.4, y: y + 0.65, w: 5.5, h: 0.7, fontSize: 14, fontFace: F, color: C.dkGray, margin: 0,
      });
    });
  }

  // ══════════════════════════════════════════════
  // 12 DEMO PATH
  // ══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.offWhite };
    addFooter(s, 12, "manager@demo.claimshield  /  demo-manager  ·  tiny seed 7");
    addLabel(s, "90-SECOND PATH");
    addTitle(s, "Show the desk, open a grouped harm case, walk the evidence, decide.");

    const demo = [
      { n: "1", t: "Landing", d: "Improper payment is not fraud. Cases are networks. Harm goes first." },
      { n: "2", t: "Load tiny 7", d: "Watch hours fill: harm, selected, gather evidence, backlog." },
      { n: "3", t: "Queue row", d: "Grouped alerts · linked NPIs · urgent still visible. Factor bars." },
      { n: "4", t: "Overview", d: "Why these alerts sit together. Six-step trail. Source tables." },
      { n: "5", t: "Findings", d: "Where this result came from. Open the drawer." },
      { n: "6", t: "Decide", d: "Human next step, 20+ character reason. Model did not close it." },
    ];
    demo.forEach((d, i) => {
      const col = i % 3;
      const row = Math.floor(i / 3);
      const x = 0.5 + col * 4.2;
      const y = BODY_Y + row * 2.65;
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: 4.0, h: 2.45, fill: { color: C.white }, shadow: shadow() });
      s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: y + 0.28, w: 0.5, h: 0.5, fill: { color: C.navy } });
      s.addText(d.n, {
        x: x + 0.25, y: y + 0.28, w: 0.5, h: 0.5, fontSize: 16, fontFace: F, color: C.white, bold: true, align: "center", valign: "middle", margin: 0,
      });
      s.addText(d.t, {
        x: x + 0.9, y: y + 0.28, w: 2.85, h: 0.5, fontSize: 18, fontFace: F, color: C.darkText, bold: true, valign: "middle", margin: 0,
      });
      s.addText(d.d, {
        x: x + 0.25, y: y + 1.05, w: 3.5, h: 1.15, fontSize: 14, fontFace: F, color: C.dkGray, margin: 0,
      });
    });
  }

  // ══════════════════════════════════════════════
  // 13 NEVER SAY / SAY
  // ══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.offWhite };
    addFooter(s, 13);
    addLabel(s, "LANGUAGE ON STAGE");
    addTitle(s, "If a judge only remembers three sentences, make them these.");

    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: BODY_Y, w: 6.15, h: 5.1, fill: { color: C.white }, shadow: shadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: BODY_Y, w: 6.15, h: 0.7, fill: { color: C.red } });
    s.addText("We will not say", {
      x: 0.75, y: BODY_Y, w: 5.7, h: 0.7, fontSize: 18, fontFace: F, color: C.white, bold: true, valign: "middle", margin: 0,
    });
    const no = [
      "The AI found fraud.",
      "This provider is guilty.",
      "Improper payment rate = fraud rate.",
      "Similar providers are in the same case.",
      "The queue live-shuffles every new alert.",
      "We suspend payment.",
    ];
    no.forEach((line, i) => {
      s.addText(line, {
        x: 0.85, y: BODY_Y + 0.95 + i * 0.65, w: 5.5, h: 0.55, fontSize: 15, fontFace: F, color: C.darkText, margin: 0, valign: "middle",
      });
    });

    s.addShape(pres.shapes.RECTANGLE, { x: 6.9, y: BODY_Y, w: 5.9, h: 5.1, fill: { color: C.white }, shadow: shadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 6.9, y: BODY_Y, w: 5.9, h: 0.7, fill: { color: C.green } });
    s.addText("We will say", {
      x: 7.15, y: BODY_Y, w: 5.45, h: 0.7, fontSize: 18, fontFace: F, color: C.white, bold: true, valign: "middle", margin: 0,
    });
    const yes = [
      "Ranked suspicion for human review.",
      "Grouped alerts; comparison peers held out.",
      "Harm first, then capacity; backlog still open.",
      "Here is the table, the rule, and the graph link.",
      "New claims enter on the next run.",
      "A person just recorded the next step.",
    ];
    yes.forEach((line, i) => {
      s.addText(line, {
        x: 7.2, y: BODY_Y + 0.95 + i * 0.65, w: 5.35, h: 0.55, fontSize: 15, fontFace: F, color: C.darkText, margin: 0, valign: "middle",
      });
    });
  }

  // ══════════════════════════════════════════════
  // 14 CLOSE
  // ══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.navy };
    s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.16, h: H, fill: { color: C.teal } });
    s.addImage({ data: icoShield, x: 0.7, y: 1.5, w: 0.7, h: 0.7 });
    s.addText("CLAIMSHIELD NEXUS", {
      x: 1.55, y: 1.55, w: 10, h: 0.6, fontSize: 16, fontFace: F, color: C.tealLight, charSpacing: 2, bold: true, valign: "middle", margin: 0,
    });
    s.addText("Alerts become cases.\nCases fit today’s hours.\nA human still decides.", {
      x: 0.7, y: 2.4, w: 12, h: 2.2, fontSize: 32, fontFace: F, color: C.white, bold: true, margin: 0,
    });
    s.addText("Team SE7EN  ·  BUILD TO CARE 2026  ·  Acentra PS3\nRecommend only. Improper payment is not fraud.", {
      x: 0.7, y: 5.0, w: 12, h: 0.8, fontSize: 16, fontFace: F, color: C.mint, margin: 0,
    });
  }

  const out = "/Users/namanrai/Downloads/ACENTRA_ClaimShield_Nexus-main/ClaimShield_Nexus_Judging.pptx";
  await pres.writeFile({ fileName: out });
  console.log("Wrote", out);
}

buildDeck().catch((err) => {
  console.error(err);
  process.exit(1);
});
