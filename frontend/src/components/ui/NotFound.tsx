import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { canOpenManagerDesk, homeFor } from "../../auth/access";
import { useAuth } from "../../auth/AuthProvider";

interface NotFoundProps {
  title: string;
  children: ReactNode;
}

/** Shared "not found" block with a way back to the user's home list. */
export function NotFound({ title, children }: NotFoundProps) {
  const { user, allowed } = useAuth();
  return (
    <section className="state not-found" aria-labelledby="not-found-title">
      <p className="kicker">404</p>
      <h2 id="not-found-title">{title}</h2>
      <div>{children}</div>
      <p className="not-found-links">
        {user ? (
          <Link to={homeFor(user)} className="btn">
            Back to your desk
          </Link>
        ) : null}
        {allowed("case:read") ? (
          <Link to="/investigator/cases" className="btn">
            Go to cases
          </Link>
        ) : null}
        {canOpenManagerDesk(user) ? (
          <Link to="/manager/queue" className="btn">
            Go to the queue
          </Link>
        ) : null}
        <Link to="/" className="btn ghost">
          Home
        </Link>
      </p>
    </section>
  );
}
