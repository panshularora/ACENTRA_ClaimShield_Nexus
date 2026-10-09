import { Component, type ErrorInfo, type ReactNode, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { LineFieldScene } from "./LineFieldScene";

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function readScroll(): number {
  const el = document.documentElement;
  const max = el.scrollHeight - el.clientHeight;
  if (max <= 1) return 0;
  return Math.min(1, Math.max(0, el.scrollTop / max));
}

/** Faint on the hero, full once most of it has scrolled away. */
const HERO_REVEAL = 0.28;

function readHeroReveal(): number {
  const hero = document.querySelector<HTMLElement>(".landing-hero");
  const h = hero?.offsetHeight ?? window.innerHeight;
  const y = window.scrollY || document.documentElement.scrollTop;
  const t = Math.min(1, Math.max(0, y / Math.max(64, h * 0.72)));
  return HERO_REVEAL + (1 - HERO_REVEAL) * t;
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

function StaticLines() {
  return (
    <svg className="line-field-static" viewBox="0 0 1200 800" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
      {Array.from({ length: 22 }, (_, i) => {
        const y = 40 + i * 34;
        const amp = 10 + (i % 4) * 4;
        const d = `M -40 ${y} C 200 ${y - amp}, 500 ${y + amp}, 800 ${y - amp * 0.4} S 1240 ${y + amp}, 1240 ${y}`;
        return <path key={i} d={d} fill="none" stroke="#e6ebe4" strokeWidth={i % 5 === 0 ? 1.1 : 0.7} opacity={0.08 + (i % 5 === 0 ? 0.08 : 0)} />;
      })}
    </svg>
  );
}

/**
 * Full-page 3D line veil for the public landing and login screens.
 * Scroll walks the camera through the lattice; pointer tilts it.
 */
export function PublicBackdrop({ holdUntilScroll = false }: { holdUntilScroll?: boolean }) {
  const reduce = prefersReducedMotion();
  const [failed, setFailed] = useState(false);
  const fail = useCallback(() => setFailed(true), []);
  const root = useRef<HTMLDivElement>(null);
  const scroll = useRef(0);
  const reveal = useRef(holdUntilScroll ? HERO_REVEAL : 1);
  const pointer = useRef({ x: 0, y: 0 });
  const nudge = useRef(0);

  useEffect(() => {
    const sync = () => {
      const s = readScroll();
      if (s > 0.02) nudge.current = 0;
      scroll.current = Math.min(1, Math.max(0, s + (holdUntilScroll ? 0 : nudge.current)));
      reveal.current = holdUntilScroll ? readHeroReveal() : 1;
      root.current?.style.setProperty("--line-reveal", reveal.current.toFixed(3));
    };
    const onPointer = (event: PointerEvent) => {
      const w = window.innerWidth || 1;
      const h = window.innerHeight || 1;
      pointer.current.x = (event.clientX / w) * 2 - 1;
      pointer.current.y = (event.clientY / h) * 2 - 1;
    };
    const onWheel = (event: WheelEvent) => {
      if (holdUntilScroll || readScroll() > 0) return;
      nudge.current = Math.min(0.55, Math.max(0, nudge.current + event.deltaY * 0.00035));
      scroll.current = nudge.current;
    };
    sync();
    window.addEventListener("scroll", sync, { passive: true });
    window.addEventListener("pointermove", onPointer, { passive: true });
    window.addEventListener("wheel", onWheel, { passive: true });
    let frame = 0;
    const tick = () => {
      if (!holdUntilScroll && nudge.current > 0.001 && readScroll() <= 0) {
        nudge.current *= 0.985;
        scroll.current = nudge.current;
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => {
      window.removeEventListener("scroll", sync);
      window.removeEventListener("pointermove", onPointer);
      window.removeEventListener("wheel", onWheel);
      cancelAnimationFrame(frame);
    };
  }, [holdUntilScroll]);

  const stage =
    failed || reduce ? (
      <StaticLines />
    ) : (
      <SceneGate fallback={<StaticLines />} onError={fail}>
        <Suspense fallback={<StaticLines />}>
          <LineFieldScene motion={{ scroll, pointer, reveal }} reducedMotion={reduce} onContextLost={fail} />
        </Suspense>
      </SceneGate>
    );

  return (
    <div className="public-lines" ref={root} aria-hidden="true">
      {stage}
    </div>
  );
}
