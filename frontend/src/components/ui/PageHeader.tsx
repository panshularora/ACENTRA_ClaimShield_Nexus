import type { ReactNode } from "react";

interface PageHeaderProps {
  eyebrow: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  titleClassName?: string;
}

/** Top-of-page heading block used by every signed-in route. */
export function PageHeader({ eyebrow, title, description, actions, titleClassName }: PageHeaderProps) {
  return (
    <header className="page-head">
      <div className="page-head-text">
        <p className="kicker">{eyebrow}</p>
        <h1 className={titleClassName}>{title}</h1>
        {description ? <p className="lede">{description}</p> : null}
      </div>
      {actions ? <div className="page-head-actions">{actions}</div> : null}
    </header>
  );
}
