import { Link } from "@tanstack/react-router";
import { StoryScene } from "../../three/StoryScene";
import { usePrefersReducedMotion, useScrollProgress } from "../../three/useScrollProgress";
import "./landing.css";

const CHAPTERS = [
  {
    kicker: "Acentra Health code-a-thon · Problem 3",
    title: "ClaimShield Nexus",
    body: "Post-adjudication program integrity for Medicaid-like claims. Built to sit downstream of eCAMS and feed an SIU — not to label anyone as fraud.",
    points: [
      "Lives after adjudication. It does not recode or deny a claim.",
      "Ranks suspicion for scarce investigator hours. A flag is a queue position.",
      "Due process stays with the state: humans decide, models cite.",
    ],
    facts: [
      { value: "eCAMS", label: "Sits downstream of the claims engine" },
      { value: "SIU", label: "Built for special investigations, not pay-and-chase noise" },
      { value: "Recommend", label: "Never prints fraud on a provider" },
    ],
  },
  {
    kicker: "The scarce resource",
    title: "Investigators have hours, not infinities.",
    body: "CMS estimated Medicaid improper payments at 6.12% ($37.39B) in FY2025. Most of that is documentation, not fraud. The SIU still has to find the few patterns that warrant human review before the 45-day screening clock runs out.",
    points: [
      "Improper payment is not a fraud rate. Documentation errors swamp true schemes.",
      "Monday-morning work is takeable suspicion, not a wall of alerts.",
      "Capacity is the control: 40 investigator hours, not infinite review.",
    ],
    facts: [
      { value: "6.12%", label: "Medicaid improper payments, FY2025" },
      { value: "$37.39B", label: "Estimated dollars in that rate" },
      { value: "45 days", label: "Screening clock the SIU is racing" },
    ],
  },
  {
    kicker: "Alerts are not cases",
    title: "A case is a network.",
    body: "Duplicate lines, EVV gaps, and peer outliers are signals. Shared TIN, owner, and contact edges turn them into rings. ClaimShield groups alerts the way a ring actually bills — across NPIs — so G1-style telefraud is one case, not twelve tickets.",
    points: [
      "Rules catch known billing patterns. Anomaly catches like-with-like peers.",
      "Identity graph ties TIN, owner, facility, and contact — the ring, not the NPI.",
      "Rural small-n peers show limited confidence. They do not auto-flag.",
    ],
    facts: [
      { value: "Rules + anomaly", label: "Both fire. Neither is a verdict." },
      { value: "One ring", label: "G1-style telefraud is one case, not twelve tickets" },
      { value: "Peers", label: "Specialty, geography, provider type, population" },
    ],
  },
  {
    kicker: "CMS harm first",
    title: "Beneficiary harm never waits in line.",
    body: "A thousand cases do not become a dollar sort. ClaimShield combines scheme severity, financial exposure, member impact, evidence strength, and urgency, then packs the result into investigator hours and a top-N desk. AI recommends today's 20. Investigators decide. The rest stay open on a tracked backlog.",
    points: [
      "Harm-priority cases jump the dollar queue. Vulnerable members come first.",
      "Today's queue is multi-factor inside capacity. Dollars or evidence alone never pick the set.",
      "Needs-evidence gathers records. Overflow stays tracked. Nothing auto-labels fraud.",
    ],
    facts: [
      { value: "Five factors", label: "Severity, exposure, members, evidence, urgency" },
      { value: "Top N + hours", label: "Capacity knapsack, then a 20-case desk cap" },
      { value: "Human loop", label: "Promote or defer with a reason. Backlog is not a close." },
    ],
  },
  {
    kicker: "30 / 60 / 90",
    title: "Risk is a clock, not a scoreboard.",
    body: "Each case carries a discrete-time hazard: probability the pattern is still burning at 30, 60, and 90 days. The queue sorts by expected value inside the hours you actually have.",
    points: [
      "F30 / F60 / F90 are survival of the pattern, not a guilt score.",
      "Managers set horizon and capacity. The queue recomputes lanes.",
      "A longer horizon raises expected value. It does not invent new evidence.",
    ],
    facts: [
      { value: "F30", label: "Still-burning chance at one month" },
      { value: "F60", label: "Two-month discrete hazard" },
      { value: "F90", label: "Three-month clock the manager can select" },
    ],
  },
  {
    kicker: "Recommend only",
    title: "Humans decide. Models cite.",
    body: "The investigation brief is grounded in claim lines, rule IDs, and statistics. Payment suspension stays with the state. Every decision writes a hash-chained audit event and can become a precedent page.",
    points: [
      "The brief names the line, the detector, and the peer group — not a fraud stamp.",
      "Disposition is a human act: monitor, refer, or close with a reason.",
      "Audit events hash in sequence. Approved reasons can become wiki precedent.",
    ],
    facts: [
      { value: "Cite", label: "Lines, rule IDs, and peer stats in the brief" },
      { value: "Decide", label: "State SIU keeps payment-suspension authority" },
      { value: "Record", label: "Hash-chained audit, optional precedent" },
    ],
  },
];

export function LandingPage() {
  const progress = useScrollProgress();
  const reduced = usePrefersReducedMotion();
  const chapter = Math.min(CHAPTERS.length - 1, Math.floor(progress * CHAPTERS.length));

  return (
    <div className="landing">
      <div className="landing-stage" aria-hidden="true">
        <StoryScene progress={progress} reduced={reduced} />
        <div className="landing-veil" />
      </div>

      <header className="landing-nav">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true" />
          <div>
            <strong>ClaimShield Nexus</strong>
            <em>Acentra Health code-a-thon prototype</em>
          </div>
        </div>
        <nav>
          <a href="#story">The problem</a>
          <a href="#method">The method</a>
          <Link to="/login">Enter SIU</Link>
        </nav>
      </header>

      <section className="landing-hero" id="story">
        <p className="kicker">Program integrity · post-adjudication</p>
        <h1>Turn a flood of claim alerts into a few cases an SIU can actually work.</h1>
        <p className="lede">
          Rules, peer anomalies, and identity graphs collapse into capacity-ranked cases.
          Harm goes first. Evidence is cited. A human still decides.
        </p>
        <div className="landing-cta">
          <Link to="/login" className="btn solid">
            Open the SIU
          </Link>
          <a className="btn ghost" href="#method">
            Scroll the story
          </a>
        </div>
        <dl className="stat-row">
          <div>
            <dt>Improper payments ≠ fraud</dt>
            <dd>6.12% Medicaid FY2025</dd>
          </div>
          <div>
            <dt>Screening clock</dt>
            <dd>45 calendar days</dd>
          </div>
          <div>
            <dt>Queue math</dt>
            <dd>Five factors + capacity + human override</dd>
          </div>
        </dl>
      </section>

      <div id="method">
        {CHAPTERS.map((ch, i) => (
          <section
            key={ch.title}
            className={`landing-chapter ${i === chapter ? "is-active" : ""}`}
            data-chapter={i}
          >
            <div className="chapter-shell">
              <div className="chapter-panel">
                <div className="chapter-meta">
                  <p className="kicker">{ch.kicker}</p>
                  <span className="chapter-index">
                    {String(i + 1).padStart(2, "0")} / {String(CHAPTERS.length).padStart(2, "0")}
                  </span>
                </div>
                <h2>{ch.title}</h2>
                <p className="chapter-body">{ch.body}</p>
                <ul className="chapter-points">
                  {ch.points.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
              </div>
              <aside className="chapter-aside">
                {ch.facts.map((fact) => (
                  <div className="chapter-fact" key={fact.value}>
                    <strong>{fact.value}</strong>
                    <span>{fact.label}</span>
                  </div>
                ))}
              </aside>
            </div>
          </section>
        ))}
      </div>

      <section className="landing-end">
        <div className="chapter-shell">
          <div className="chapter-panel">
            <p className="kicker">Demo path</p>
            <h2>Manager loads the tiny extract. Investigator works a ring.</h2>
            <p className="chapter-body">
              Sign in as manager, run seed 7, watch harm / selected / needs-evidence fill 40 hours,
              then open a multi-NPI case. The product never prints the word fraud on a provider.
            </p>
            <ol className="demo-steps">
              <li>
                <strong>Manager</strong>
                <span>Load tiny, seed 7. Set hours. Recompute the queue.</span>
              </li>
              <li>
                <strong>Queue</strong>
                <span>Change hours or member impact. Watch today's 20 move. Overflow stays open.</span>
              </li>
              <li>
                <strong>Investigator</strong>
                <span>Open a ring, read the brief, dispose with a cited reason.</span>
              </li>
            </ol>
            <Link to="/login" className="btn solid">
              Sign in to the live API
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
