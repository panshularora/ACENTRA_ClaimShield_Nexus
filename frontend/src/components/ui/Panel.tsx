import type { ReactNode } from "react";

interface PanelProps {
  /** Used for the heading id so the region is labelled by its title. */
  id: string;
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
  children: ReactNode;
}

/** A titled card region. Renders as a labelled <section>. */
export function Panel({ id, eyebrow, title, description, actions, className, children }: PanelProps) {
  const headingId = `${id}-title`;
  return (
    <section id={id} className={`panel ${className ?? ""}`} aria-labelledby={headingId}>
      <header className="panel-head">
        <div className="panel-head-text">
          {eyebrow ? <p className="kicker">{eyebrow}</p> : null}
          <h2 id={headingId}>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {actions ? <div className="panel-actions">{actions}</div> : null}
      </header>
      <div className="panel-body">{children}</div>
    </section>
  );
}
