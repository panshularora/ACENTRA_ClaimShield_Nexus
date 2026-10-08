import { useEffect, useState } from "react";

export function useScrollProgress(target?: HTMLElement | null): number {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const read = () => {
      const el = target ?? document.documentElement;
      const max = el.scrollHeight - (target ? el.clientHeight : window.innerHeight);
      const top = target ? el.scrollTop : window.scrollY;
      setProgress(max > 0 ? Math.min(1, Math.max(0, top / max)) : 0);
    };
    read();
    const onScroll = () => read();
    const node: EventTarget = target ?? window;
    node.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", read);
    return () => {
      node.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", read);
    };
  }, [target]);

  return progress;
}

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReduced(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);
  return reduced;
}
