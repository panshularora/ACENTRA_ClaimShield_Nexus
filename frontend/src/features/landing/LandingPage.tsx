import { Link } from "@tanstack/react-router";
import { StoryScene } from "../../three/StoryScene";
import { usePrefersReducedMotion, useScrollProgress } from "../../three/useScrollProgress";
import "./landing.css";

const CHAPTERS = [
  {
    kicker: "Acentra Health · Problem 3",
    title: "ClaimShield Nexus",
    body: "Post-adjudication program integrity for Medicaid-like claims. Built to sit downstream of eCAMS and feed an SIU — not to label anyone as fraud.",
  },
  {
    kicker: "The scarce resource",
    title: "Investigators have hours, not infinities.",
    body: "CMS estimated Medicaid improper payments at 6.12% ($37.39B) in FY2025. Most of that is documentation, not fraud. The SIU still has to find the few patterns that warrant human review before the 45-day screening clock runs out.",
  },
  {
    kicker: "Alerts are not cases",
    title: "A case is a network.",
    body: "Duplicate lines, EVV gaps, and peer outliers are signals. Shared TIN, owner, and contact edges turn them into rings. ClaimShield groups alerts the way a ring actually bills — across NPIs — so G1-style telefraud is one case, not twelve tickets.",
  },
  {
    kicker: "CMS harm first",
    title: "Beneficiary harm never waits in line.",
    body: "Services after death and excluded parties take a reserved slice of capacity. Remaining hours fill a knapsack of expected recovery plus a harm term. Weak evidence goes to needs-evidence, not the investigator’s day.",
  },
  {
    kicker: "30 / 60 / 90",
    title: "Risk is a clock, not a scoreboard.",
    body: "Each case carries a discrete-time hazard: probability the pattern is still burning at 30, 60, and 90 days. The queue sorts by expected value inside the hours you actually have.",
  },
  {
    kicker: "Recommend only",
    title: "Humans decide. Models cite.",
    body: "The investigation brief is grounded in claim lines, rule IDs, and statistics. Payment suspension stays with the state. Every decision writes a hash-chained audit event and can become a precedent page.",
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
            <em>for Acentra Health</em>
          </div>
        </div>
        <nav>
          <a href="#story">The problem</a>
          <a href="#method">The method</a>
          <Link to="/login">Enter SIU</Link>
        </nav>
      </header>

      <section className="landing-hero" id="story">
        <p className="kicker">Accelerating better outcomes · program integrity</p>
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
            <dd>Harm override + knapsack</dd>
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
            <p className="kicker">{ch.kicker}</p>
            <h2>{ch.title}</h2>
            <p>{ch.body}</p>
          </section>
        ))}
      </div>

      <section className="landing-end">
        <p className="kicker">Demo path</p>
        <h2>Manager loads the tiny extract. Investigator works a ring.</h2>
        <p>
          Sign in as manager, run seed 7, watch harm / selected / needs-evidence fill 40 hours, then
          open a multi-NPI case. The product never prints the word fraud on a provider.
        </p>
        <Link to="/login" className="btn solid">
          Sign in to the live API
        </Link>
      </section>
    </div>
  );
}
