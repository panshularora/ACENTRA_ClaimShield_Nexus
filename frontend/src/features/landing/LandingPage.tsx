import { useGSAP } from "@gsap/react";
import { Link } from "@tanstack/react-router";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Component, type ErrorInfo, type ReactNode, Suspense, useCallback, useRef, useState } from "react";
import { AppLogo } from "../../components/ui/AppLogo";
import { PipelineScene } from "../../three/PipelineScene";
import "./landing.css";

gsap.registerPlugin(useGSAP, ScrollTrigger);

const STEPS = [
  {
    name: "Rules",
    detail: "Known billing patterns on paid lines: duplicates, after-death DME, EVV gaps, LEIE, unbundling.",
  },
  {
    name: "Peers",
    detail: "Same specialty, geography, and provider type. Volume alone is a reason to look.",
  },
  {
    name: "Graph",
    detail: "Shared TIN, owner, contact, or referral. One ring becomes one case.",
  },
  {
    name: "Rank",
    detail: "Five factors packed into the hours you actually have. Harm goes first. A person still decides.",
  },
];

const FACTORS = [
  { name: "Scheme severity", weight: "22%", detail: "How serious the billed pattern looks." },
  { name: "Financial exposure", weight: "22%", detail: "Dollars already paid on flagged lines." },
  { name: "Member impact", weight: "22%", detail: "People on those lines, and harm level." },
  { name: "Evidence strength", weight: "18%", detail: "How complete the packet is." },
  { name: "Urgency", weight: "16%", detail: "Days left on the 45-day screening clock." },
];

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

class SceneGate extends Component<{ children: ReactNode; fallback: ReactNode; onError: () => void }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(_error: Error, _info: ErrorInfo) {
    this.props.onError();
    this.setState({ failed: true });
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

function StaticCore() {
  return (
    <svg className="scene-static" viewBox="0 0 200 200" aria-hidden="true" focusable="false">
      {Array.from({ length: 42 }, (_, i) => {
        const h = Math.sin((i + 1) * 12.9898) * 43758.5453;
        const u = h - Math.floor(h);
        const h2 = Math.sin((i + 101) * 12.9898) * 43758.5453;
        const u2 = h2 - Math.floor(h2);
        const angle = u * Math.PI * 2;
        const r = 30 + u2 * 62;
        return (
          <circle
            key={i}
            cx={100 + r * Math.cos(angle)}
            cy={100 + r * Math.sin(angle) * 0.62}
            r={i < 6 ? 2.2 : 1.4}
            fill={i < 6 ? "#d46568" : "#c5d0c8"}
            opacity={0.75}
          />
        );
      })}
      <circle cx={100} cy={100} r={58} fill="none" stroke="#5c6b72" strokeWidth={1} strokeDasharray="3 3" />
      <circle cx={100} cy={100} r={40} fill="none" stroke="#e6ebe4" strokeWidth={1.25} />
      <circle cx={100} cy={100} r={22} fill="#c5d0c8" opacity={0.28} />
      <circle cx={100} cy={100} r={15} fill="#c5d0c8" />
    </svg>
  );
}

export function LandingPage() {
  const root = useRef<HTMLDivElement>(null);
  const progressRef = useRef(0);
  const reduce = prefersReducedMotion();
  const [failed, setFailed] = useState(false);
  const fail = useCallback(() => setFailed(true), []);

  useGSAP(
    () => {
      if (reduce) return;
      gsap.utils.toArray<HTMLElement>(".reveal").forEach((el) => {
        gsap.fromTo(
          el,
          { y: 28, autoAlpha: 0 },
          {
            y: 0,
            autoAlpha: 1,
            duration: 0.7,
            ease: "power3.out",
            scrollTrigger: { trigger: el, start: "top 86%", once: true },
          },
        );
      });
      ScrollTrigger.create({
        trigger: ".landing-hero",
        start: "top top",
        end: "bottom top",
        onUpdate: (self) => {
          progressRef.current = self.progress;
        },
      });
    },
    { scope: root },
  );

  const stage = failed || reduce ? (
    <StaticCore />
  ) : (
    <SceneGate fallback={<StaticCore />} onError={fail}>
      <Suspense fallback={<StaticCore />}>
        <PipelineScene progressRef={progressRef} reducedMotion={reduce} onContextLost={fail} />
      </Suspense>
    </SceneGate>
  );

  return (
    <div className="landing" ref={root}>
      <header className="landing-nav">
        <div className="brand-lockup">
          <AppLogo />
        </div>
        <nav>
          <a href="#method">How it works</a>
          <a href="#demo">Demo</a>
          <Link to="/login">Enter SIU</Link>
        </nav>
      </header>

      <section className="landing-hero" id="story">
        <div className="hero-copy">
          <p className="kicker">Post-adjudication SIU desk</p>
          <h1>Paid-claim noise becomes a desk an investigator can finish today.</h1>
          <p className="lede">
            Claim lines fall into the rank core. Four checks fire. The dashed ring is desk
            capacity. ClaimShield recommends. A human still decides.
          </p>
          <div className="landing-cta">
            <Link to="/login" className="btn solid">
              Open the SIU
            </Link>
            <a className="btn ghost" href="#method">
              How the desk is built
            </a>
          </div>
          <dl className="stat-row">
            <div>
              <dt>Medicaid FY2025</dt>
              <dd>6.12% improper payments</dd>
            </div>
            <div>
              <dt>Screening clock</dt>
              <dd>45 days</dd>
            </div>
            <div>
              <dt>Today&apos;s control</dt>
              <dd>Hours, not infinite review</dd>
            </div>
          </dl>
        </div>
        <aside className="hero-stage" aria-label="Live 3D claim detector">
          <div className="stage-canvas">{stage}</div>
          <ul className="scene-legend" aria-label="How to read the detector">
            <li>
              <span className="scene-key scene-key-line" aria-hidden="true" />
              Claim line
            </li>
            <li>
              <span className="scene-key scene-key-flag" aria-hidden="true" />
              Flagged line
            </li>
            <li>
              <span className="scene-key scene-key-band" aria-hidden="true" />
              Desk capacity
            </li>
            <li>
              <span className="scene-key scene-key-rate" aria-hidden="true" />
              Packed hours
            </li>
          </ul>
        </aside>
      </section>

      <section className="landing-band" id="method">
        <div className="band-head reveal">
          <p className="kicker">How it works</p>
          <h2>Four checks, then a capacity-ranked desk.</h2>
          <p>
            Rules catch known billing patterns. Peers catch outliers. The identity graph catches a
            ring that bills clean on each NPI. Rank packs the result into the hours you have.
          </p>
        </div>
        <ol className="process-rail">
          {STEPS.map((step, i) => (
            <li key={step.name} className="reveal">
              <span className="process-index">{i + 1}</span>
              <strong>{step.name}</strong>
              <span>{step.detail}</span>
            </li>
          ))}
        </ol>
        <div className="rank-ledger reveal">
          <p className="kicker">Desk rank uses these five — not suspicion alone</p>
          <p className="ledger-note">
            Suspicion is a separate review score. It never prints as 100%, and it is not a finding.
          </p>
          <ul>
            {FACTORS.map((factor) => (
              <li key={factor.name}>
                <span className="factor-weight">{factor.weight}</span>
                <strong>{factor.name}</strong>
                <span>{factor.detail}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="landing-band split">
        <div className="reveal">
          <p className="kicker">Recommend only</p>
          <h2>The packet says what fired, where, and why to look.</h2>
          <p>
            Each finding names the problem in SIU English, the claim lines it sits on, and what a
            person should verify. Payment suspension stays with the state. The product never prints
            fraud on a provider.
          </p>
        </div>
        <ul className="promise-list">
          <li className="reveal">A case is a network of NPIs, not a single ticket.</li>
          <li className="reveal">Harm-priority work jumps the dollar sort.</li>
          <li className="reveal">Every decision writes a hash-chained audit event.</li>
        </ul>
      </section>

      <section className="landing-end" id="demo">
        <div className="reveal">
          <p className="kicker">Four-minute walkthrough</p>
          <h2>Manager loads the extract. Investigator opens a packet.</h2>
        </div>
        <ol className="demo-steps">
          <li className="reveal">
            <strong>Manager</strong>
            <span>Sign in, confirm the desk filled, set hours if you want, then hand off.</span>
          </li>
          <li className="reveal">
            <strong>Investigator</strong>
            <span>Open a harm-priority case. Read the finding: problem, where it sits, why it fired.</span>
          </li>
          <li className="reveal">
            <strong>Decide</strong>
            <span>Record escalate, monitor, dismiss, or gather records — with a reason of 20+ characters.</span>
          </li>
        </ol>
        <p className="demo-creds reveal">
          <span>
            Manager <code>manager@demo.claimshield</code> / <code>demo-manager</code>
          </span>
          <span>
            Investigator <code>investigator@demo.claimshield</code> / <code>demo-investigator</code>
          </span>
        </p>
        <Link to="/login" className="btn solid reveal">
          Sign in
        </Link>
      </section>
    </div>
  );
}
