import { useEffect, useRef, type ReactNode } from "react";

interface DrawerProps {
  /** Id for the heading that labels the dialog. */
  titleId: string;
  eyebrow: string;
  title: ReactNode;
  subtitle?: ReactNode;
  onClose: () => void;
  children: ReactNode;
}

/**
 * Modal side drawer: scrim click and Escape close it, focus moves to Close on open
 * and returns to the opener on close.
 */
export function Drawer({ titleId, eyebrow, title, subtitle, onClose, children }: DrawerProps) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCloseRef.current();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      opener?.focus();
    };
  }, []);

  return (
    <>
      <div className="drawer-scrim" onClick={onClose} aria-hidden="true" />
      <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <header className="drawer-head">
          <div>
            <p className="kicker">{eyebrow}</p>
            <h2 id={titleId}>{title}</h2>
            {subtitle ? <p className="mono muted">{subtitle}</p> : null}
          </div>
          <button ref={closeRef} type="button" className="btn small" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="drawer-body">{children}</div>
      </aside>
    </>
  );
}
