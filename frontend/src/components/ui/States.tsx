import type { ReactNode } from "react";

/** Busy placeholder with a live text label for assistive tech. */
export function LoadingState({ label }: { label: string }) {
  return (
    <div className="state is-compact" role="status" aria-live="polite">
      <div className="skeleton" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <span>{label}</span>
    </div>
  );
}

/** Request failure. Pass the thrown value; ApiError messages are shown verbatim. */
export function ErrorState({
  title = "Something went wrong",
  error,
  onRetry,
}: {
  title?: string;
  error: unknown;
  onRetry?: () => void;
}) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className="state is-error" role="alert">
      <h3>{title}</h3>
      <p>{message}</p>
      {onRetry ? (
        <button type="button" className="btn small" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

/** Nothing to show, with an honest reason. */
export function EmptyState({
  title,
  children,
  compact = false,
}: {
  title: string;
  children?: ReactNode;
  compact?: boolean;
}) {
  return (
    <div className={`state ${compact ? "is-compact" : ""}`}>
      <h3>{title}</h3>
      {children ? <div>{children}</div> : null}
    </div>
  );
}
